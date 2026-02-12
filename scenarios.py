"""FastAPI router for simulated ERP scenarios."""

from __future__ import annotations

import datetime as dt
from typing import List, Optional, Dict, Any

from fastapi import APIRouter, Depends, HTTPException
from pydantic import BaseModel, Field
from sqlalchemy.orm import Session
from sqlalchemy.exc import SQLAlchemyError
import uuid

from database import get_db
from models import ERPScenarioEvent, ERPScenarioRun
from scenario_engine import coach, rules_engine, state_machine, synthetic_data, templates


router = APIRouter()


# In-memory fallback store so scenarios still work even if the DB
# is unavailable or tables are missing.
_IN_MEMORY_RUNS: Dict[str, Dict[str, Any]] = {}


class CompanyEntity(BaseModel):
    code: str
    name: str
    currency: str
    is_parent: bool = False
    parent_code: Optional[str] = None


class CompanyProfile(BaseModel):
    name: str
    business_model: str
    customers: int
    arr: float
    entities: List[CompanyEntity]
    tools: List[str]


class ScenarioChoice(BaseModel):
    id: str
    label: str
    description: str


class ScenarioStep(BaseModel):
    id: str
    title: str
    description: str
    step_type: str
    choices: List[ScenarioChoice] = []


class ScenarioTemplateSummary(BaseModel):
    id: str
    title: str
    description: str
    difficulty: str
    skills_trained: List[str]
    estimated_minutes: int


class ScenarioTemplateDetail(ScenarioTemplateSummary):
    company_profile: CompanyProfile
    datasets: dict
    steps: List[ScenarioStep]


class ScenarioDecisionEvent(BaseModel):
    step_id: str
    choice_id: str


class ScenarioMetrics(BaseModel):
    simulated_hours: float = 0.0
    revenue_error_pct: float = 0.0
    open_recon_issues: int = 0
    audit_risk_score: int = 0


class ScenarioFlags(BaseModel):
    stripe_sync_delayed: bool = False
    revenue_understated: bool = False
    period_closed: bool = False
    integration_root_cause_found: bool = False


class ScenarioState(BaseModel):
    current_step_id: str
    completed_steps: List[str]
    decisions: List[ScenarioDecisionEvent]
    metrics: ScenarioMetrics
    flags: ScenarioFlags
    status: str


class ScenarioRunState(BaseModel):
    run_id: str
    template: ScenarioTemplateSummary
    state: ScenarioState
    current_step: ScenarioStep
    synthetic_data: dict


class DecisionRequest(BaseModel):
    choice_id: str = Field(..., description="ID of the selected choice for the current step.")


class DecisionResponse(BaseModel):
    run: ScenarioRunState
    coach_message: Optional[str] = None


class CoachQuestionRequest(BaseModel):
    question: str


class CoachAnswerResponse(BaseModel):
    answer: str


class DebriefSummary(BaseModel):
    outcome_title: str
    metrics: rules_engine.ScenarioState  # simple dict with metrics/flags
    strengths: List[str]
    weaknesses: List[str]
    concepts_to_review: List[str]
    recommended_next_scenarios: List[ScenarioTemplateSummary]


def _to_step_model(raw_step: dict) -> ScenarioStep:
    return ScenarioStep(
        id=raw_step["id"],
        title=raw_step["title"],
        description=raw_step["description"],
        step_type=raw_step.get("step_type", "task"),
        choices=[ScenarioChoice(**c) for c in raw_step.get("choices", [])],
    )


def _get_template_or_404(template_id: str):
    tpl = templates.load_template(template_id)
    if not tpl:
        raise HTTPException(status_code=404, detail="Scenario template not found")
    return tpl


@router.get("", response_model=List[ScenarioTemplateSummary])
def list_scenarios() -> List[ScenarioTemplateSummary]:
    """List all available ERP scenario templates."""
    return [ScenarioTemplateSummary(**t) for t in templates.get_all_summaries()]


