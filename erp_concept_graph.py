"""
ERP Skill Map + Knowledge Graph.
Concepts with dependencies; supports "recommend next", gaps, and why-it-matters.
Uses neutral, industry-standard terms only.
"""
from typing import Optional

# Flat list of concepts: id, title, description, why_it_matters, depends_on (ids), suggested_questions
CONCEPTS = [
    {
        "id": "erp",
        "title": "ERP",
        "description": "Enterprise resource planning (ERP) is software that helps organizations manage day-to-day business: accounting, procurement, project management, supply chain, and more. ERP ties together business processes and keeps data in one place so teams have a single source of truth.",
        "why_it_matters": "Finance and operations run on accurate, shared data. ERP replaces spreadsheets and disconnected tools so you can close faster, report correctly, and scale without chaos.",
        "depends_on": [],
        "suggested_questions": ["What is ERP and why does it matter?", "How do companies use ERP for finance?"],
    },
    {
        "id": "what-is-erp",
        "title": "What is ERP?",
        "description": "ERP stands for enterprise resource planning. It’s a type of software that organizations use to manage daily activities like accounting, procurement, project management, risk and compliance, and supply chain. A full ERP suite can also include planning, budgeting, and reporting on financial results.",
        "why_it_matters": "Understanding what ERP is helps you see how finance, operations, and reporting fit together. It’s the foundation for everything from general ledger to revenue recognition.",
        "depends_on": ["erp"],
        "suggested_questions": ["What is an ERP system?", "What’s the difference between ERP and just financials?"],
    },
    {
        "id": "general-ledger",
        "title": "General Ledger",
        "description": "The general ledger (GL) is the core record of all financial transactions. Every sale, expense, transfer, and adjustment is recorded as entries. It’s the foundation for financial reporting and closing the books. Data often flows into the GL from subledgers (e.g. AR, AP, payroll).",
        "why_it_matters": "The GL is where all costs and revenue roll up. Getting it right means correct financial statements, audits, and decisions. Modern ERP automates posting and reconciliation to speed up the close.",
        "depends_on": ["erp"],
        "suggested_questions": ["What is general ledger and how does Campfire handle it?", "What is a subledger and how does it relate to the GL?"],
    },
    {
        "id": "chart-of-accounts",
        "title": "Chart of Accounts",
        "description": "The chart of accounts (COA) is the list of accounts used to classify transactions in the general ledger. Each account has a type (asset, liability, equity, revenue, expense) and often a code. Consistent COA across the company keeps reporting and roll-ups meaningful.",
        "why_it_matters": "Without a clear COA, you can’t compare periods or entities or report correctly. ERP keeps one defined structure so data is normalized and reportable.",
        "depends_on": ["general-ledger"],
        "suggested_questions": ["What is a chart of accounts?", "How does multi-entity affect the chart of accounts?"],
    },
    {
        "id": "journal-entries",
        "title": "Journal Entries",
        "description": "Journal entries are the mechanism for recording transactions in the general ledger. Each entry has a date, accounts, debits and credits, and often a description or reference. Manual entries are common for adjustments; automation can reduce them.",
        "why_it_matters": "Every number in the books got there via journal entries. Understanding them helps you trace data and trust the close. Automation cuts errors and speed.",
        "depends_on": ["general-ledger"],
        "suggested_questions": ["What are journal entries?", "How does Campfire reduce manual journal entries?"],
    },
    {
        "id": "period-close",
        "title": "Period Close",
        "description": "Period close is the process of finalizing the books for a reporting period (e.g. month or quarter): reconciling accounts, posting adjustments, running reports, and locking the period. It’s when the GL is declared complete for that period.",
        "why_it_matters": "Closing on time and accurately drives reporting, audits, and investor trust. Faster close means faster insight and less last-minute firefighting.",
        "depends_on": ["general-ledger", "journal-entries"],
        "suggested_questions": ["What is a period close?", "How does Campfire speed up the close?"],
    },
    {
        "id": "revenue-recognition",
        "title": "Revenue Recognition",
        "description": "Revenue recognition is the set of rules for when and how a company records revenue. For subscriptions, revenue is often recognized over time (e.g. monthly) rather than upfront. Standards like ASC 606 (US) define how to do this consistently.",
        "why_it_matters": "Correct revenue recognition affects reported revenue, compliance, and investor trust. Getting it wrong can mean restatements and lost confidence.",
        "depends_on": ["erp"],
        "suggested_questions": ["What is revenue recognition and why does it matter?", "How does Campfire support revenue recognition?"],
    },
    {
        "id": "contracts",
        "title": "Contracts",
        "description": "In revenue recognition, contracts are agreements with customers that create rights and obligations. Under ASC 606, you identify the contract, performance obligations, transaction price, and then allocate and recognize revenue over time or at a point in time.",
        "why_it_matters": "Contracts drive what you owe the customer and when you can book revenue. ERP that understands contracts automates allocation and schedules.",
        "depends_on": ["revenue-recognition"],
        "suggested_questions": ["How do contracts affect revenue recognition?", "What is a performance obligation?"],
    },
    {
        "id": "performance-obligations",
        "title": "Performance Obligations",
        "description": "A performance obligation is a promise to transfer a good or service to a customer. Under ASC 606, you identify distinct performance obligations in a contract and recognize revenue when each is satisfied (over time or at a point in time).",
        "why_it_matters": "Splitting contracts into performance obligations determines the timing of revenue. Subscription software often has one obligation satisfied over time.",
        "depends_on": ["revenue-recognition", "contracts"],
        "suggested_questions": ["What is a performance obligation?", "How does Campfire handle subscription revenue?"],
    },
    {
        "id": "revrec-schedules",
        "title": "Rev Rec Schedules",
        "description": "Revenue recognition schedules show when and how much revenue is recognized for a contract. They’re built from contract terms, performance obligations, and the chosen pattern (e.g. straight-line over term). Automation keeps schedules in sync with contract changes.",
        "why_it_matters": "Schedules are what finance uses to post revenue each period. Automating them reduces manual spreadsheets and errors.",
        "depends_on": ["revenue-recognition", "performance-obligations"],
        "suggested_questions": ["What is a revenue recognition schedule?", "How does Campfire automate rev rec?"],
    },
    {
        "id": "financials",
        "title": "Financials",
        "description": "Financials here means the finance-related parts of ERP: financial accounting, subledger accounting, payables and receivables, billing, expense management, and reporting. Financials produce the numbers that go into financial statements and regulatory filings.",
        "why_it_matters": "Financials are the core of what finance teams own. ERP that integrates financials with operations gives one source of truth for reporting.",
        "depends_on": ["erp"],
        "suggested_questions": ["What’s the difference between ERP and financials?", "What are the main financial statements?"],
    },
    {
        "id": "financial-statements",
        "title": "Financial Statements",
        "description": "The main outputs of the books are the income statement (revenue, expenses, profit), balance sheet (assets, liabilities, equity), and cash flow statement. They’re built from the general ledger and must comply with standards (e.g. GAAP, IFRS).",
        "why_it_matters": "Stakeholders and regulators rely on these statements. ERP that closes and reports quickly gets these out on time.",
        "depends_on": ["financials", "general-ledger"],
        "suggested_questions": ["What are the main financial statements?", "How does Campfire help with reporting?"],
    },
    {
        "id": "payables-receivables",
        "title": "Payables & Receivables",
        "description": "Accounts payable (AP) is what you owe vendors; accounts receivable (AR) is what customers owe you. These are often managed in subledgers that feed into the general ledger. Automation can match POs to invoices and track customer payments.",
        "why_it_matters": "AP and AR drive cash flow and accuracy. Integrated with the GL, they keep the books correct without manual rekeying.",
        "depends_on": ["financials", "general-ledger"],
        "suggested_questions": ["What are payables and receivables?", "How do subledgers feed the GL?"],
    },
    {
        "id": "integrations",
        "title": "Integrations",
        "description": "ERP often connects to other systems: billing (Stripe), CRM (Salesforce), banks, payroll, and more. Integrations move data in and out so the GL and reports stay current without manual entry.",
        "why_it_matters": "Companies already use Stripe, Salesforce, and bank feeds. ERP that integrates well reduces duplicate entry and errors.",
        "depends_on": ["erp"],
        "suggested_questions": ["What integrations does Campfire support?", "How does data get into the general ledger?"],
    },
    {
        "id": "stripe",
        "title": "Stripe",
        "description": "Stripe is a common billing and payments platform. ERP integrations with Stripe can sync customers, subscriptions, invoices, and payment events so revenue and cash are recorded automatically.",
        "why_it_matters": "Many startups bill through Stripe. Connecting it to ERP automates revenue and receivables and keeps the books in sync.",
        "depends_on": ["integrations", "revenue-recognition"],
        "suggested_questions": ["How does Campfire integrate with Stripe?", "How does Stripe data flow into the GL?"],
    },
    {
        "id": "salesforce",
        "title": "Salesforce",
        "description": "Salesforce is a CRM used for deals, contacts, and contracts. ERP–CRM integration can sync contract and customer data so revenue recognition and reporting use the same source.",
        "why_it_matters": "When sales and finance use the same contract and customer data, rev rec and reporting stay aligned.",
        "depends_on": ["integrations"],
        "suggested_questions": ["Does Campfire integrate with Salesforce?", "How does CRM data feed into ERP?"],
    },
    {
        "id": "banks",
        "title": "Banks",
        "description": "Bank feeds connect bank accounts to ERP so transactions (deposits, payments, fees) flow in automatically. That supports reconciliation and cash reporting without manual entry.",
        "why_it_matters": "Bank feeds are table stakes for modern finance. They keep the cash side of the books current and reduce manual work.",
        "depends_on": ["integrations", "general-ledger"],
        "suggested_questions": ["How does Campfire connect to banks?", "How is bank data used in the close?"],
    },
    {
        "id": "deployment-models",
        "title": "Cloud vs On-Premises",
        "description": "ERP can run on-premises (your own servers) or in the cloud (hosted by a vendor, often as SaaS). Cloud ERP is updated by the vendor, scales without you buying hardware, and is accessible from anywhere. On-premises gives more control but more upkeep.",
        "why_it_matters": "Cloud ERP is the norm for modern teams: faster to adopt, always current, and built for distributed work. Campfire is cloud-native.",
        "depends_on": ["erp"],
        "suggested_questions": ["What’s the difference between cloud and on-premises ERP?", "Why choose cloud ERP?"],
    },
    {
        "id": "campfire-context",
        "title": "Campfire's Place",
        "description": "Campfire builds AI-native ERP for finance and accounting teams at fast-growing, venture-backed companies. We focus on general ledger, revenue recognition, multi-entity, and automation, with a conversational assistant (Ember AI) for finance workflows. We compete on speed, UX, and built-in intelligence.",
        "why_it_matters": "Knowing where Campfire sits helps you position us: modern, AI-first, and built for how finance teams work today—not legacy implementations.",
        "depends_on": ["erp", "general-ledger", "revenue-recognition"],
        "suggested_questions": ["What is Ember AI and how do we use it?", "Who are Campfire's main customers and why do they choose us?"],
    },
]

