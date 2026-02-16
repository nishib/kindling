"""Competitor release-notes/docs crawler -> capability-level IntelEvents.

This replaces the old You.com-based competitor feed for the UI.

High-level flow:
- Dynamic competitor discovery + high-signal URL detection
- Sources: release notes, feature docs, deprecation notices, API changelogs
- On each crawl:
  - Fetch each URL.
  - Extract main content, split into H2/H3-based chunks.
  - Hash each chunk; compare against last-seen hashes stored in SyncState.
  - For any changed/new chunk, create an IntelEvent:
      - theme (AI, consolidation, reporting, integrations, etc.)
      - change_type (new capability, enhancement, deprecation, limitation)
      - claim (1 sentence)
      - beginner_summary (3 bullets in plain language)
      - evidence (URL + exact changed snippet)
"""

from __future__ import annotations

import hashlib
import logging
import re
from dataclasses import dataclass
from datetime import datetime
from typing import Any, Dict, List, Tuple, Set, Optional
from urllib.parse import urljoin, urlparse

import httpx

# Set up logging
logger = logging.getLogger(__name__)
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
)
try:
    from bs4 import BeautifulSoup  # type: ignore
except ImportError:
    BeautifulSoup = None  # graceful fallback when bs4 is not installed
from sqlalchemy import select
from sqlalchemy.orm import Session

from models import IntelEvent, SyncState
from rag import _client, _LLM_MODEL, _REQUEST_TIMEOUT_MS


@dataclass
class Source:
    competitor: str
    url: str
    label: str
    source_type: str  # "release_notes", "feature_docs", "api_changelog", "deprecation"


@dataclass
class Competitor:
    name: str
    website: str
    category: str  # "traditional", "modern", "mid-market"
    description: str
    priority: int  # 1=highest, 2=medium, 3=low
    enabled: bool = True  # Can disable specific competitors


# Core competitor registry (expandable)
# Top 5 priority: NetSuite, SAP, Workday, Rillet, DualEntry
_COMPETITORS: List[Competitor] = [
    # Traditional enterprise ERP
    Competitor("NetSuite", "https://www.netsuite.com", "traditional", "Cloud ERP for finance, accounting, and operations", priority=1),
    Competitor("SAP", "https://www.sap.com", "traditional", "Enterprise ERP with finance, supply chain, and HR", priority=1),
    Competitor("Workday", "https://www.workday.com", "traditional", "Cloud ERP for finance, HR, and planning", priority=1),
    Competitor("Oracle", "https://www.oracle.com", "traditional", "Cloud ERP for global multi-entity operations", priority=2),
    Competitor("Microsoft Dynamics 365", "https://dynamics.microsoft.com", "traditional", "Business applications for finance and operations", priority=2),
    Competitor("Sage Intacct", "https://www.sageintacct.com", "traditional", "Cloud accounting for mid-market", priority=2),

    # Modern AI-native competitors
    Competitor("Rillet", "https://www.rillet.com", "modern", "AI-native ERP for complex revenue models", priority=1),
    Competitor("DualEntry", "https://www.dualentry.com", "modern", "AI-native ERP with ML-powered automation", priority=1),
    Competitor("Digits", "https://digits.com", "modern", "AI-native accounting built for automation", priority=2),
    Competitor("Puzzle", "https://www.puzzle.io", "modern", "AI-powered accounting for startups", priority=2),

    # Mid-market alternatives
    Competitor("Acumatica", "https://www.acumatica.com", "mid-market", "Cloud ERP for growing businesses", priority=3),
    Competitor("SAP Business One", "https://www.sap.com/products/erp/business-one.html", "mid-market", "ERP for small and midsize businesses", priority=3),
    Competitor("Odoo", "https://www.odoo.com", "mid-market", "Open-source business apps suite", priority=3),
]


