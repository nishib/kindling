"""RAG pipeline: Gemini embeddings, pgvector search, Gemini LLM synthesis with citations."""
import json
import os
import re
from typing import Optional

from sqlalchemy import select
from sqlalchemy.orm import Session

from models import KnowledgeItem, CompetitorIntel

# API key from environment only; never hardcode or log
_GEMINI_KEY = "GEMINI_API_KEY"
_EMBED_MODEL = "models/gemini-embedding-001"
_LLM_MODEL = "models/gemini-2.0-flash"
_EMBED_DIM = 768
_TOP_K = 5
_TOP_K_BRIEF = 25  # more context for daily brief
_REQUEST_TIMEOUT_MS = 45_000  # 45 seconds for generate/embed
_BRIEF_TIMEOUT_MS = 60_000  # 60s for brief (larger output)


def _client():
    """Return Gemini client if key is set, else None. Key is read from env only."""
    api_key = os.environ.get(_GEMINI_KEY)
    if not api_key:
        return None
    try:
        from google import genai
        return genai.Client(api_key=api_key)
    except Exception:
        return None


def get_embedding(text: str, task_type: str = "RETRIEVAL_QUERY") -> Optional[list]:
    """
    Get 768-dim embedding from Gemini. task_type: RETRIEVAL_QUERY for questions,
    RETRIEVAL_DOCUMENT for documents. Returns None if key missing or API fails.
    """
    client = _client()
    if not client:
        return None
    try:
        from google.genai import types
        config = types.EmbedContentConfig(
            task_type=task_type,
            output_dimensionality=_EMBED_DIM,
        )
        result = client.models.embed_content(
            model=_EMBED_MODEL,
            contents=text,
            config=config,
        )
        if not result.embeddings:
            return None
        emb = result.embeddings[0]
        values = getattr(emb, "values", None) or getattr(emb, "embedding", None)
        if values is None and hasattr(emb, "__iter__"):
            values = list(emb)
        return values if isinstance(values, list) else list(values) if values else None
    except Exception:
        return None


def search_similar(db: Session, query_embedding: list, k: int = _TOP_K):
    """Return up to k KnowledgeItems nearest to query_embedding (cosine distance)."""
    if not query_embedding or len(query_embedding) != _EMBED_DIM:
        return []
    try:
        stmt = (
            select(KnowledgeItem)
            .where(KnowledgeItem.embedding.isnot(None))
            .order_by(KnowledgeItem.embedding.cosine_distance(query_embedding))
            .limit(k)
        )
        return list(db.scalars(stmt).all())
    except (AttributeError, TypeError):
        # Fallback: order by id when .cosine_distance not available (e.g. older pgvector)
        stmt = (
            select(KnowledgeItem)
            .where(KnowledgeItem.embedding.isnot(None))
            .order_by(KnowledgeItem.id)
            .limit(k)
        )
        return list(db.scalars(stmt).all())


def _format_context(item: KnowledgeItem) -> dict:
    """Build citation-friendly context from a KnowledgeItem."""
    meta = item.metadata_ or {}
    title = meta.get("title") or meta.get("repo_name") or meta.get("channel") or item.source
    if meta.get("author"):
        title = f"{title} ({meta['author']})"
    snippet = (item.content or "")[:400].strip()
    if len((item.content or "")) > 400:
        snippet += "..."
    return {
        "source": item.source,
        "title": str(title),
        "snippet": snippet,
        "content": item.content,
    }


def _first_sentence(text: str, max_len: int = 200) -> str:
    """Return the first sentence or first max_len chars of text, trimmed."""
    if not text or not text.strip():
        return ""
    text = text.strip()
    for end in (". ", ".\n", "! ", "? "):
        i = text.find(end)
        if i != -1:
            return text[: i + 1].strip()
    return text[:max_len].strip() + ("..." if len(text) > max_len else "")


_COMPETITOR_KEYWORDS = (
    "netsuite", "sap", "quickbooks", "oracle", "competitor", "competitors",
    "pricing", "competition", "market", "rival", "erp", "compare",
)


def _is_competitor_question(question: str) -> bool:
    """Heuristic: question likely about competitors or external research."""
    q = (question or "").lower().strip()
    return any(k in q for k in _COMPETITOR_KEYWORDS)