@router.get("/{scenario_id}", response_model=ScenarioTemplateDetail)
def get_scenario_detail(scenario_id: str) -> ScenarioTemplateDetail:
    """Get a single scenario template, including synthetic data preview."""
    tpl = _get_template_or_404(scenario_id)
    bundle = synthetic_data.generate_bundle(scenario_id)
    summary = ScenarioTemplateSummary(
        id=tpl["id"],
        title=tpl["title"],
        description=tpl["description"],
        difficulty=tpl["difficulty"],
        skills_trained=tpl["skills_trained"],
        estimated_minutes=tpl["estimated_minutes"],
    )
    steps = [
        ScenarioStep(
            id=s["id"],
            title=s["title"],
            description=s["description"],
            step_type=s.get("step_type", "task"),
            choices=[ScenarioChoice(**c) for c in s.get("choices", [])],
        )
        for s in tpl["steps"]
    ]
    return ScenarioTemplateDetail(
        **summary.dict(),
        company_profile=CompanyProfile(**bundle["company_profile"]),
        datasets=bundle["datasets"],
        steps=steps,
    )


@router.post("/{scenario_id}/start", response_model=ScenarioRunState)
def start_scenario(
    scenario_id: str,
    user_session_id: Optional[str] = None,
    db: Session = Depends(get_db),
) -> ScenarioRunState:
    """Start a new scenario run and persist initial state.

    If the database is unavailable, fall back to an in-memory run so the
    learning experience still works during development.
    """
    tpl = _get_template_or_404(scenario_id)
    state_dict, current_step_raw = state_machine.initialize_state(tpl)
    bundle = synthetic_data.generate_bundle(scenario_id)
    run_id_str = str(uuid.uuid4())

    # Try to persist to DB; on failure, fall back to in-memory only.
    try:
        run = ERPScenarioRun(
            template_id=scenario_id,
            user_session_id=user_session_id,
            started_at=dt.datetime.utcnow(),
            last_updated_at=dt.datetime.utcnow(),
            state_json=state_dict,
            synthetic_data_json=bundle,
        )
        db.add(run)
        db.commit()
        db.refresh(run)
        run_id_str = str(run.run_id)
        stored_bundle = run.synthetic_data_json
    except SQLAlchemyError:
        db.rollback()
        stored_bundle = bundle

    # Always keep an in-memory copy so we can operate without DB.
    _IN_MEMORY_RUNS[run_id_str] = {
        "template_id": scenario_id,
        "state": state_dict,
        "synthetic_data": bundle,
    }

    summary = ScenarioTemplateSummary(
        id=tpl["id"],
        title=tpl["title"],
        description=tpl["description"],
        difficulty=tpl["difficulty"],
        skills_trained=tpl["skills_trained"],
        estimated_minutes=tpl["estimated_minutes"],
    )

    state_model = ScenarioState(
        current_step_id=state_dict["current_step_id"],
        completed_steps=state_dict["completed_steps"],
        decisions=[ScenarioDecisionEvent(**d) for d in state_dict["decisions"]],
        metrics=ScenarioMetrics(**state_dict["metrics"]),
        flags=ScenarioFlags(**state_dict["flags"]),
        status=state_dict["status"],
    )

    return ScenarioRunState(
        run_id=run_id_str,
        template=summary,
        state=state_model,
        current_step=_to_step_model(current_step_raw),
        synthetic_data=stored_bundle,
    )


