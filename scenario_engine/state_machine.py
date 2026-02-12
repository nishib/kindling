"""Finite state machine for ERP scenarios."""

from __future__ import annotations

from typing import Dict, Tuple

from .templates import ScenarioTemplateDef, ScenarioStepDef


def _index_steps(template: ScenarioTemplateDef) -> Dict[str, ScenarioStepDef]:
    return {step["id"]: step for step in template["steps"]}


def initialize_state(template: ScenarioTemplateDef) -> Tuple[dict, ScenarioStepDef]:
    """Create initial ScenarioState and first step.

    State shape matches the planning document at a minimal level.
    """
    steps_by_id = _index_steps(template)
    first_step = template["steps"][0]
    state = {
        "current_step_id": first_step["id"],
        "completed_steps": [],
        "decisions": [],
        "metrics": {
            "simulated_hours": 0.0,
            "revenue_error_pct": 0.0,
            "open_recon_issues": 1,
            "audit_risk_score": 20,
        },
        "flags": {
            "stripe_sync_delayed": False,
            "revenue_understated": False,
            "period_closed": False,
            "integration_root_cause_found": False,
        },
        "status": "AWAITING_DECISION",
    }
    return state, steps_by_id[first_step["id"]]


def apply_choice(
    template: ScenarioTemplateDef,
    state: dict,
    choice_id: str,
) -> Tuple[dict, ScenarioStepDef]:
    """Apply a user choice and advance the state machine.

    Returns (new_state, current_step). Raises ValueError on invalid transitions.
    """
    if state.get("status") not in {"AWAITING_DECISION", "IN_PROGRESS"}:
        raise ValueError("Scenario is not accepting decisions in its current state.")

    steps_by_id = _index_steps(template)
    current_step_id = state.get("current_step_id")
    if current_step_id not in steps_by_id:
        raise ValueError("Current step not found in template.")
    current_step = steps_by_id[current_step_id]

    choice = next((c for c in current_step["choices"] if c["id"] == choice_id), None)
    if not choice:
        raise ValueError("Invalid choice for current step.")

    # Clone state shallowly for safety
    new_state = {
        **state,
        "completed_steps": list(state.get("completed_steps") or []),
        "decisions": list(state.get("decisions") or []),
    }
    new_state["completed_steps"].append(current_step_id)
    new_state["decisions"].append(
        {
            "step_id": current_step_id,
            "choice_id": choice_id,
        }
    )

    next_step_id = choice.get("next_step_id")
    if next_step_id:
        if next_step_id not in steps_by_id:
            raise ValueError("Next step not found in template.")
        new_state["current_step_id"] = next_step_id
        new_state["status"] = "AWAITING_DECISION"
        next_step = steps_by_id[next_step_id]
    else:
        # Terminal step
        new_state["current_step_id"] = current_step_id
        new_state["status"] = "COMPLETE"
        next_step = current_step

    return new_state, next_step