def _enhance_query_for_competitive_search(question: str) -> str:
    """
    Transform user's question into a competitive/market-focused search query.
    Automatically detects question topic and adds relevant competitive/market context.
    Example: "What is our main product?" -> "main product competition market alternatives"
    """
    q = (question or "").strip().lower()

    # Remove common question words to extract core topic
    q_cleaned = q
    for phrase in ["what is", "what are", "what's", "who is", "who are", "how does", "tell me about", "give me"]:
        q_cleaned = q_cleaned.replace(phrase, "")
    q_cleaned = q_cleaned.replace("our", "").replace("the", "")
    q_cleaned = q_cleaned.replace("?", "").strip()

    # Topic-based competitive query enhancement
    # Product & Features
    if any(k in q for k in ["product", "platform", "solution", "offering"]):
        return f"ERP finance accounting {q_cleaned} NetSuite SAP QuickBooks comparison market"

    # Pricing & Business Model
    elif any(k in q for k in ["pricing", "price", "cost", "plan", "subscription", "tier"]):
        return f"ERP accounting software {q_cleaned} pricing NetSuite QuickBooks comparison"

    # Features & Capabilities
    elif any(k in q for k in ["feature", "capability", "function", "tool", "automation", "general ledger", "revenue"]):
        return f"ERP finance {q_cleaned} competitive analysis NetSuite SAP features comparison"

    # Competitors
    elif any(k in q for k in ["competitor", "competition", "rival", "versus", "vs", "netsuite", "sap", "quickbooks", "oracle"]):
        return f"ERP {q_cleaned} competitive landscape NetSuite SAP QuickBooks Oracle market"

    # Tech Stack & Architecture
    elif any(k in q for k in ["tech stack", "technology", "architecture", "infrastructure", "framework", "database"]):
        return f"ERP platform {q_cleaned} technology stack finance accounting industry"

    # Team & Company
    elif any(k in q for k in ["team", "founder", "employee", "people", "culture", "hiring"]):
        return f"ERP startup Campfire {q_cleaned} company team funding market"

    # Roadmap & Strategy
    elif any(k in q for k in ["roadmap", "future", "plan", "strategy", "vision", "upcoming"]):
        return f"ERP industry {q_cleaned} trends AI-native finance accounting market direction"

    # Sales & Go-to-Market
    elif any(k in q for k in ["sales", "customer", "client", "deal", "revenue", "growth"]):
        return f"ERP market {q_cleaned} sales venture-funded startups finance operations"

    # Onboarding & Implementation
    elif any(k in q for k in ["onboard", "implementation", "setup", "getting started", "integration"]):
        return f"ERP {q_cleaned} onboarding implementation best practices finance"

    # Daily Brief / Summary requests
    elif any(k in q for k in ["brief", "summary", "update", "news", "recent"]):
        return f"ERP finance accounting industry news updates competitive landscape trends"

    # Generic enhancement: add ERP market context
    else:
        return f"ERP finance accounting {q_cleaned} market NetSuite SAP QuickBooks alternatives"


def _recent_knowledge_for_brief(db: Session, limit: int = _TOP_K_BRIEF) -> list:
    """Return recent knowledge items (by created_at) for daily brief—no query embedding."""
    try:
        stmt = (
            select(KnowledgeItem)
            .order_by(KnowledgeItem.created_at.desc())
            .limit(limit)
        )
        return list(db.scalars(stmt).all())
    except Exception:
        return []


def _competitor_context_items(db: Session, question: str, limit: int = 5) -> list[dict]:
    """
    Fetch competitor context for RAG: cached DB intel + live You.com search.

    Uses enhanced You.com integration: customer search (Replit, PostHog, etc.) and
    accounting/ERP explainer search when the question mentions them; results are
    cached in YouComCache. Also runs general competitive search with query enhancement.
    """
    from sqlalchemy import select
    from you_com import live_search_for_rag_with_customer_and_explainer

    items = []
    # Always include cached competitor intel (fast)
    stmt = (
        select(CompetitorIntel)
        .order_by(CompetitorIntel.created_at.desc())
        .limit(limit)
    )
    rows = list(db.scalars(stmt).all())
    for r in rows:
        items.append({
            "source": "you_com",
            "title": f"{r.competitor_name} ({r.intel_type})",
            "snippet": (r.content or "")[:300],
            "content": r.content,
        })
    # Enhanced: customer + explainer + general live search (cached where possible)
    enhanced_query = _enhance_query_for_competitive_search(question)
    live = live_search_for_rag_with_customer_and_explainer(
        question, db=db, enhanced_query=enhanced_query, max_items=5, customer_explainer_max=2
    )
    for c in live[:8]:
        items.append(c)
    return items


