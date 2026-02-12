"""Static scenario templates for ERP simulations (V1).

These are deliberately simple, hard-coded templates that match the
shape expected by the transport models in `scenarios.py`.
"""

from __future__ import annotations

from typing import Dict, List, Optional, TypedDict


class ScenarioChoiceDef(TypedDict):
    id: str
    label: str
    description: str
    next_step_id: Optional[str]
    rules: List[str]


class ScenarioStepDef(TypedDict):
    id: str
    title: str
    description: str
    step_type: str
    choices: List[ScenarioChoiceDef]


class ScenarioTemplateDef(TypedDict):
    id: str
    title: str
    description: str
    difficulty: str
    skills_trained: List[str]
    estimated_minutes: int
    steps: List[ScenarioStepDef]


_TEMPLATES: Dict[str, ScenarioTemplateDef] = {}


def _register(template: ScenarioTemplateDef) -> None:
    _TEMPLATES[template["id"]] = template


_register(
    {
        "id": "rev-rec-001",
        "title": "Revenue Recognition Debugging",
        "description": "Debug why an Acme Corp invoice posted correctly but no revenue was recognized due to a missing rev rec rule.",
        "difficulty": "intermediate",
        "skills_trained": ["ASC 606 timing", "Item master configuration", "Revenue waterfalls"],
        "estimated_minutes": 20,
        "steps": [
            {
                "id": "intro",
                "title": "Ticket from CFO: $0 on P&L",
                "description": "Ticket #224: The CFO flags that the Acme Corp invoice posted, cash has been collected, but revenue is showing as $0 on the P&L for the month.",
                "step_type": "task",
                "choices": [
                    {
                        "id": "view_invoice",
                        "label": "View the Acme Corp invoice record",
                        "description": "Open the invoice inside Campfire ERP and confirm what actually posted.",
                        "next_step_id": "view_invoice",
                        "rules": ["revrec_debug_path_invoice_first"],
                    },
                    {
                        "id": "check_bank",
                        "label": "Check the bank feed and cash account first",
                        "description": "Look at bank transactions instead of system-of-record invoices.",
                        "next_step_id": "view_invoice",
                        "rules": ["revrec_bank_detour"],
                    },
                ],
            },
            {
                "id": "view_invoice",
                "title": "Review the invoice record",
                "description": "The Acme Corp invoice looks correct. Line item SaaS_Enterprise_Plan is present and marked paid, but recognized revenue is still $0.",
                "step_type": "task",
                "choices": [
                    {
                        "id": "inspect_schedule",
                        "label": "Inspect the revenue schedule for this invoice",
                        "description": "Open the revenue schedule linked to this invoice and see what entries were created.",
                        "next_step_id": "inspect_schedule",
                        "rules": ["revrec_check_schedule"],
                    },
                    {
                        "id": "view_gl",
                        "label": "Jump straight to the GL",
                        "description": "Look at journal entries in the GL instead of checking the schedule first.",
                        "next_step_id": "inspect_schedule",
                        "rules": ["revrec_check_gl_first"],
                    },
                ],
            },
            {
                "id": "inspect_schedule",
                "title": "Revenue schedule is missing",
                "description": "The system shows no revenue schedule attached to the Acme Corp invoice. Everything is sitting in Deferred Revenue.",
                "step_type": "task",
                "choices": [
                    {
                        "id": "check_config",
                        "label": "Check the item master configuration for SaaS_Enterprise_Plan",
                        "description": "Inspect the item configuration, including revenue recognition rule mapping.",
                        "next_step_id": "check_config",
                        "rules": ["revrec_check_item_config"],
                    },
                    {
                        "id": "force_create",
                        "label": "Force-create a manual revenue schedule",
                        "description": "Manually create a revenue schedule without fixing underlying configuration.",
                        "next_step_id": "check_config",
                        "rules": ["revrec_force_schedule"],
                    },
                ],
            },
            {
                "id": "check_config",
                "title": "Item master shows missing rev rec rule",
                "description": "The item master for SaaS_Enterprise_Plan has no revenue recognition rule mapped, so the system never generated a schedule.",
                "step_type": "task",
                "choices": [
                    {
                        "id": "set_rule_ratable_daily",
                        "label": "Set rev rec rule to Ratable - Daily and save",
                        "description": "Map SaaS_Enterprise_Plan to a daily ratable revenue rule and save the configuration.",
                        "next_step_id": "resolution",
                        "rules": ["revrec_fix_rule"],
                    }
                ],
            },
            {
                "id": "resolution",
                "title": "Revenue schedule generated",
                "description": "After fixing the rev rec rule, the system backfills and generates the correct revenue schedule and waterfall for Acme Corp.",
                "step_type": "debrief",
                "choices": [
                    {
                        "id": "finish",
                        "label": "Review revenue waterfall and finish",
                        "description": "Confirm the schedule and explain the root cause to the CFO.",
                        "next_step_id": None,
                        "rules": [],
                    }
                ],
            },
        ],
    }
)

def get_all_summaries() -> List[dict]:
    """Return lightweight summaries for sidebar listing."""
    return [
        {
            "id": t["id"],
            "title": t["title"],
            "description": t["description"],
            "difficulty": t["difficulty"],
            "skills_trained": t["skills_trained"],
            "estimated_minutes": t["estimated_minutes"],
        }
        for t in _TEMPLATES.values()
    ]


def load_template(template_id: str) -> Optional[ScenarioTemplateDef]:
    """Return the full template definition for a given id."""
    return _TEMPLATES.get(template_id)