# High-signal URL patterns to look for when discovering sources
_URL_PATTERNS = {
    "release_notes": [
        r"release[-_]?notes?",
        r"whats[-_]?new",
        r"changelog",
        r"product[-_]?updates?",
        r"latest[-_]?updates?",
        r"announcements?",
    ],
    "feature_docs": [
        r"features?",
        r"capabilities",
        r"documentation",
        r"docs/.*features?",
        r"product[-_]?guide",
        r"user[-_]?guide",
    ],
    "api_changelog": [
        r"api.*changelog",
        r"api.*release",
        r"api.*updates?",
        r"developer.*changelog",
    ],
    "deprecation": [
        r"deprecat",
        r"sunset",
        r"end[-_]?of[-_]?life",
        r"eol",
        r"retiring",
    ],
}


def get_active_competitors(max_priority: int = 3) -> List[Competitor]:
    """
    Get active competitors filtered by priority.

    Args:
        max_priority: Include competitors with priority <= this value (1=top only, 3=all)

    Returns:
        List of enabled competitors within the priority threshold
    """
    return [
        c for c in _COMPETITORS
        if c.enabled and c.priority <= max_priority
    ]


def _fetch(url: str, timeout: float = 20.0) -> str | None:
    """Fetch URL with error handling."""
    try:
        resp = httpx.get(
            url,
            timeout=timeout,
            follow_redirects=True,
            headers={
                "User-Agent": "Mozilla/5.0 (compatible; CampfireBot/1.0; +https://campfire.ai)"
            }
        )
        resp.raise_for_status()
        return resp.text
    except Exception as e:
        logger.warning(f"Failed to fetch {url}: {e}")
        return None


def discover_sources(competitor: Competitor, max_sources: int = 15) -> List[Source]:
    """
    Discover high-signal documentation URLs for a competitor.

    Strategy:
    1. Fetch homepage
    2. Extract all links
    3. Match against high-signal patterns
    4. Return up to max_sources per competitor
    """
    if BeautifulSoup is None:
        logger.error("BeautifulSoup not available, cannot discover sources")
        return []

    logger.info(f"Discovering sources for {competitor.name}...")
    html = _fetch(competitor.website)
    if not html:
        logger.warning(f"Could not fetch homepage for {competitor.name}")
        return []

    soup = BeautifulSoup(html, "html.parser")
    discovered: List[Source] = []
    seen_urls: Set[str] = set()

    # Extract all links
    for link in soup.find_all("a", href=True):
        href = link.get("href", "")
        if not href:
            continue

        # Normalize URL
        full_url = urljoin(competitor.website, href)
        parsed = urlparse(full_url)

        # Filter: same domain only
        base_domain = urlparse(competitor.website).netloc
        if parsed.netloc and base_domain not in parsed.netloc:
            continue

        # Filter: no anchors, queries simplified
        clean_url = f"{parsed.scheme}://{parsed.netloc}{parsed.path}"
        if clean_url in seen_urls or len(discovered) >= max_sources:
            continue

        # Match against patterns
        url_lower = clean_url.lower()
        link_text = link.get_text(strip=True).lower()
        combined = f"{url_lower} {link_text}"

        for source_type, patterns in _URL_PATTERNS.items():
            for pattern in patterns:
                if re.search(pattern, combined, re.IGNORECASE):
                    label = link.get_text(strip=True) or parsed.path.split("/")[-1] or "Documentation"
                    discovered.append(
                        Source(
                            competitor=competitor.name,
                            url=clean_url,
                            label=label[:200],
                            source_type=source_type,
                        )
                    )
                    seen_urls.add(clean_url)
                    logger.debug(f"  Found {source_type}: {clean_url}")
                    break
            if clean_url in seen_urls:
                break

    logger.info(f"Discovered {len(discovered)} sources for {competitor.name}")
    return discovered


def get_all_sources(max_priority: int = 1) -> List[Source]:
    """
    Get all high-signal sources across competitors filtered by priority.

    Args:
        max_priority: Include only competitors with priority <= this value
                     1 = top 5 only (default), 3 = all competitors

    Returns:
        List of all discovered sources from active competitors
    """
    all_sources: List[Source] = []
    competitors = get_active_competitors(max_priority)

    logger.info(f"Discovering sources for {len(competitors)} competitors (priority <= {max_priority})")

    for competitor in competitors:
        sources = discover_sources(competitor, max_sources=15)
        all_sources.extend(sources)

    logger.info(f"Total sources discovered: {len(all_sources)}")
    return all_sources