_LEVEL_INSTRUCTIONS = {
    "beginner": (
        "The user is new to ERP and finance concepts. Use simple language, avoid jargon, "
        "and explain acronyms (e.g. ERP = Enterprise Resource Planning). Use short sentences and analogies where helpful."
    ),
    "intermediate": (
        "The user has some familiarity with business systems. Use standard terminology but "
        "briefly clarify domain terms when relevant. Balance clarity with depth."
    ),
    "advanced": (
        "The user is experienced with ERP or finance. You may use technical terms (GL, revenue recognition, "
        "multi-entity, etc.) and include nuance, comparisons, and competitive context where appropriate."
    ),
}


def generate_answer(
    question: str,
    context_items: list,
    competitor_context: Optional[list] = None,
    knowledge_level: Optional[str] = None,
) -> tuple[str, list]:
    """
    Use Gemini to synthesize an answer from retrieved contexts + optional competitor intel.
    knowledge_level: beginner | intermediate | advanced (Phase 1 – adapt vocabulary and depth).
    Returns (answer_text, citations). citations: list of {source, title, snippet} for UI.
    """
    client = _client()
    contexts = [_format_context(it) for it in context_items]
    if competitor_context:
        contexts.extend(competitor_context)
    citations = [{"source": c["source"], "title": c["title"], "snippet": c["snippet"]} for c in contexts]

    level_instruction = ""
    if knowledge_level and knowledge_level in _LEVEL_INSTRUCTIONS:
        level_instruction = f"\nAdaptation: {_LEVEL_INSTRUCTIONS[knowledge_level]}"

    if not client or not contexts:
        if not contexts:
            return "I couldn't find relevant information in the knowledge base. Please try rephrasing your question.", []
        # Fallback: short synthesis from top context (no dump)
        c0 = contexts[0]
        fallback = f"According to [{c0['source']}: {c0['title']}], {_first_sentence(c0.get('snippet') or c0.get('content', ''))}"
        if len(contexts) > 1:
            c1 = contexts[1]
            s1 = _first_sentence(c1.get('snippet') or c1.get('content', ''))
            if s1:
                fallback += f" Additionally, [{c1['source']}: {c1['title']}] notes that {s1}"
        fallback += "."
        return fallback, citations

    try:
        from google.genai import types
        context_blob = "\n\n---\n\n".join(
            f"[Source: {c['source']} – {c['title']}]\n{c['content']}" for c in contexts
        )
        prompt = f"""You are the Campfire ERP Onboarding Assistant. You help new Campfire employees learn:
- ERP fundamentals (what ERP is, why it matters, core components like general ledger, revenue automation).
- Traditional ERP landscape (NetSuite, SAP, Oracle, QuickBooks) vs modern/AI-native ERP.
- Campfire's approach: AI-native ERP for finance & accounting, Ember AI (Claude-powered), multi-entity, automation; competing with legacy systems for venture-funded startups.
{level_instruction}

Rules:
- Use the provided context when answering. For general ERP/Campfire positioning you may use the role above if context is thin.
- Write a concise answer that directly addresses the question in 5–10 lines (short paragraphs or 3–5 bullet points).
- Synthesize the information; do not list or dump raw sources.
- Cite sources inline where relevant.
- Answer the question asked; do not just repeat the context.

Context:
{context_blob}

Question: {question}

Answer (5–10 lines, synthesized, with inline source citations):"""

        config_kw = {"temperature": 0.2, "max_output_tokens": 1024}
        try:
            config_kw["http_options"] = types.HttpOptions(timeout=_REQUEST_TIMEOUT_MS)
        except (TypeError, AttributeError):
            pass
        response = client.models.generate_content(
            model=_LLM_MODEL,
            contents=types.Part.from_text(prompt),
            config=types.GenerateContentConfig(**config_kw),
        )
        text = None
        if response.candidates:
            cand = response.candidates[0]
            finish = getattr(cand, "finish_reason", None) or getattr(cand, "finishReason", None)
            if str(finish).upper() in ("BLOCKED", "SAFETY", "RECITATION"):
                text = None
            else:
                part = cand.content.parts[0] if cand.content.parts else None
                if part:
                    text = getattr(part, "text", None) or str(part)
        if not text or not str(text).strip():
            text = "I couldn't generate an answer. Please try rephrasing."
        return str(text).strip(), citations
    except Exception:
        if contexts:
            # Synthesize a short summary from top 1–2 contexts instead of dumping all
            c0 = contexts[0]
            fallback = f"According to [{c0['source']}: {c0['title']}], {_first_sentence(c0.get('snippet') or c0.get('content', ''))}"
            if len(contexts) > 1:
                c1 = contexts[1]
                s1 = _first_sentence(c1.get('snippet') or c1.get('content', ''))
                if s1:
                    fallback += f" Additionally, [{c1['source']}: {c1['title']}] notes that {s1}"
            fallback += "."
            return fallback, citations
        return "An error occurred while generating the answer.", []