# Tree structure: children by id (for Skill Map display)
CHILDREN_MAP = {
    "erp": ["what-is-erp", "general-ledger", "revenue-recognition", "financials", "integrations", "deployment-models", "campfire-context"],
    "general-ledger": ["chart-of-accounts", "journal-entries", "period-close"],
    "revenue-recognition": ["contracts", "performance-obligations", "revrec-schedules"],
    "financials": ["financial-statements", "payables-receivables"],
    "integrations": ["stripe", "salesforce", "banks"],
}


def _concept_by_id(cid: str) -> Optional[dict]:
    for c in CONCEPTS:
        if c["id"] == cid:
            return c
    return None


def get_concept_graph():
    """Return full concept graph: list of concepts with children and dependency info."""
    by_id = {c["id"]: {**c, "children": CHILDREN_MAP.get(c["id"], [])} for c in CONCEPTS}
    return {"concepts": list(by_id.values()), "root_id": "erp"}


def get_concept(concept_id: str) -> Optional[dict]:
    """Return a single concept by id with children and depends_on details."""
    c = _concept_by_id(concept_id)
    if not c:
        return None
    children = CHILDREN_MAP.get(concept_id, [])
    dep_details = []
    for dep_id in c.get("depends_on", []):
        d = _concept_by_id(dep_id)
        if d:
            dep_details.append({"id": d["id"], "title": d["title"]})
    return {
        **c,
        "children": children,
        "depends_on_details": dep_details,
    }


def get_recommend_next(completed_ids: list) -> list:
    """Given a list of completed concept ids, return concepts that are ready to learn next (all deps satisfied)."""
    completed = set(completed_ids or [])
    out = []
    for c in CONCEPTS:
        cid = c["id"]
        if cid in completed:
            continue
        deps = set(c.get("depends_on") or [])
        if deps and deps <= completed:
            out.append({"id": c["id"], "title": c["title"], "description": c.get("description", "")[:120]})
    return out


def get_concept_context_for_ask(concept_id: str) -> Optional[str]:
    """Short context string for RAG when user asks from a concept."""
    c = _concept_by_id(concept_id)
    if not c:
        return None
    title = c.get("title") or ""
    desc = (c.get("description") or "").strip()[:400]
    return f"Concept: {title}. {desc}"
