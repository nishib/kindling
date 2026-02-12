"""
Phase 4 – You.com Intelligence: live web + news search, cached competitor intel.
Chunk 4: customer search (per major customer), accounting/ERP explainer search; cache and feed RAG.
API key from environment only: YOU_API_KEY. Never hardcode or log.
ERP competitors (Campfire context): NetSuite, SAP, QuickBooks, Oracle.
"""
import os
import re
from datetime import datetime, timedelta
from typing import Optional

import httpx
from sqlalchemy.orm import Session

from models import CompetitorIntel, YouComCache

# Search API (returns both web and news)
_BASE = "https://ydc-index.io/v1"
# Live News API (news-only; may require early-access)
_NEWS_BASE = "https://api.ydc-index.io"
# ERP competitors for Campfire onboarding (Phase 4)
_COMPETITORS = [
    ("NetSuite", "product", "NetSuite ERP product updates pricing enterprise"),
    ("SAP", "market", "SAP ERP S/4HANA finance accounting market"),
    ("QuickBooks", "product", "QuickBooks accounting software small business"),
    ("Oracle", "market", "Oracle ERP Cloud finance accounting enterprise"),
]

# Major Campfire customers for customer search (Chunk 4)
_MAJOR_CUSTOMERS = [
    "Replit", "PostHog", "Decagon", "Heidi Health", "CloudZero",
]

# Accounting/ERP terms for explainer search (Chunk 4)
_EXPLAINER_TERMS = [
    "general ledger", "revenue recognition", "multi-entity", "ERP", "ASC 606",
    "chart of accounts", "accounts payable", "accounts receivable", "close the books",
    "subledger", "journal entry", "trial balance", "financial statements",
]

# Cache TTL for YouComCache (days)
_CACHE_TTL_DAYS = 7


def _headers() -> dict:
    key = os.environ.get("YOU_API_KEY")
    if not key:
        return {}
    return {"X-API-Key": key, "Accept": "application/json"}


def search(query: str, count: int = 10, freshness: str = "month") -> Optional[dict]:
    """You.com unified search (web + news). Returns raw response JSON or None."""
    if not _headers():
        return None
    try:
        r = httpx.get(
            f"{_BASE}/search",
            headers=_headers(),
            params={"query": query, "count": min(count, 20), "freshness": freshness},
            timeout=15.0,
        )
        r.raise_for_status()
        return r.json()
    except Exception:
        return None


def search_news(query: str, count: int = 10) -> Optional[dict]:
    """You.com Live News API (news-only). Returns raw response or None (e.g. if no early access)."""
    if not _headers():
        return None
    try:
        r = httpx.get(
            f"{_NEWS_BASE}/livenews",
            headers=_headers(),
            params={"q": query, "count": min(count, 40)},
            timeout=15.0,
        )
        r.raise_for_status()
        return r.json()
    except Exception:
        return None


def _normalize_web_hit(hit: dict) -> dict:
    """Normalize a web result for live search response."""
    url = hit.get("url") or ""
    title = hit.get("title") or ""
    desc = hit.get("description") or ""
    snippets = hit.get("snippets") or []
    content = desc or (snippets[0] if snippets else title) or url
    return {
        "title": (title or "").strip(),
        "content": (content[:1500] + "..." if len(content) > 1500 else content).strip(),
        "url": url[:512] if url else None,
        "thumbnail_url": (hit.get("thumbnail_url") or "").strip() or None,
    }


def _normalize_news_hit(hit: dict) -> dict:
    """Normalize a news result (unified search or livenews) for live search response."""
    url = hit.get("url") or ""
    title = hit.get("title") or ""
    desc = hit.get("description") or ""
    content = desc or title or url
    return {
        "title": (title or "").strip(),
        "content": (content[:1500] + "..." if len(content) > 1500 else content).strip(),
        "url": url[:512] if url else None,
        "thumbnail_url": (hit.get("thumbnail_url") or (hit.get("thumbnail") or {}).get("src") or "").strip() or None,
        "source_name": (hit.get("source_name") or "").strip() or None,
        "page_age": hit.get("page_age") or hit.get("age") or None,
    }


