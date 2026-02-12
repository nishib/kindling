"""
Learning pathways for Campfire onboarding (Chunk 1).
Accounting path and ERP path with structured modules; short text per module.
API: paths list, path detail with modules; "Ask the assistant" uses module context.
"""
from typing import Optional

# ERP path: ERP 101 → Legacy vs modern → Campfire's place
ERP_PATH = {
    "id": "erp",
    "title": "ERP fundamentals",
    "description": "From what ERP is to how Campfire fits in the landscape.",
    "modules": [
        {
            "id": "erp-101",
            "title": "ERP 101",
            "order": 1,
            "content": """**What is ERP?** ERP stands for Enterprise Resource Planning. It's software that helps companies manage day-to-day business operations in one system: finance, accounting, inventory, orders, and often HR and supply chain.

**Why it matters:** Instead of spreadsheets and disconnected tools, ERP gives a single source of truth. Finance teams can close the books faster, report accurately, and scale without chaos. For venture-backed companies, the choice is often between legacy ERP (NetSuite, SAP, Oracle) and modern, AI-native platforms built for speed and automation.""",
            "suggested_questions": [
                "What is ERP and why does it matter for startups?",
                "How do companies use ERP for finance and accounting?",
            ],
        },
        {
            "id": "erp-legacy-vs-modern",
            "title": "Legacy vs modern ERP",
            "order": 2,
            "content": """**Legacy ERP** (NetSuite, SAP, Oracle, QuickBooks) often means long implementations, heavy customization, and interfaces built for an earlier era. They're powerful but can be slow to deploy and expensive to maintain.

**Modern ERP** focuses on faster time-to-value, better UX, and automation. AI-native ERP adds intelligent workflows (e.g. AI-assisted closing, automated reconciliation) and is built for how teams work today—often with a conversational or assistant-style interface.

**Campfire's position:** We're in the modern, AI-native camp: built for finance and accounting teams at venture-funded companies, with Ember AI (Claude-powered), multi-entity out of the box, and automation as a core differentiator.""",
            "suggested_questions": [
                "How does Campfire differ from NetSuite or QuickBooks?",
                "What does AI-native ERP mean?",
            ],
        },
        {
            "id": "erp-campfire-place",
            "title": "Campfire's place in the market",
            "order": 3,
            "content": """**Who we serve:** Finance and accounting teams at fast-growing, venture-backed companies (e.g. Replit, PostHog, Decagon, Heidi Health, CloudZero). These teams need accuracy, speed, and scalability without the overhead of legacy implementations.

**What we offer:** AI-native ERP with Ember AI (Claude-powered) for conversational finance workflows, multi-entity support, and deep automation for general ledger, revenue recognition, and reporting. We compete with NetSuite, QuickBooks, Oracle, and SAP by offering faster implementation, better UX, and built-in intelligence.

**Key differentiators:** Automation first, multi-entity out of the box, modern stack, and a product built for the way modern finance teams work.""",
            "suggested_questions": [
                "What is Ember AI and how do we use it?",
                "Who are Campfire's main customers and why do they choose us?",
            ],
        },
    ],
}

# Accounting path (Accounting 101 → GL → Revenue recognition)
ACCOUNTING_PATH = {
    "id": "accounting",
    "title": "Accounting fundamentals",
    "description": "Core accounting concepts you'll hear in finance and at Campfire.",
    "modules": [
        {
            "id": "acct-101",
            "title": "Accounting 101",
            "order": 1,
            "content": """**What accounting does:** Accounting records, summarizes, and reports financial transactions. It answers: What did we earn? What do we owe? What do we own? The outputs are financial statements (income statement, balance sheet, cash flow) that stakeholders and regulators rely on.

**Why it matters for Campfire:** Our product automates and streamlines accounting workflows. Understanding the basics helps you talk to customers and internal teams about what we're improving: faster closes, accurate books, and less manual work.""",
            "suggested_questions": [
                "What is the role of accounting in a company?",
                "What are the main financial statements?",
            ],
        },
        {
            "id": "acct-gl",
            "title": "General ledger (GL)",
            "order": 2,
            "content": """**General ledger (GL)** is the core record of all financial transactions. Every sale, expense, transfer, and adjustment is recorded as entries in the GL. It's the foundation for financial reporting and closing the books.

**In practice:** Finance teams post transactions (often from subledgers like AR, AP, payroll) into the GL. At period end they reconcile, run reports, and close. Campfire's GL is designed for multi-entity and automation—reducing manual journal entries and speeding up the close.""",
            "suggested_questions": [
                "What is general ledger and how does Campfire handle it?",
                "What is a subledger and how does it relate to the GL?",
            ],
        },
        {
            "id": "acct-revenue",
            "title": "Revenue recognition",
            "order": 3,
            "content": """**Revenue recognition** is the rule set for when and how a company records revenue. For subscription businesses, revenue is often recognized over time (e.g. monthly) rather than all at once. Standards like ASC 606 (US) define how to do this consistently.

**Why it matters:** Getting revenue recognition right affects reported revenue, compliance, and investor trust. Campfire helps automate revenue recognition and reporting so finance teams can stay compliant and close faster.""",
            "suggested_questions": [
                "What is revenue recognition and why does it matter?",
                "How does Campfire support revenue recognition?",
            ],
        },
    ],
}

ALL_PATHS = [ERP_PATH, ACCOUNTING_PATH]


def get_all_paths():
    """Return all learning paths (list of path summaries: id, title, description, module_count)."""
    return [
        {
            "id": p["id"],
            "title": p["title"],
            "description": p["description"],
            "module_count": len(p.get("modules", [])),
        }
        for p in ALL_PATHS
    ]


def get_path(path_id: str):
    """Return a single path by id with full modules, or None."""
    for p in ALL_PATHS:
        if p["id"] == path_id:
            modules = sorted(p.get("modules", []), key=lambda m: m.get("order", 0))
            return {
                "id": p["id"],
                "title": p["title"],
                "description": p["description"],
                "modules": modules,
            }
    return None


def get_module(path_id: str, module_id: str):
    """Return a single module by path_id and module_id, or None."""
    path = get_path(path_id)
    if not path:
        return None
    for m in path.get("modules", []):
        if m["id"] == module_id:
            return m
    return None


def get_module_context_for_ask(path_id: str, module_id: str) -> Optional[str]:
    """
    Return a short context string to prepend to the user's question when they
    click "Ask the assistant" from a module. Used by RAG to scope the answer.
    """
    mod = get_module(path_id, module_id)
    if not mod:
        return None
    title = mod.get("title") or ""
    content = (mod.get("content") or "").strip()
    if not content:
        return f"Learning module: {title}."
    # First 500 chars of content as context
    snippet = content[:500] + "..." if len(content) > 500 else content
    return f"Learning module: {title}. Context: {snippet}"
