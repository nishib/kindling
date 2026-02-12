"""Simple rules engine for ERP scenario metrics and flags.

V1 keeps this deliberately lightweight while still matching the shape
described in the planning document.
"""

from __future__ import annotations

from typing import Callable, Dict, Tuple


ScenarioState = dict


def _clamp(v: float, lo: float, hi: float) -> float:
    return max(lo, min(hi, v))


def rule_stripe_sync_investigated(
    before: ScenarioState, after: ScenarioState, choice_id: str, context: dict | None = None
) -> ScenarioState:
    metrics = dict(after.get("metrics") or {})
    flags = dict(after.get("flags") or {})
    metrics["simulated_hours"] = (metrics.get("simulated_hours") or 0.0) + 0.5
    flags["stripe_sync_delayed"] = True
    metrics["audit_risk_score"] = _clamp((metrics.get("audit_risk_score") or 0) - 5, 0, 100)
    after["metrics"] = metrics
    after["flags"] = flags
    return after


def rule_revenue_understated_if_ignored(
    before: ScenarioState, after: ScenarioState, choice_id: str, context: dict | None = None
) -> ScenarioState:
    metrics = dict(after.get("metrics") or {})
    flags = dict(after.get("flags") or {})
    metrics["revenue_error_pct"] = (metrics.get("revenue_error_pct") or 0.0) + 3.0
    metrics["audit_risk_score"] = _clamp((metrics.get("audit_risk_score") or 0) + 10, 0, 100)
    flags["revenue_understated"] = True
    after["metrics"] = metrics
    after["flags"] = flags
    return after


def rule_integration_root_cause_found(
    before: ScenarioState, after: ScenarioState, choice_id: str, context: dict | None = None
) -> ScenarioState:
    metrics = dict(after.get("metrics") or {})
    flags = dict(after.get("flags") or {})
    metrics["simulated_hours"] = (metrics.get("simulated_hours") or 0.0) + 1.0
    flags["integration_root_cause_found"] = True
    metrics["audit_risk_score"] = _clamp((metrics.get("audit_risk_score") or 0) - 8, 0, 100)
    after["metrics"] = metrics
    after["flags"] = flags
    return after


def rule_reduce_revenue_error_and_risk(
    before: ScenarioState, after: ScenarioState, choice_id: str, context: dict | None = None
) -> ScenarioState:
    metrics = dict(after.get("metrics") or {})
    metrics["revenue_error_pct"] = _clamp((metrics.get("revenue_error_pct") or 0.0) - 2.0, 0.0, 100.0)
    metrics["audit_risk_score"] = _clamp((metrics.get("audit_risk_score") or 0) - 10, 0, 100)
    metrics["simulated_hours"] = (metrics.get("simulated_hours") or 0.0) + 1.0
    after["metrics"] = metrics
    return after


def rule_increase_audit_risk(
    before: ScenarioState, after: ScenarioState, choice_id: str, context: dict | None = None
) -> ScenarioState:
    metrics = dict(after.get("metrics") or {})
    metrics["audit_risk_score"] = _clamp((metrics.get("audit_risk_score") or 0) + 15, 0, 100)
    after["metrics"] = metrics
    return after


def rule_good_close_prioritization(
    before: ScenarioState, after: ScenarioState, choice_id: str, context: dict | None = None
) -> ScenarioState:
    metrics = dict(after.get("metrics") or {})
    metrics["simulated_hours"] = (metrics.get("simulated_hours") or 0.0) + 0.5
    metrics["open_recon_issues"] = max((metrics.get("open_recon_issues") or 1) - 1, 0)
    after["metrics"] = metrics
    return after


def rule_slow_close_path(
    before: ScenarioState, after: ScenarioState, choice_id: str, context: dict | None = None
) -> ScenarioState:
    metrics = dict(after.get("metrics") or {})
    metrics["simulated_hours"] = (metrics.get("simulated_hours") or 0.0) + 1.5
    metrics["open_recon_issues"] = (metrics.get("open_recon_issues") or 1) + 1
    after["metrics"] = metrics
    return after


def rule_reduce_close_risk(
    before: ScenarioState, after: ScenarioState, choice_id: str, context: dict | None = None
) -> ScenarioState:
    metrics = dict(after.get("metrics") or {})
    metrics["audit_risk_score"] = _clamp((metrics.get("audit_risk_score") or 0) - 10, 0, 100)
    metrics["open_recon_issues"] = max((metrics.get("open_recon_issues") or 1) - 1, 0)
    after["metrics"] = metrics
    return after