_DAILY_BRIEF_SYSTEM = """You are an AI that generates a clean daily product brief from raw, unstructured inputs (knowledge base and web/intel results).

The input will change every time and may be messy, incomplete, duplicated, or partially cut off.

Your job is to:
1. Normalize and clean the raw text (fix fragments, remove noise, deduplicate).
2. Extract only factual, decision-relevant updates.
3. Infer structure when the input is unstructured.
4. Rewrite everything in clear, concise, professional product-brief language.
5. Group related facts and merge overlapping points.

Output the final brief as a single JSON object with exactly these keys:
- summary: array of 1-2 strings (most important leadership-level takeaways, 1-2 sentences each)
- product: array of 1-2 strings (shipping updates; performance/reliability; bugs/incidents; 1-2 sentences each)
- sales: array of 1-2 strings (pipeline; customer objections; GTM/revenue; 1-2 sentences each)
- company: array of 1-2 strings (strategy; positioning; competitive landscape; 1-2 sentences each)
- onboarding: array of 1-2 strings (onboarding process; success metrics; common issues; 1-2 sentences each)
- risks: array of 1-2 strings (product; market/competitive; execution/operational; 1-2 sentences each)

CRITICAL Rules:
- EVERY section must have at least 1 entry with 1-2 sentences. NEVER use empty arrays.
- If you cannot find specific information for a section, infer based on context or write a general statement.
- Each bullet should be exactly 1-2 sentences, no more, no less.
- Do NOT mention sources.
- Do NOT quote raw text; rewrite in your own words.
- If multiple items conflict, surface the conflict clearly in one bullet.
- Prioritize what leadership would care about today.
- Return ONLY valid JSON, no markdown code fence or extra text."""


def _raw_context_blob_for_brief(items: list, competitor_dicts: list) -> str:
    """Build a single raw text blob from knowledge + intel for the brief (no source labels)."""
    parts = []
    for it in items:
        content = (it.content or "").strip()
        if content:
            parts.append(content)
    for c in (competitor_dicts or []):
        content = (c.get("content") or c.get("snippet") or "").strip()
        if content:
            parts.append(content)
    return "\n\n---\n\n".join(parts)


def _parse_brief_json(text: str) -> dict:
    """Parse JSON from model output; tolerate markdown code block. Fill empty sections with fallback."""
    if not text or not str(text).strip():
        return {}
    raw = str(text).strip()
    # Strip optional markdown code fence
    for pattern in (r"^```(?:json)?\s*\n?(.*?)\n?```\s*$", r"^```\s*\n?(.*?)\n?```\s*$"):
        m = re.search(pattern, raw, re.DOTALL)
        if m:
            raw = m.group(1).strip()
    try:
        out = json.loads(raw)
        if not isinstance(out, dict):
            return {}
        # Normalize keys and ensure arrays with fallback for empty sections
        result = {}
        for key in ("summary", "product", "sales", "company", "onboarding", "risks"):
            val = out.get(key)
            if isinstance(val, list):
                items = [str(x).strip() for x in val if str(x).strip()]
                # If section is empty, add fallback message
                if not items:
                    items = ["Ask manager for more information."]
                result[key] = items
            else:
                result[key] = ["Ask manager for more information."]
        return result
    except json.JSONDecodeError:
        return {}