@router.post("/{run_id}/decision", response_model=DecisionResponse)
def submit_decision(
    run_id: str,
    req: DecisionRequest,
    db: Session = Depends(get_db),
) -> DecisionResponse:
    """Record a decision for the current step and advance the run.

    Uses the database when available; otherwise falls back to the
    in-memory run store populated at start.
    """
    run = None
    try:
        run = db.get(ERPScenarioRun, run_id)
    except SQLAlchemyError:
        run = None

    mem_run = _IN_MEMORY_RUNS.get(run_id)
    if not run and not mem_run:
        raise HTTPException(status_code=404, detail="Scenario run not found")

    template_id = run.template_id if run else mem_run["template_id"]
    tpl = _get_template_or_404(template_id)
    before_state = dict((run.state_json or {}) if run else (mem_run["state"] or {}))

    try:
        new_state_dict, current_step_raw = state_machine.apply_choice(tpl, before_state, req.choice_id)
    except ValueError as exc:
        raise HTTPException(status_code=422, detail=str(exc)) from exc

    # Find rules on the chosen choice
    choice_rules: list[str] = []
    for step in tpl["steps"]:
        if step["id"] == before_state.get("current_step_id"):
            for c in step["choices"]:
                if c["id"] == req.choice_id:
                    choice_rules = list(c.get("rules") or [])
                    break
            break

    after_with_rules = rules_engine.compute_consequences(before_state, new_state_dict, choice_rules)

    # Persist to DB if possible, but never fail the request if DB is down.
    if run:
        try:
            run.state_json = after_with_rules
            run.last_updated_at = dt.datetime.utcnow()
            db.add(
                ERPScenarioEvent(
                    run_id=run.run_id,
                    step_id=before_state.get("current_step_id") or "",
                    choice_id=req.choice_id,
                )
            )
            db.commit()
            db.refresh(run)
        except SQLAlchemyError:
            db.rollback()

    # Always update in-memory copy.
    if mem_run:
        mem_run["state"] = after_with_rules
    else:
        _IN_MEMORY_RUNS[run_id] = {
            "template_id": template_id,
            "state": after_with_rules,
            "synthetic_data": (run.synthetic_data_json if run else {}),
        }

    summary = ScenarioTemplateSummary(
        id=tpl["id"],
        title=tpl["title"],
        description=tpl["description"],
        difficulty=tpl["difficulty"],
        skills_trained=tpl["skills_trained"],
        estimated_minutes=tpl["estimated_minutes"],
    )

    state_model = ScenarioState(
        current_step_id=after_with_rules["current_step_id"],
        completed_steps=after_with_rules["completed_steps"],
        decisions=[ScenarioDecisionEvent(**d) for d in after_with_rules["decisions"]],
        metrics=ScenarioMetrics(**after_with_rules["metrics"]),
        flags=ScenarioFlags(**after_with_rules["flags"]),
        status=after_with_rules["status"],
    )

    # Simple inline coach message
    current_step = _to_step_model(current_step_raw)
    choice_label = req.choice_id
    for step in tpl["steps"]:
        for c in step["choices"]:
            if c["id"] == req.choice_id:
                choice_label = c["label"]
                break

    coach_msg = coach.generate_inline_feedback(current_step.title, choice_label)

    return DecisionResponse(
        run=ScenarioRunState(
            run_id=run_id,
            template=summary,
            state=state_model,
            current_step=current_step,
            synthetic_data=(run.synthetic_data_json if run else mem_run.get("synthetic_data", {})),
        ),
        coach_message=coach_msg,
    )


@router.post("/{run_id}/coach", response_model=CoachAnswerResponse)
def ask_coach(
    run_id: str,
    req: CoachQuestionRequest,
    db: Session = Depends(get_db),
) -> CoachAnswerResponse:
    """Ask the AI coach a question about the current scenario."""
    run = db.get(ERPScenarioRun, run_id)
    if not run:
        raise HTTPException(status_code=404, detail="Scenario run not found")

    tpl = _get_template_or_404(run.template_id)
    ctx = {
        "template": {
            "id": tpl["id"],
            "title": tpl["title"],
            "description": tpl["description"],
        },
        "state": run.state_json,
        "synthetic_data": run.synthetic_data_json,
    }
    answer = coach.answer_question(ctx, req.question)
    return CoachAnswerResponse(answer=answer)


@router.get("/{run_id}/debrief", response_model=DebriefSummary)
def get_debrief(
    run_id: str,
    db: Session = Depends(get_db),
) -> DebriefSummary:
    """Compute a debrief summary for a completed scenario run.

    Reads from DB when possible; otherwise uses the in-memory run store.
    """
    run = None
    try:
        run = db.get(ERPScenarioRun, run_id)
    except SQLAlchemyError:
        run = None

    mem_run = _IN_MEMORY_RUNS.get(run_id)
    if not run and not mem_run:
        raise HTTPException(status_code=404, detail="Scenario run not found")

    template_id = run.template_id if run else mem_run["template_id"]
    tpl = _get_template_or_404(template_id)
    final_state = (run.state_json or {}) if run else (mem_run["state"] or {})
    outcome = rules_engine.compute_outcome(final_state)

    outcome_title = "Scenario completed"
    if final_state.get("status") != "COMPLETE":
        outcome_title = "Scenario in progress"

    metrics = outcome["metrics"]
    strengths = outcome["strengths"]
    weaknesses = outcome["weaknesses"]
    concepts_to_review = outcome["concepts_to_review"]

    all_summaries = [ScenarioTemplateSummary(**t) for t in templates.get_all_summaries()]

    return DebriefSummary(
        outcome_title=outcome_title,
        metrics=metrics,
        strengths=strengths,
        weaknesses=weaknesses,
        concepts_to_review=concepts_to_review,
        recommended_next_scenarios=all_summaries,
    )