def rule_revrec_debug_path_invoice_first(
    before: ScenarioState, after: ScenarioState, choice_id: str, context: dict | None = None
) -> ScenarioState:
    """Good habit: start from system-of-record invoice, not bank."""
    metrics = dict(after.get("metrics") or {})
    flags = dict(after.get("flags") or {})
    metrics["simulated_hours"] = (metrics.get("simulated_hours") or 0.0) + 0.5
    metrics["audit_risk_score"] = _clamp((metrics.get("audit_risk_score") or 0) - 3, 0, 100)
    after["metrics"] = metrics
    after["flags"] = flags
    return after


def rule_revrec_bank_detour(
    before: ScenarioState, after: ScenarioState, choice_id: str, context: dict | None = None
) -> ScenarioState:
    """Less efficient path: jumping to bank feed before invoice/config."""
    metrics = dict(after.get("metrics") or {})
    metrics["simulated_hours"] = (metrics.get("simulated_hours") or 0.0) + 1.0
    metrics["audit_risk_score"] = _clamp((metrics.get("audit_risk_score") or 0) + 5, 0, 100)
    after["metrics"] = metrics
    return after


def rule_revrec_check_schedule(
    before: ScenarioState, after: ScenarioState, choice_id: str, context: dict | None = None
) -> ScenarioState:
    """Looking at the schedule is necessary, but doesn't fix config yet."""
    metrics = dict(after.get("metrics") or {})
    metrics["simulated_hours"] = (metrics.get("simulated_hours") or 0.0) + 0.5
    metrics["revenue_error_pct"] = (metrics.get("revenue_error_pct") or 0.0) + 1.0
    after["metrics"] = metrics
    return after


def rule_revrec_check_gl_first(
    before: ScenarioState, after: ScenarioState, choice_id: str, context: dict | None = None
) -> ScenarioState:
    """Jumping into GL before schedule tends to waste time."""
    metrics = dict(after.get("metrics") or {})
    metrics["simulated_hours"] = (metrics.get("simulated_hours") or 0.0) + 1.0
    metrics["audit_risk_score"] = _clamp((metrics.get("audit_risk_score") or 0) + 4, 0, 100)
    after["metrics"] = metrics
    return after


def rule_revrec_check_item_config(
    before: ScenarioState, after: ScenarioState, choice_id: str, context: dict | None = None
) -> ScenarioState:
    """Correct move: inspect item master and configuration."""
    metrics = dict(after.get("metrics") or {})
    flags = dict(after.get("flags") or {})
    metrics["simulated_hours"] = (metrics.get("simulated_hours") or 0.0) + 0.5
    metrics["open_recon_issues"] = max((metrics.get("open_recon_issues") or 1) - 1, 0)
    flags["integration_root_cause_found"] = True
    after["metrics"] = metrics
    after["flags"] = flags
    return after


def rule_revrec_force_schedule(
    before: ScenarioState, after: ScenarioState, choice_id: str, context: dict | None = None
) -> ScenarioState:
    """Manual schedule hack: improves numbers but increases audit risk."""
    metrics = dict(after.get("metrics") or {})
    flags = dict(after.get("flags") or {})
    metrics["simulated_hours"] = (metrics.get("simulated_hours") or 0.0) + 0.5
    metrics["revenue_error_pct"] = _clamp((metrics.get("revenue_error_pct") or 0.0) - 2.0, 0.0, 100.0)
    metrics["audit_risk_score"] = _clamp((metrics.get("audit_risk_score") or 0) + 12, 0, 100)
    flags["revenue_understated"] = True
    after["metrics"] = metrics
    after["flags"] = flags
    return after


def rule_revrec_fix_rule(
    before: ScenarioState, after: ScenarioState, choice_id: str, context: dict | None = None
) -> ScenarioState:
    """Fixing the rev rec rule should largely resolve understatement and risk."""
    metrics = dict(after.get("metrics") or {})
    flags = dict(after.get("flags") or {})
    metrics["simulated_hours"] = (metrics.get("simulated_hours") or 0.0) + 0.5
    metrics["revenue_error_pct"] = _clamp((metrics.get("revenue_error_pct") or 0.0) - 5.0, 0.0, 100.0)
    metrics["audit_risk_score"] = _clamp((metrics.get("audit_risk_score") or 0) - 15, 0, 100)
    flags["revenue_understated"] = False
    after["metrics"] = metrics
    after["flags"] = flags
    return after

