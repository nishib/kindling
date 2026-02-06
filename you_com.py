"""
Phase 4: You.com competitor intelligence.
API key from environment only: YOU_API_KEY. Never hardcode or log.
"""
import os
from datetime import datetime
from typing import Optional

import httpx
from sqlalchemy.orm import Session

from models import CompetitorIntel

# Read from env only
_BASE = "https://ydc-index.io/v1"
_COMPETITORS = [
    ("Intercom", "pricing", "Intercom customer support software pricing news"),
    ("Zendesk", "product", "Zendesk AI customer service product updates"),
    ("Gorgias", "market", "Gorgias e-commerce support growth funding"),
]


def _headers() -> dict:
    key = os.environ.get("YOU_API_KEY")
    if not key:
        return {}
    return {"X-API-Key": key, "Accept": "application/json"}


def search(query: str, count: int = 5, freshness: str = "month") -> Optional[dict]:
    """You.com search. Returns response JSON or None. Key from env only."""
    if not _headers():
        return None
    try:
        r = httpx.get(
            f"{_BASE}/search",
            headers=_headers(),
            params={"query": query, "count": min(count, 10), "freshness": freshness},
            timeout=15.0,
        )
        r.raise_for_status()
        return r.json()
    except Exception:
        return None


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
    Search You.com for Intercom, Zendesk, Gorgias; store in CompetitorIntel (cached).
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