def generate_daily_brief(db: Session) -> dict:
    """
    Generate a structured daily product brief from recent knowledge + competitor intel.
    Returns { summary, product, sales, company, onboarding, risks } (each list of strings).
    """
    client = _client()
    items = _recent_knowledge_for_brief(db, limit=_TOP_K_BRIEF)
    competitor_rows = []
    try:
        stmt = (
            select(CompetitorIntel)
            .order_by(CompetitorIntel.created_at.desc())
            .limit(10)
        )
        competitor_rows = list(db.scalars(stmt).all())
    except Exception:
        pass
    competitor_dicts = [
        {"source": "you_com", "title": f"{r.competitor_name} ({r.intel_type})", "snippet": (r.content or "")[:500], "content": r.content}
        for r in competitor_rows
    ]
    context_blob = _raw_context_blob_for_brief(items, competitor_dicts)

    if not context_blob:
        return {
            "summary": ["No recent data available. Add content to the knowledge base or refresh intel to generate a brief."],
            "product": ["Ask manager for more information."],
            "sales": ["Ask manager for more information."],
            "company": ["Ask manager for more information."],
            "onboarding": ["Ask manager for more information."],
            "risks": ["Ask manager for more information."],
        }

    if not client:
        return {
            "summary": ["Brief generation requires GEMINI_API_KEY."],
            "product": ["Ask manager for more information."],
            "sales": ["Ask manager for more information."],
            "company": ["Ask manager for more information."],
            "onboarding": ["Ask manager for more information."],
            "risks": ["Ask manager for more information."],
        }

    try:
        from google.genai import types
        prompt = f"""{_DAILY_BRIEF_SYSTEM}

Raw context (do not mention these sources in the brief):

{context_blob[:120000]}

Respond with a single JSON object only (keys: summary, product, sales, company, onboarding, risks)."""

        config_kw = {"temperature": 0.2, "max_output_tokens": 2048}
        try:
            config_kw["http_options"] = types.HttpOptions(timeout=_BRIEF_TIMEOUT_MS)
        except (TypeError, AttributeError):
            pass
        response = client.models.generate_content(
            model=_LLM_MODEL,
            contents=types.Part.from_text(prompt),
            config=types.GenerateContentConfig(**config_kw),
        )
        text = None
        if response.candidates:
            cand = response.candidates[0]
            finish = getattr(cand, "finish_reason", None) or getattr(cand, "finishReason", None)
            if str(finish).upper() in ("BLOCKED", "SAFETY", "RECITATION"):
                text = None
            else:
                part = cand.content.parts[0] if cand.content.parts else None
                if part:
                    text = getattr(part, "text", None) or str(part)
        if not text or not str(text).strip():
            return {
                "summary": ["Could not generate brief. Try again or check API key."],
                "product": ["Ask manager for more information."],
                "sales": ["Ask manager for more information."],
                "company": ["Ask manager for more information."],
                "onboarding": ["Ask manager for more information."],
                "risks": ["Ask manager for more information."],
            }
        parsed = _parse_brief_json(str(text).strip())
        if not parsed:
            return {
                "summary": ["Brief response was not valid. Try again."],
                "product": ["Ask manager for more information."],
                "sales": ["Ask manager for more information."],
                "company": ["Ask manager for more information."],
                "onboarding": ["Ask manager for more information."],
                "risks": ["Ask manager for more information."],
            }
        return parsed
    except Exception:
        return {
            "summary": ["Brief generation failed. Ensure GEMINI_API_KEY is set and try again."],
            "product": ["Ask manager for more information."],
            "sales": ["Ask manager for more information."],
            "company": ["Ask manager for more information."],
            "onboarding": ["Ask manager for more information."],
            "risks": ["Ask manager for more information."],
        }


def ask(db: Session, question: str, knowledge_level: Optional[str] = None) -> dict:
    """
    Full RAG: embed question, search knowledge + competitor intel (You.com cache), generate answer.
    knowledge_level: beginner | intermediate | advanced for adaptive answers (Phase 1).
    Returns {answer, citations}. Competitor intel is included so answers cite You.com research.
    """
    import numpy as np
    query_embedding = get_embedding(question, task_type="RETRIEVAL_QUERY")
    if not query_embedding:
        np.random.seed(hash(question) % (2**32))
        query_embedding = np.random.randn(_EMBED_DIM).tolist()
    items = search_similar(db, query_embedding, k=_TOP_K)
    competitor_context = _competitor_context_items(db, question, limit=5)
    answer, citations = generate_answer(
        question, items, competitor_context=competitor_context, knowledge_level=knowledge_level
    )
    return {"answer": answer, "citations": citations}
