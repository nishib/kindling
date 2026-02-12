"""Lightweight AI coach stub for scenarios.

V1 keeps this intentionally simple: it generates structured, textual
feedback without requiring additional external API calls beyond what
the app already supports for Gemini.
"""

from __future__ import annotations


def generate_inline_feedback(step_title: str, choice_label: str) -> str:
    """Short, encouraging explanation shown after a decision."""
    return (
        f"In this step ({step_title}), you chose '{choice_label}'. "
        "Think about how this affects revenue accuracy, audit risk, and time-to-resolution."
    )


def answer_question(context: dict, question: str) -> str:
    """Answer a free-form learner question based on lightweight context.

    For now this does not call Gemini directly; instead it uses the
    scenario metadata to frame a helpful, bounded answer.
    """
    template = context.get("template") or {}
    state = context.get("state") or {}
    company = (context.get("synthetic_data") or {}).get("company_profile") or {}

    title = template.get("title") or "this scenario"
    company_name = company.get("name") or "the company in this scenario"
    current_step_id = state.get("current_step_id") or ""

    return (
        f"You are practicing {title} for {company_name}. "
        f"Right now you are on step '{current_step_id or 'start'}'. "
        "Use this scenario to reason through what good looks like: "
        "identify anomalies, trace them to root causes, and recommend "
        "actions that reduce audit risk while keeping revenue accurate. "
        f"For your question — “{question}” — focus on how your next decision "
        "impacts reconciliations, integrations, and how confident you would "
        "feel explaining it to an auditor or a new teammate."
    )