def get_competitor_registry(max_priority: int = 1) -> List[Dict[str, Any]]:
    """
    Return registry grouped by competitor for the API/UI.

    Args:
        max_priority: Include only competitors with priority <= this value
    """
    sources = get_all_sources(max_priority)

    by_comp: Dict[str, Dict[str, Any]] = {}
    for src in sources:
        comp = by_comp.setdefault(
            src.competitor,
            {
                "competitor": src.competitor,
                "sources": [],
                "category": next((c.category for c in _COMPETITORS if c.name == src.competitor), "unknown"),
                "description": next((c.description for c in _COMPETITORS if c.name == src.competitor), ""),
                "priority": next((c.priority for c in _COMPETITORS if c.name == src.competitor), 3),
            },
        )
        comp["sources"].append({
            "url": src.url,
            "label": src.label,
            "type": src.source_type,
        })

    return list(by_comp.values())


def _extract_chunks(html: str, base_url: str = "") -> List[Tuple[str, str]]:
    """
    Extract (heading, text) chunks from HTML with improved logic.

    Strategy:
    - Prefer <main> or <article>; fall back to <body>.
    - Use H2/H3 headings as boundaries; collect paragraph text under each.
    - Include list items (li) for feature lists
    - Filter out navigation, footer, and sidebar content
    - If BeautifulSoup is unavailable, fall back to a single coarse chunk.
    """
    if BeautifulSoup is None:
        # Very coarse fallback: strip tags naively and return one chunk.
        text = re.sub(r"<[^>]+>", " ", html or "")
        text = " ".join(text.split())
        if len(text) < 200:
            return []
        return [("Page", text)]

    soup = BeautifulSoup(html, "html.parser")

    # Remove noise elements
    for noise in soup.find_all(["nav", "header", "footer", "aside", "script", "style"]):
        noise.decompose()

    root = soup.find("main") or soup.find("article") or soup.body
    if not root:
        return []

    chunks: List[Tuple[str, str]] = []
    current_heading = "Overview"
    current_text_parts: List[str] = []

    def flush():
        nonlocal current_heading, current_text_parts
        text = " ".join(t.strip() for t in current_text_parts if t.strip())
        if text and len(text) > 200:  # Only keep substantial chunks
            chunks.append((current_heading.strip() or "Overview", text))
        current_text_parts = []

    for el in root.descendants:
        name = getattr(el, "name", None)
        if name in ("h1", "h2", "h3"):
            flush()
            current_heading = el.get_text(separator=" ", strip=True) or current_heading
        elif name in ("p", "li", "td"):
            txt = el.get_text(separator=" ", strip=True)
            if txt and len(txt) > 20:  # Filter out very short snippets
                current_text_parts.append(txt)

    flush()
    return chunks


def _hash_chunk(heading: str, text: str) -> str:
    """Hash a chunk for change detection."""
    h = hashlib.sha256()
    h.update(heading.encode("utf-8"))
    h.update(b"\n")
    h.update(text.encode("utf-8"))
    return h.hexdigest()


def _load_state(db: Session) -> Dict[str, Dict[str, str]]:
    """
    Load last-seen chunk hashes from SyncState.
    Structure:
      { url: { heading_hash_key: chunk_hash } }
    """
    row = db.get(SyncState, "competitor_source_state")
    if not row or not isinstance(row.value, dict):
        return {}
    data = row.value or {}
    # Ensure nested dict[str, str]
    out: Dict[str, Dict[str, str]] = {}
    for url, chunks in data.items():
        if isinstance(chunks, dict):
            out[url] = {str(k): str(v) for k, v in chunks.items()}
    return out


def _save_state(db: Session, state: Dict[str, Dict[str, str]]) -> None:
    """Save chunk hash state to database."""
    row = db.get(SyncState, "competitor_source_state")
    now = datetime.utcnow()
    if not row:
        row = SyncState(key="competitor_source_state", value=state, updated_at=now)
        db.add(row)
    else:
        row.value = state
        row.updated_at = now
    db.commit()


