"""Competitor intelligence crawler using You.com live web search.

Replaces web scraping with accurate You.com API searches for competitor news and updates.
Uses Gemini to extract structured capability events from search results.
"""

import logging
from datetime import datetime
from typing import Dict, Any, List, Optional
from dataclasses import dataclass

from sqlalchemy.orm import Session
from sqlalchemy import select

from models import IntelEvent, SyncState
from you_com import live_search, _headers as you_headers
from rag import _client as gemini_client, _LLM_MODEL

logger = logging.getLogger(__name__)
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
)


@dataclass
class Competitor:
    name: str
    category: str
    search_terms: List[str]
    priority: int
    enabled: bool = True


# Top competitors to monitor with ERP-focused search queries
_COMPETITORS: List[Competitor] = [
    # Traditional enterprise ERP
    Competitor(
        "NetSuite",
        "traditional",
        [
            "NetSuite ERP software new features accounting finance",
            "NetSuite cloud ERP product release financial management",
            "NetSuite accounting software updates revenue recognition"
        ],
        priority=1
    ),
    Competitor(
        "SAP",
        "traditional",
        [
            "SAP S/4HANA ERP software finance accounting updates",
            "SAP ERP system general ledger financial close features",
            "SAP cloud ERP accounting automation revenue"
        ],
        priority=1
    ),
    Competitor(
        "Workday",
        "traditional",
        [
            "Workday Financial Management ERP software accounting",
            "Workday ERP finance system general ledger updates",
            "Workday accounting software financial close planning"
        ],
        priority=1
    ),
    Competitor(
        "Oracle",
        "traditional",
        [
            "Oracle Cloud ERP accounting finance software updates",
            "Oracle Fusion ERP financial management features",
            "Oracle NetSuite ERP general ledger revenue recognition"
        ],
        priority=2
    ),
    Competitor(
        "Microsoft Dynamics 365",
        "traditional",
        [
            "Dynamics 365 Finance ERP accounting software updates",
            "Microsoft Dynamics ERP financial management features",
            "Dynamics 365 Business Central accounting finance"
        ],
        priority=2
    ),
    Competitor(
        "Sage Intacct",
        "traditional",
        [
            "Sage Intacct cloud accounting ERP software updates",
            "Sage Intacct financial management ERP features",
            "Sage Intacct accounting software general ledger"
        ],
        priority=2
    ),

    # Modern AI-native competitors
    Competitor(
        "Rillet",
        "modern",
        [
            "Rillet AI accounting ERP software revenue recognition",
            "Rillet financial management automation accounting",
            "Rillet ERP accounting software features updates"
        ],
        priority=1
    ),
    Competitor(
        "DualEntry",
        "modern",
        [
            "DualEntry AI accounting software ERP automation",
            "DualEntry financial management accounting features",
            "DualEntry ERP accounting software updates"
        ],
        priority=1
    ),
    Competitor(
        "Digits",
        "modern",
        [
            "Digits AI accounting software financial management",
            "Digits accounting automation ERP features",
            "Digits financial software accounting updates"
        ],
        priority=2
    ),
]


def get_active_competitors(max_priority: int = 3) -> List[Competitor]:
    """Get competitors filtered by priority level."""
    return [c for c in _COMPETITORS if c.enabled and c.priority <= max_priority]


