"""Synthetic company profile and datasets for scenarios (V1).

To keep things simple we generate small, deterministic tables that
illustrate the concepts without heavy volume.
"""

from __future__ import annotations

from typing import Dict, List


def generate_company_profile(template_id: str) -> dict:
    """Return a small synthetic company profile keyed by template."""
    if template_id == "rev-rec-001":
        return {
            "name": "EmberStack, Inc.",
            "business_model": "B2B SaaS",
            "customers": 180,
            "arr": 4_200_000.0,
            "entities": [
                {"code": "US", "name": "EmberStack US", "currency": "USD", "is_parent": True},
                {"code": "UK", "name": "EmberStack UK", "currency": "GBP", "is_parent": False, "parent_code": "US"},
            ],
            "tools": ["Stripe", "Salesforce", "Campfire ERP"],
        }
    if template_id == "month_end_close":
        return {
            "name": "LedgerLoop Labs",
            "business_model": "B2B SaaS",
            "customers": 75,
            "arr": 1_300_000.0,
            "entities": [
                {"code": "US", "name": "LedgerLoop US", "currency": "USD", "is_parent": True},
                {"code": "CA", "name": "LedgerLoop Canada", "currency": "CAD", "is_parent": False, "parent_code": "US"},
            ],
            "tools": ["Stripe", "QuickBooks", "Campfire ERP"],
        }
    # Fallback generic company
    return {
        "name": "SampleCo",
        "business_model": "B2B SaaS",
        "customers": 50,
        "arr": 1_000_000.0,
        "entities": [{"code": "US", "name": "SampleCo US", "currency": "USD", "is_parent": True}],
        "tools": ["Stripe", "Campfire ERP"],
    }


def generate_datasets(template_id: str) -> Dict[str, List[dict]]:
    """Return small tables aligned with the planning doc."""
    if template_id == "rev-rec-001":
        return {
            "chart_of_accounts": [
                {"code": "4000", "name": "SaaS Subscription Revenue", "type": "revenue", "entity_code": "US"},
                {"code": "1000", "name": "Cash", "type": "asset", "entity_code": "US"},
            ],
            "invoices": [
                {
                    "invoice_id": "INV-1001",
                    "customer_name": "Acme Corp",
                    "amount": 12000.0,
                    "issue_date": "2024-11-01",
                    "due_date": "2024-12-01",
                    "status": "paid",
                    "integration_source": "Stripe",
                },
                {
                    "invoice_id": "INV-1002",
                    "customer_name": "Orbit Labs",
                    "amount": 18000.0,
                    "issue_date": "2024-11-01",
                    "due_date": "2024-12-01",
                    "status": "pending_sync",
                    "integration_source": "Stripe",
                },
            ],
            "integration_events": [
                {
                    "event_id": "evt_1",
                    "source_system": "Stripe",
                    "event_type": "invoice.paid",
                    "status": "processed",
                    "created_at": "2024-11-02T10:32:00Z",
                },
                {
                    "event_id": "evt_2",
                    "source_system": "Stripe",
                    "event_type": "invoice.payment_succeeded",
                    "status": "failed",
                    "error_code": "timeout",
                    "error_message": "Webhook delivery timed out",
                    "created_at": "2024-11-02T10:35:00Z",
                },
            ],
            "failed_webhooks": [
                {
                    "id": "wh_1",
                    "provider": "Stripe",
                    "status_code": 500,
                    "error_summary": "Internal error while applying invoice to contract",
                    "first_failed_at": "2024-11-02T10:35:12Z",
                    "last_attempt_at": "2024-11-02T10:45:12Z",
                }
            ],
        }

    if template_id == "month_end_close":
        return {
            "chart_of_accounts": [
                {"code": "1000", "name": "Cash", "type": "asset", "entity_code": "US"},
                {"code": "1100", "name": "Cash - CA", "type": "asset", "entity_code": "CA"},
                {"code": "2000", "name": "Accounts Payable", "type": "liability", "entity_code": "US"},
            ],
            "journal_entries": [
                {
                    "entry_id": "JE-100",
                    "date": "2024-11-30",
                    "description": "Stripe fees reclass",
                    "debit_account": "6000",
                    "credit_account": "1000",
                    "amount": 1200.0,
                    "entity_code": "US",
                },
                {
                    "entry_id": "JE-101",
                    "date": "2024-11-30",
                    "description": "Accrued revenue",
                    "debit_account": "1200",
                    "credit_account": "4000",
                    "amount": 8000.0,
                    "entity_code": "US",
                },
            ],
            "invoices": [
                {
                    "invoice_id": "INV-CA-10",
                    "customer_name": "DataNorth",
                    "amount": 5000.0,
                    "issue_date": "2024-11-28",
                    "due_date": "2024-12-28",
                    "status": "open",
                    "integration_source": "Stripe",
                }
            ],
        }

    # Minimal generic set
    return {
        "chart_of_accounts": [],
        "invoices": [],
        "journal_entries": [],
        "integration_events": [],
        "failed_webhooks": [],
    }


def generate_bundle(template_id: str) -> dict:
    """Convenience for router: { company_profile, datasets, artifacts_by_step? }."""
    bundle: dict = {
        "company_profile": generate_company_profile(template_id),
        "datasets": generate_datasets(template_id),
    }

    # Optional, richer artifacts for specific scenarios
    if template_id == "rev-rec-001":
        bundle["artifacts_by_step"] = {
            "view_invoice": [
                {
                    "id": "inv_2024_001",
                    "type": "invoice",
                    "title": "Invoice #INV-2024-001 · Acme Corp",
                    "content": {
                        "customer": "Acme Corp",
                        "date": "2024-03-15",
                        "total": 12000,
                        "lines": [
                            {
                                "item": "SaaS_Enterprise_Plan",
                                "amount": 12000,
                                "rev_rule": "Pending",
                            }
                        ],
                    },
                }
            ],
            "check_config": [
                {
                    "id": "item_config_saas",
                    "type": "config_form",
                    "title": "Item Master: SaaS_Enterprise_Plan",
                    "content": {
                        "sku": "SaaS_Enterprise_Plan",
                        "gl_account": "4000 Revenue",
                        "rev_rec_rule": None,  # The bug: rule not mapped
                    },
                }
            ],
            "resolution": [
                {
                    "id": "rev_schedule_final",
                    "type": "waterfall_table",
                    "title": "Preview: Revenue Schedule for Acme Corp",
                    "content": [
                        {"period": "Mar 2024", "amount": 516.12},
                        {"period": "Apr 2024", "amount": 1000.00},
                        {"period": "May 2024", "amount": 1000.00},
                    ],
                }
            ],
        }

    return bundle