RULES: Dict[str, Callable[[ScenarioState, ScenarioState, str, dict | None], ScenarioState]] = {
    "stripe_sync_investigated": rule_stripe_sync_investigated,
    "revenue_understated_if_ignored": rule_revenue_understated_if_ignored,
    "integration_root_cause_found": rule_integration_root_cause_found,
    "reduce_revenue_error_and_risk": rule_reduce_revenue_error_and_risk,
    "increase_audit_risk": rule_increase_audit_risk,
    "good_close_prioritization": rule_good_close_prioritization,
    "slow_close_path": rule_slow_close_path,
    "reduce_close_risk": rule_reduce_close_risk,
    "revrec_debug_path_invoice_first": rule_revrec_debug_path_invoice_first,
    "revrec_bank_detour": rule_revrec_bank_detour,
    "revrec_check_schedule": rule_revrec_check_schedule,
    "revrec_check_gl_first": rule_revrec_check_gl_first,
    "revrec_check_item_config": rule_revrec_check_item_config,
    "revrec_force_schedule": rule_revrec_force_schedule,
    "revrec_fix_rule": rule_revrec_fix_rule,
}


def compute_consequences(
    before: ScenarioState, after: ScenarioState, choice_rules: list[str]
) -> ScenarioState:
    """Apply all rules declared on the taken choice."""
    new_state = dict(after)
    for rule_id in choice_rules:
        fn = RULES.get(rule_id)
        if not fn:
            continue
        new_state = fn(before, new_state, "", {})
    return new_state


def compute_outcome(final_state: ScenarioState) -> dict:
    """Summarize final metrics into a debrief-friendly structure."""
    metrics = final_state.get("metrics") or {}
    flags = final_state.get("flags") or {}
    decisions = final_state.get("decisions") or []

    strengths: list[str] = []
    weaknesses: list[str] = []
    concepts_to_review: list[str] = []

    if metrics.get("revenue_error_pct", 0) <= 1.0:
        strengths.append("You kept revenue error within an acceptable range.")
    else:
        weaknesses.append("Revenue remained materially misstated during the scenario.")
        concepts_to_review.append("Revenue recognition timing and reconciliations.")

    if metrics.get("audit_risk_score", 0) <= 40:
        strengths.append("You managed overall audit risk down over time.")
    else:
        weaknesses.append("Audit risk stayed high because key anomalies were not fully resolved.")
        concepts_to_review.append("How to reduce audit and close risk when integrations misbehave.")

    if flags.get("integration_root_cause_found"):
        strengths.append("You traced issues back to a clear root cause.")
    else:
        weaknesses.append("You did not fully isolate likely root causes.")
        concepts_to_review.append("How to work backwards from anomalies to root causes.")

    if flags.get("revenue_understated"):
        weaknesses.append(
            "Revenue remained understated because configuration or schedules were not fully corrected."
        )
        concepts_to_review.append(
            "Deferred revenue vs earned revenue and how revenue waterfalls reflect timing."
        )

    choice_ids = [d.get("choice_id") for d in decisions]
    if "revrec_debug_path_invoice_first" in choice_ids and "revrec_fix_rule" in choice_ids:
        strengths.append(
            "You approached the issue like a senior revenue lead: starting from the invoice, "
            "following the missing schedule, and fixing the underlying rev rec rule."
        )
    elif "revrec_force_schedule" in choice_ids and "revrec_fix_rule" not in choice_ids:
        weaknesses.append(
            "You improved reported revenue with a manual schedule but did not fix the missing rev rec rule, "
            "leaving configuration risk and future discrepancies."
        )
        concepts_to_review.append("Why configuration-level fixes are safer than one-off schedule or journal hacks.")

    if not strengths:
        strengths.append("You explored the scenario and made decisions; use the feedback to iterate.")
    if not weaknesses:
        weaknesses.append("You avoided major pitfalls in this scenario.")

    return {
        "metrics": {
            "simulated_hours": float(metrics.get("simulated_hours", 0.0)),
            "revenue_error_pct": float(metrics.get("revenue_error_pct", 0.0)),
            "open_recon_issues": int(metrics.get("open_recon_issues", 0)),
            "audit_risk_score": int(metrics.get("audit_risk_score", 0)),
        },
        "strengths": strengths,
        "weaknesses": weaknesses,
        "concepts_to_review": list(dict.fromkeys(concepts_to_review)),
    }