def _summarize_change(
    competitor: str,
    url: str,
    heading: str,
    text: str,
    source_type: str,
) -> Tuple[str, str, str, List[str]]:
    """
    Use Gemini (when configured) to derive theme, change_type, claim, beginner_summary.

    Enhanced to provide beginner-friendly explanations for engineers unfamiliar with accounting.

    Fallbacks:
    - theme="unspecified"
    - change_type="unspecified"
    - claim = first sentence
    - beginner_summary = 3 generic bullets
    """
    client = _client()
    snippet = text[:1500]

    # Simple heuristic fallbacks
    default_theme = "unspecified"
    default_change_type = "unspecified"
    default_claim = (snippet.split(".")[0] or heading).strip()
    if default_claim and not default_claim.endswith("."):
        default_claim += "."
    default_bullets = [
        f"{competitor} has changed something related to \"{heading}\".",
        "This affects how their ERP product behaves or is positioned.",
        "Check the linked documentation for exact behavior and limitations.",
    ]

    if not client:
        return default_theme, default_change_type, default_claim, default_bullets

    try:
        from google.genai import types

        prompt = f"""
You analyze release notes and product documentation for ERP competitors.

Your audience: Engineers joining Campfire (an AI-native ERP) who may not have accounting/ERP backgrounds.

Given the following changed section from an official page, classify and summarize it for an internal capability change feed.

Return a single JSON object with EXACTLY these keys:

1. **theme**: one of ["ai", "consolidation", "reporting", "integrations", "procurement", "automation", "platform", "compliance", "performance", "revenue_recognition", "accounts_payable", "accounts_receivable", "general_ledger", "close_management", "other"]

2. **change_type**: one of ["new capability", "enhancement", "deprecation", "limitation", "other"]

3. **claim**: One precise sentence summarizing the change in product language (what they did).

4. **beginner_summary**: Array of exactly 3 bullets in PLAIN LANGUAGE:
   - Bullet 1: What this means in simple terms (avoid jargon)
   - Bullet 2: Why it matters / what problem it solves
   - Bullet 3: How it compares to what we do OR what competitive insight this gives us

IMPORTANT: For accounting/ERP jargon (ASC 606, sub-ledger, month-end close, etc.), explain briefly in parentheses.

Competitor: {competitor}
Page URL: {url}
Section heading: {heading}
Source type: {source_type}

Changed text:
\"\"\"{snippet}\"\"\""""

        config_kw = {"temperature": 0.15, "max_output_tokens": 700}
        try:
            config_kw["http_options"] = types.HttpOptions(timeout=_REQUEST_TIMEOUT_MS)
        except Exception:
            pass
        response = client.models.generate_content(
            model=_LLM_MODEL,
            contents=types.Part.from_text(prompt),
            config=types.GenerateContentConfig(**config_kw),
        )
        text_out = ""
        if getattr(response, "candidates", None):
            cand = response.candidates[0]
            finish = getattr(cand, "finish_reason", None) or getattr(cand, "finishReason", None)
            if str(finish).upper() not in ("BLOCKED", "SAFETY", "RECITATION"):
                part = cand.content.parts[0] if cand.content.parts else None
                if part is not None:
                    text_out = getattr(part, "text", None) or str(part)
        if not text_out:
            return default_theme, default_change_type, default_claim, default_bullets

        import json
        raw = text_out.strip()
        # Strip optional markdown fences
        if raw.startswith("```"):
            raw = raw.strip("` \n")
            if raw.lower().startswith("json"):
                raw = raw[4:].strip()
        obj = json.loads(raw)
        if not isinstance(obj, dict):
            return default_theme, default_change_type, default_claim, default_bullets
        theme = str(obj.get("theme") or default_theme).strip().lower()
        change_type = str(obj.get("change_type") or default_change_type).strip().lower()
        claim = str(obj.get("claim") or default_claim).strip()
        bullets = obj.get("beginner_summary") or default_bullets
        if not isinstance(bullets, list):
            bullets = default_bullets
        bullets = [str(b).strip() for b in bullets if str(b).strip()][:3]
        while len(bullets) < 3:
            bullets.append(default_bullets[len(bullets)])
        return theme, change_type, claim or default_claim, bullets
    except Exception:
        return default_theme, default_change_type, default_claim, default_bullets