def live_search(query: str, count: int = 8, freshness: str = "month") -> dict:
    """
    Run live You.com search and return normalized web + news for the UI.
    Returns {"web": [...], "news": [...], "query": str}. Uses unified search (web + news in one call).
    """
    out = {"web": [], "news": [], "query": (query or "").strip()}
    if not out["query"] or not _headers():
        return out
    data = search(out["query"], count=count, freshness=freshness)
    if not data:
        return out
    results = data.get("results") or {}
    # Web results
    web = results.get("web") or []
    if isinstance(web, list):
        for hit in web[:count]:
            if isinstance(hit, dict) and (hit.get("title") or hit.get("description") or hit.get("snippets")):
                out["web"].append(_normalize_web_hit(hit))
    # News from same unified response
    news = results.get("news") or []
    if isinstance(news, list):
        for hit in news[:count]:
            if isinstance(hit, dict) and (hit.get("title") or hit.get("description")):
                out["news"].append(_normalize_news_hit(hit))
    # If no news in unified response, try Live News API (may 403 without early access)
    if not out["news"]:
        news_data = search_news(out["query"], count=min(count, 15))
        if news_data:
            news_obj = news_data.get("news") or {}
            news_list = news_obj.get("results") if isinstance(news_obj, dict) else []
            if isinstance(news_list, list):
                for hit in news_list[:count]:
                    if isinstance(hit, dict) and (hit.get("title") or hit.get("description")):
                        out["news"].append(_normalize_news_hit(hit))
    return out


def live_search_for_rag(question: str, max_items: int = 5) -> list[dict]:
    """
    Run live You.com search for a question and return RAG-style context items.
    Returns list of {source, title, snippet, content} for generate_answer.
    Used to augment RAG when the question is about competitors or external research.
    """
    out = []
    q = (question or "").strip()
    if not q or not _headers():
        return out
    result = live_search(q, count=max_items, freshness="month")
    for item in (result.get("web") or []) + (result.get("news") or []):
        title = (item.get("title") or "").strip()
        content = (item.get("content") or "").strip()
        if not content:
            continue
        source = "you_com_live"
        if item.get("source_name"):
            source = f"you_com_live ({item['source_name']})"
        out.append({
            "source": source,
            "title": title or "You.com result",
            "snippet": content[:300] + "..." if len(content) > 300 else content,
            "content": content,
        })
        if len(out) >= max_items:
            break
    return out


def _parse_web_results(data: dict, competitor_name: str, intel_type: str) -> list[dict]:
    """Parse You.com response into intel items: {competitor_name, intel_type, content, source_url}."""
    items = []
    results = data.get("results") or {}
    web = results.get("web") or []
    if not isinstance(web, list):
        return items
    for hit in web[:5]:
        if not isinstance(hit, dict):
            continue
        url = hit.get("url") or ""
        title = hit.get("title") or ""
        desc = hit.get("description") or ""
        snippets = hit.get("snippets") or []
        content = desc or (snippets[0] if snippets else title) or url
        if not content or len(content.strip()) < 20:
            continue
        items.append({
            "competitor_name": competitor_name,
            "intel_type": intel_type,
            "content": (content[:2000] + "..." if len(content) > 2000 else content).strip(),
            "source_url": url[:512] if url else None,
        })
    return items


def refresh_competitor_intel(db: Session) -> int:
    """
    Search You.com for NetSuite, SAP, QuickBooks, Oracle; store in CompetitorIntel (cached).
    Returns number of new items stored. Uses YOU_API_KEY from env only.
    """
    added = 0
    if not _headers():
        return 0
    for competitor_name, intel_type, query in _COMPETITORS:
        data = search(query, count=5, freshness="month")
        if not data:
            continue
        for item in _parse_web_results(data, competitor_name, intel_type):
            row = CompetitorIntel(
                competitor_name=item["competitor_name"],
                intel_type=item["intel_type"],
                content=item["content"],
                source_url=item.get("source_url"),
                created_at=datetime.utcnow(),
            )
            db.add(row)
            added += 1
    if added:
        db.commit()
    return added


def get_intel_feed(db: Session, limit: int = 20):
    """Return recent CompetitorIntel rows for feed (timeline)."""
    from sqlalchemy import select
    stmt = (
        select(CompetitorIntel)
        .order_by(CompetitorIntel.created_at.desc())
        .limit(limit)
    )
    return list(db.scalars(stmt).all())


# --- Customer & explainer search (Chunk 4): cache and RAG ---

def _cache_key(prefix: str, value: str) -> str:
    """Normalize cache key: prefix:normalized_value (lower, single spaces)."""
    normalized = re.sub(r"\s+", " ", (value or "").strip().lower())[:200]
    return f"{prefix}:{normalized}"


def _get_cached(db: Session, query_key: str, max_age_days: int = _CACHE_TTL_DAYS) -> list[dict] | None:
    """Return cached RAG-style items for query_key if any and not stale."""
    from sqlalchemy import select
    cutoff = datetime.utcnow() - timedelta(days=max_age_days)
    stmt = (
        select(YouComCache)
        .where(YouComCache.query_key == query_key, YouComCache.created_at >= cutoff)
        .order_by(YouComCache.created_at.desc())
    )
    rows = list(db.scalars(stmt).all())
    if not rows:
        return None
    return [
        {
            "source": "you_com_cached",
            "title": r.title or "You.com",
            "snippet": (r.content or "")[:300],
            "content": r.content,
        }
        for r in rows[:5]
    ]