def _is_erp_related(title: str, content: str) -> bool:
    """
    Check if article is actually about ERP/accounting/finance SOFTWARE.
    Requires multiple strong indicators that this is about B2B software products.
    Returns True only if content is specifically about ERP/accounting software systems.
    """
    combined = (title + " " + content).lower()

    # STRONG exclusions first - consumer/personal finance topics
    strong_exclude = [
        # Personal/consumer banking
        "personal account", "savings account", "checking account", "women's account",
        "credit card", "debit card", "mortgage", "loan", "personal finance",
        "consumer banking", "retail banking", "bank account", "financial advisor",
        # Politics, legal, news
        "border", "immigration", "federal crackdown", "court case", "lawsuit",
        "criminal", "politics", "election", "war", "military",
        # Entertainment
        "sports", "entertainment", "celebrity", "music", "movie", "gaming",
        # Crypto/trading
        "cryptocurrency", "bitcoin", "blockchain", "nft", "trading", "forex",
        # Real estate
        "real estate", "property", "housing market", "mortgage",
        # HR/recruiting (not ERP)
        "job posting", "career opportunities", "hiring", "resume",
        # Security threats/hacks (not product features)
        "malicious", "hijack", "hack", "breach", "cyber attack", "cyberattack",
        "ransomware", "phishing", "scam", "fraud", "exploit", "vulnerability",
        "data breach", "security threat", "malware",
        # Stock market/company earnings (not product news)
        "stock price", "share price", "shares tumble", "shares rise", "earnings report",
        "quarterly earnings", "revenue growth", "profit", "pat nearly doubles",
        "stock plummets", "stock soars", "market cap", "ipo", "acquisition price",
        "tariffs", "trade war", "economic downturn",
        # Training/courses/education (not product updates)
        "online course", "training course", "certification", "udemy", "coursera",
        "learn", "tutorial", "bootcamp", "from zero to expert", "beginner guide",
        # Health/environment/science (not tech)
        "microplastics", "plastic particles", "health risk", "medical", "disease",
        "cancer", "virus", "pandemic", "climate change", "pollution", "waste"
    ]

    # Check for strong exclusions first
    if any(keyword in combined for keyword in strong_exclude):
        return False

    # PRIMARY REQUIREMENT: Must explicitly mention SOFTWARE/SYSTEM/PRODUCT
    software_indicators = [
        "software", "system", "platform", "solution", "product", "application",
        "cloud", "saas", "technology", "tool", "module", "feature", "release",
        "update", "version", "integration", "api"
    ]

    has_software_indicator = any(indicator in combined for indicator in software_indicators)
    if not has_software_indicator:
        return False

    # SECONDARY REQUIREMENT: Must mention specific ERP/accounting functionality
    erp_specific_keywords = [
        "erp", "accounting software", "financial management software",
        "general ledger", "gl", "revenue recognition", "accounts payable", "ap automation",
        "accounts receivable", "ar", "financial close", "chart of accounts",
        "journal entries", "financial reporting", "consolidation", "multi-entity",
        "subledger", "sub-ledger", "trial balance", "financial statements",
        "expense management", "procurement", "order management",
        "billing system", "invoicing", "payment processing",
        "accounting automation", "financial planning", "budgeting software",
        "audit trail", "compliance", "gaap", "ifrs", "asc 606"
    ]

    # Count how many ERP-specific keywords are present
    erp_keyword_matches = sum(1 for keyword in erp_specific_keywords if keyword in combined)

    # Require at least 1 ERP-specific keyword (combined with software indicator makes this strict enough)
    return erp_keyword_matches >= 1


def _create_fallback_event(
    competitor: str,
    search_result: Dict[str, Any]
) -> Dict[str, Any] | None:
    """
    Create a fallback event when Gemini is unavailable.
    Uses simple heuristics from the You.com search result.
    Returns None if content is not ERP-related.
    """
    title = search_result.get("title", "")
    content = search_result.get("content", "")
    url = search_result.get("url", "")

    # Validate it's actually about ERP/accounting
    if not _is_erp_related(title, content):
        return None

    # Simple classification based on keywords
    content_lower = (title + " " + content).lower()

    if any(word in content_lower for word in ["launch", "introduce", "new", "release", "unveil"]):
        change_type = "new_feature"
    elif any(word in content_lower for word in ["update", "improve", "enhance", "upgrade"]):
        change_type = "enhancement"
    elif any(word in content_lower for word in ["deprecat", "sunset", "end of life", "discontinue"]):
        change_type = "deprecation"
    elif any(word in content_lower for word in ["partner", "acquisition", "acquire", "merge"]):
        change_type = "partnership"
    else:
        change_type = "announcement"

    # Create claim from title
    claim = title.strip()
    if not claim.endswith("."):
        claim += "."

    # Create simple beginner summary
    beginner_summary = [
        f"{competitor} announced: {title}",
        "This is a recent update from the competitor.",
        "Check the linked article for full details."
    ]

    return {
        "change_type": change_type,
        "claim": claim[:500],  # Limit length
        "beginner_summary": beginner_summary,
        "evidence_url": url[:512] if url else "",
        "evidence_snippet": content[:2000]
    }