def crawl_sources(
    db: Session,
    max_urls: int | None = None,
    max_priority: int = 1
) -> Dict[str, Any]:
    """
    Crawl all registered sources, detect changed chunks, and emit IntelEvents.

    Args:
        db: Database session
        max_urls: Optional limit on number of URLs to crawl
        max_priority: Include only competitors with priority <= this value (default 1 = top 5)

    Returns:
        Dict with crawl statistics: {
            "events_created": int,
            "sources_crawled": int,
            "sources_failed": int,
            "competitors": [list of competitor names],
            "duration_seconds": float
        }
    """
    start_time = datetime.utcnow()
    logger.info(f"Starting crawl (max_priority={max_priority}, max_urls={max_urls})")

    sources = get_all_sources(max_priority)
    state = _load_state(db)
    created = 0
    failed = 0
    crawled = 0
    competitors_seen: Set[str] = set()

    urls_processed = 0
    for src in sources:
        if max_urls is not None and urls_processed >= max_urls:
            break
        urls_processed += 1
        competitors_seen.add(src.competitor)

        logger.info(f"Crawling: {src.competitor} - {src.label}")
        html = _fetch(src.url)
        if not html:
            failed += 1
            continue

        chunks = _extract_chunks(html, src.url)
        if not chunks:
            logger.warning(f"  No chunks extracted from {src.url}")
            failed += 1
            continue

        crawled += 1
        logger.info(f"  Extracted {len(chunks)} chunks")

        url_state = state.setdefault(src.url, {})
        changes_in_url = 0
        for heading, text in chunks:
            chunk_hash = _hash_chunk(heading, text)
            key = heading[:120]  # heading acts as stable identifier within URL
            prev_hash = url_state.get(key)
            if prev_hash == chunk_hash:
                continue  # unchanged

            logger.info(f"  Change detected in chunk: {heading[:50]}...")
            theme, change_type, claim, bullets = _summarize_change(
                src.competitor, src.url, heading, text, src.source_type
            )
            event = IntelEvent(
                competitor=src.competitor,
                theme=theme,
                change_type=change_type,
                claim=claim,
                beginner_summary=bullets,
                evidence_url=src.url,
                evidence_snippet=text[:2000],
                chunk_hash=chunk_hash,
                created_at=datetime.utcnow(),
            )
            db.add(event)
            url_state[key] = chunk_hash
            created += 1
            changes_in_url += 1

        if changes_in_url > 0:
            logger.info(f"  Created {changes_in_url} events from this URL")

    if created:
        _save_state(db, state)
        db.commit()
        logger.info(f"Saved state with {created} new events")

    end_time = datetime.utcnow()
    duration = (end_time - start_time).total_seconds()

    stats = {
        "events_created": created,
        "sources_crawled": crawled,
        "sources_failed": failed,
        "competitors": sorted(list(competitors_seen)),
        "duration_seconds": round(duration, 2),
    }

    logger.info(f"Crawl complete: {stats}")
    return stats


def get_recent_events(db: Session, limit: int = 50) -> List[Dict[str, Any]]:
    """Return recent IntelEvents for the UI."""
    stmt = (
        select(IntelEvent)
        .order_by(IntelEvent.created_at.desc())
        .limit(limit)
    )
    rows = list(db.scalars(stmt).all())
    out: List[Dict[str, Any]] = []
    for r in rows:
        out.append(
            {
                "id": r.id,
                "competitor": r.competitor,
                "theme": r.theme,
                "change_type": r.change_type,
                "claim": r.claim,
                "beginner_summary": r.beginner_summary,
                "evidence_url": r.evidence_url,
                "evidence_snippet": r.evidence_snippet,
                "created_at": r.created_at.isoformat() if r.created_at else None,
            }
        )
    return out