def _save_cache(db: Session, query_key: str, query_type: str, items: list[dict]) -> None:
    """Save RAG-style items into YouComCache."""
    for item in items[:5]:
        row = YouComCache(
            query_key=query_key,
            query_type=query_type,
            content=item.get("content") or item.get("snippet") or "",
            source_url=item.get("url"),
            title=item.get("title") or "",
            created_at=datetime.utcnow(),
        )
        db.add(row)
    db.commit()


def _rag_items_from_live_search(query: str, max_items: int = 3) -> list[dict]:
    """Run live You.com search and return RAG-style list of dicts (source, title, snippet, content)."""
    result = live_search(query, count=max_items, freshness="month")
    out = []
    for item in (result.get("web") or []) + (result.get("news") or []):
        title = (item.get("title") or "").strip()
        content = (item.get("content") or "").strip()
        if not content:
            continue
        out.append({
            "source": "you_com_live",
            "title": title or "You.com result",
            "snippet": content[:300] + "..." if len(content) > 300 else content,
            "content": content,
            "url": item.get("url"),
        })
        if len(out) >= max_items:
            break
    return out


def customer_search(customer_name: str, db: Session | None = None, max_items: int = 3) -> list[dict]:
    """
    Search You.com for a major customer (what they do, why Campfire). Uses cache if db provided.
    Returns RAG-style list of {source, title, snippet, content}.
    """
    name = (customer_name or "").strip()
    if not name:
        return []
    key = _cache_key("customer", name)
    if db:
        cached = _get_cached(db, key)
        if cached:
            return cached
    query = f"{name} company what they do Campfire ERP finance accounting"
    items = _rag_items_from_live_search(query, max_items=max_items)
    if db and items:
        _save_cache(db, key, "customer", items)
    return items


def explainer_search(term: str, db: Session | None = None, max_items: int = 3) -> list[dict]:
    """
    Search You.com for an accounting/ERP term explanation. Uses cache if db provided.
    Returns RAG-style list of {source, title, snippet, content}.
    """
    t = (term or "").strip()
    if not t:
        return []
    key = _cache_key("explainer", t)
    if db:
        cached = _get_cached(db, key)
        if cached:
            return cached
    query = f"{t} accounting ERP definition explain finance"
    items = _rag_items_from_live_search(query, max_items=max_items)
    if db and items:
        _save_cache(db, key, "explainer", items)
    return items


def _detect_customers_in_question(question: str) -> list[str]:
    """Return list of major customer names mentioned in question (case-insensitive)."""
    q = (question or "").lower()
    return [c for c in _MAJOR_CUSTOMERS if c.lower() in q]


def _detect_explainer_terms_in_question(question: str) -> list[str]:
    """Return list of explainer terms mentioned in question (longest match first)."""
    q = (question or "").lower()
    found = []
    for term in sorted(_EXPLAINER_TERMS, key=len, reverse=True):
        if term.lower() in q and term not in found:
            found.append(term)
    return found


def live_search_for_rag_with_customer_and_explainer(
    question: str,
    db: Session | None = None,
    enhanced_query: str | None = None,
    max_items: int = 5,
    customer_explainer_max: int = 2,
) -> list[dict]:
    """
    Enhanced live_search_for_rag: run general You.com search plus customer/explainer-specific
    search when the question mentions known customers or accounting/ERP terms. Results are
    merged; cached explainer/customer results used when db is provided.
    enhanced_query: optional competitive/market-focused query for general search (from RAG).
    """
    seen = set()
    out = []

    # 1) Customer-specific search
    for customer in _detect_customers_in_question(question)[:2]:
        for item in customer_search(customer, db=db, max_items=customer_explainer_max):
            content = (item.get("content") or item.get("snippet") or "").strip()
            if content and content[:100] not in seen:
                seen.add(content[:100])
                item["source"] = f"you_com_customer ({customer})"
                out.append(item)

    # 2) Explainer search for accounting/ERP terms
    for term in _detect_explainer_terms_in_question(question)[:2]:
        for item in explainer_search(term, db=db, max_items=customer_explainer_max):
            content = (item.get("content") or item.get("snippet") or "").strip()
            if content and content[:100] not in seen:
                seen.add(content[:100])
                item["source"] = f"you_com_explainer ({term})"
                out.append(item)

    # 3) General competitive/live search (use enhanced_query when provided for better relevance)
    general_q = (enhanced_query or question).strip() or question
    general = live_search_for_rag(general_q, max_items=max_items)
    for item in general:
        content = (item.get("content") or item.get("snippet") or "").strip()
        if content and content[:100] not in seen:
            seen.add(content[:100])
            out.append(item)

    return out[: max_items + (customer_explainer_max * 4)]