def _extract_event_from_result(
    competitor: str,
    search_result: Dict[str, Any],
    category: str
) -> Optional[Dict[str, Any]]:
    """
    Extract a structured IntelEvent from a You.com search result.
    Uses Gemini when available, falls back to simple extraction otherwise.

    Returns dict with: change_type, claim, beginner_summary, evidence_url, evidence_snippet
    """
    title = search_result.get("title", "")
    content = search_result.get("content", "")
    url = search_result.get("url", "")

    if not content or len(content) < 50:
        return None

    # First check if content is actually ERP-related
    if not _is_erp_related(title, content):
        logger.debug(f"Skipping non-ERP article: {title[:60]}...")
        return None

    client = gemini_client()
    if not client:
        logger.debug("Gemini not available, using fallback extraction")
        return _create_fallback_event(competitor, search_result)

    # Use Gemini to analyze and extract structured data
    try:
        from google.genai import types

        prompt = f"""You analyze competitor intelligence for ERP/accounting/financial management software products.

Given this search result about {competitor}, extract structured information ONLY if it's about their ERP/accounting/finance software product.

Competitor: {competitor}
Category: {category}
Title: {title}
Content: {content[:1500]}
URL: {url}

STRICT VALIDATION:
- Article MUST be about ERP, accounting software, financial management systems, or finance software features
- REJECT if about: politics, legal cases, unrelated business news, general company news, non-software topics
- REJECT if not specifically about their software product capabilities

Return a JSON object with EXACTLY these fields:

1. **change_type**: one of ["new_feature", "enhancement", "deprecation", "announcement"]

2. **claim**: One precise sentence about the ERP/accounting software change or announcement.

3. **beginner_summary**: Array of exactly 3 bullets in PLAIN LANGUAGE for engineers new to ERP:
   - Bullet 1: What this software feature/change means in simple terms
   - Bullet 2: Why it matters for finance/accounting teams
   - Bullet 3: How this compares to what Campfire offers or what we should know

IMPORTANT:
- Use simple language in beginner_summary
- Explain ERP/accounting terms briefly (e.g., "revenue recognition is...")
- Focus ONLY on software product features and capabilities
- If article is NOT about ERP/accounting software features, return null

Example good response:
{{
  "change_type": "new_feature",
  "claim": "NetSuite launched AI-powered revenue recognition that automatically applies ASC 606 rules to contracts.",
  "beginner_summary": [
    "Revenue recognition is the process of recording when a company earns revenue, and ASC 606 is the accounting rule that governs this. NetSuite now uses AI to automate this complex process.",
    "This matters because revenue recognition is error-prone and time-consuming for finance teams, especially for SaaS companies with complex contracts.",
    "Campfire also offers AI-powered revenue recognition, but we focus on real-time accuracy and multi-entity scenarios which traditional ERPs struggle with."
  ]
}}

Example null response (general news, not product):
null
"""

        config_kw = {"temperature": 0.15, "max_output_tokens": 700}
        try:
            config_kw["http_options"] = types.HttpOptions(timeout=30000)
        except Exception:
            pass

        response = client.models.generate_content(
            model=_LLM_MODEL,
            contents=prompt,
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

        if not text_out or text_out.strip().lower() in ("null", "none", "{}"):
            return None

        import json
        raw = text_out.strip()
        # Strip markdown fences if present
        if raw.startswith("```"):
            raw = raw.strip("` \n")
            if raw.lower().startswith("json"):
                raw = raw[4:].strip()

        obj = json.loads(raw)
        if not isinstance(obj, dict) or obj is None:
            return None

        # Validate required fields
        change_type = str(obj.get("change_type", "")).strip()
        claim = str(obj.get("claim", "")).strip()
        beginner_summary = obj.get("beginner_summary", [])

        if not change_type or not claim or not isinstance(beginner_summary, list) or len(beginner_summary) < 3:
            logger.debug(f"Incomplete extraction for {competitor}: missing required fields")
            return None

        # Ensure we have exactly 3 bullets
        beginner_summary = [str(b).strip() for b in beginner_summary if str(b).strip()][:3]
        while len(beginner_summary) < 3:
            beginner_summary.append(f"See the linked article for more details about this {competitor} update.")

        return {
            "change_type": change_type,
            "claim": claim,
            "beginner_summary": beginner_summary,
            "evidence_url": url[:512] if url else "",
            "evidence_snippet": content[:2000]
        }

    except Exception as e:
        logger.warning(f"Gemini extraction failed ({str(e)[:100]}), using fallback")
        return _create_fallback_event(competitor, search_result)


def crawl_competitor(
    db: Session,
    competitor: Competitor,
    freshness: str = "week",
    max_results_per_query: int = 3
) -> int:
    """
    Crawl a single competitor using You.com search.

    Returns number of new IntelEvents created.
    """
    if not you_headers():
        logger.error("YOU_API_KEY not configured")
        return 0

    events_created = 0

    for search_term in competitor.search_terms:
        logger.info(f"Searching for: {search_term}")

        # Search You.com
        result = live_search(search_term, count=max_results_per_query, freshness=freshness)

        web_results = result.get("web", [])
        news_results = result.get("news", [])
        all_results = web_results + news_results

        logger.info(f"  Found {len(web_results)} web + {len(news_results)} news results")

        for search_result in all_results:
            url = search_result.get("url", "")
            if not url:
                continue

            # Check if we've already processed this URL recently
            # Use hash to keep key under 64 chars
            import hashlib
            url_hash = hashlib.md5(url.encode()).hexdigest()[:16]
            state_key = f"intel:{url_hash}"
            existing = db.get(SyncState, state_key)
            if existing:
                logger.debug(f"  Skipping already processed URL: {url[:80]}")
                continue

            # Extract structured event using Gemini
            event_data = _extract_event_from_result(
                competitor.name,
                search_result,
                competitor.category
            )

            if not event_data:
                logger.debug(f"  No valid event extracted from: {url[:80]}")
                continue

            # Create IntelEvent
            event = IntelEvent(
                competitor=competitor.name,
                change_type=event_data["change_type"],
                claim=event_data["claim"],
                beginner_summary=event_data["beginner_summary"],
                evidence_url=event_data["evidence_url"],
                evidence_snippet=event_data["evidence_snippet"],
                created_at=datetime.utcnow()
            )
            db.add(event)

            # Mark URL as processed and commit immediately to avoid duplicates
            state = SyncState(
                key=state_key,
                value={"processed_at": datetime.utcnow().isoformat(), "url": url},
                updated_at=datetime.utcnow()
            )
            db.add(state)

            try:
                db.commit()
                events_created += 1
                logger.info(f"  ✓ Created event: {event.claim[:80]}...")
            except Exception as commit_error:
                logger.warning(f"  Commit failed (likely duplicate): {str(commit_error)[:100]}")
                db.rollback()

    return events_created


def crawl_sources(
    db: Session,
    max_priority: int = 1,
    freshness: str = "week",
    max_competitors: Optional[int] = None
) -> Dict[str, Any]:
    """
    Crawl all active competitors using You.com search.

    Args:
        db: Database session
        max_priority: Include only competitors with priority <= this value
        freshness: You.com freshness filter ("day", "week", "month", "year")
        max_competitors: Optional limit on number of competitors to crawl

    Returns:
        Dict with crawl statistics
    """
    start_time = datetime.utcnow()
    logger.info(f"Starting competitor crawl (priority <= {max_priority}, freshness={freshness})")

    competitors = get_active_competitors(max_priority)
    if max_competitors:
        competitors = competitors[:max_competitors]

    total_events = 0
    competitors_crawled = []
    competitors_failed = []

    for competitor in competitors:
        logger.info(f"\nCrawling {competitor.name} ({competitor.category})...")
        try:
            events = crawl_competitor(db, competitor, freshness=freshness)
            total_events += events
            competitors_crawled.append(competitor.name)
            logger.info(f"✓ {competitor.name}: {events} events created")
        except Exception as e:
            logger.error(f"✗ {competitor.name} failed: {e}", exc_info=True)
            competitors_failed.append(competitor.name)

    end_time = datetime.utcnow()
    duration = (end_time - start_time).total_seconds()

    stats = {
        "events_created": total_events,
        "competitors_crawled": len(competitors_crawled),
        "competitors_failed": len(competitors_failed),
        "competitor_names": competitors_crawled,
        "failed_competitors": competitors_failed,
        "duration_seconds": round(duration, 2),
        "freshness": freshness
    }

    logger.info(f"\n{'='*60}")
    logger.info(f"Crawl complete!")
    logger.info(f"Events created: {total_events}")
    logger.info(f"Competitors crawled: {len(competitors_crawled)}/{len(competitors)}")
    logger.info(f"Duration: {duration:.1f}s")
    logger.info(f"{'='*60}\n")

    return stats


def get_recent_events(db: Session, limit: int = 50) -> List[Dict[str, Any]]:
    """Return recent IntelEvents for the UI."""
    stmt = (
        select(IntelEvent)
        .order_by(IntelEvent.created_at.desc())
        .limit(limit)
    )
    rows = list(db.scalars(stmt).all())

    return [
        {
            "id": r.id,
            "competitor": r.competitor,
            "change_type": r.change_type,
            "claim": r.claim,
            "beginner_summary": r.beginner_summary,
            "evidence_url": r.evidence_url,
            "evidence_snippet": r.evidence_snippet[:500] + "..." if len(r.evidence_snippet) > 500 else r.evidence_snippet,
            "created_at": r.created_at.isoformat() if r.created_at else None,
        }
        for r in rows
    ]


def get_competitor_registry(max_priority: int = 1) -> List[Dict[str, Any]]:
    """
    Return competitor registry for API/UI.

    Shows which competitors are being monitored and their search terms.
    """
    competitors = get_active_competitors(max_priority)

    return [
        {
            "competitor": c.name,
            "category": c.category,
            "priority": c.priority,
            "search_terms": c.search_terms,
            "status": "active" if c.enabled else "disabled"
        }
        for c in competitors
    ]
