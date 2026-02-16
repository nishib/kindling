"""FastAPI application for Campfire ERP Onboarding Assistant."""
import logging
import os
from contextlib import asynccontextmanager
from pathlib import Path

from dotenv import load_dotenv

logger = logging.getLogger(__name__)

# Load .env from repo root so RENDER_API_KEY etc. work when set locally
load_dotenv(Path(__file__).resolve().parent / ".env")

from fastapi import Depends, FastAPI
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import FileResponse
from fastapi.staticfiles import StaticFiles
from sqlalchemy.orm import Session

from database import check_connection, engine, get_db, init_pgvector, ensure_connection
from models import Base
from scenarios import router as scenarios_router
from learning_paths import get_all_paths, get_path
from erp_concept_graph import (
    get_concept_graph,
    get_concept,
    get_recommend_next,
)


@asynccontextmanager
async def lifespan(app: FastAPI):
    """Startup: connect to DB, create tables and enable pgvector with retry logic."""
    # Try to establish connection with retries
    if ensure_connection():
        try:
            Base.metadata.create_all(bind=engine)
            db = next(get_db())
            try:
                init_pgvector(db)
                logger.info("Database connected: tables ready, pgvector enabled")
            finally:
                db.close()
        except Exception as e:
            logger.warning("Database initialization failed: %s. Will retry on requests.", e)
    else:
        logger.warning("Database unavailable at startup. Will retry on requests. /health will report status.")

    yield

    # Cleanup on shutdown
    try:
        engine.dispose()
        logger.info("Database connection pool disposed")
    except Exception as e:
        logger.warning(f"Error disposing database connection pool: {e}")


app = FastAPI(title="Campfire ERP Onboarding", lifespan=lifespan)

app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# Scenario engine API
app.include_router(scenarios_router, prefix="/api/scenarios", tags=["scenarios"])


@app.post("/api/mentor/month-end")
def month_end_mentor(payload: dict):
    """
    AI Mentor for Month-End Close game, backed by Gemini.

    Frontend sends a small, typed payload:
    {
      "view": "DASHBOARD" | "AP_MODULE" | "REV_REC_MODULE" | "GL_RECON_MODULE",
      "periodStatus": "OPEN" | "CLOSED",
      "tasks": {
        "apMismatch": bool,
        "revenueUnrecognized": bool,
        "suspenseBalance": bool
      },
      "lastEvent": str | null
    }
    """
    from rag import _client  # reuse existing Gemini client helper

    client = _client()
    if not client:
        # No Gemini client - let frontend use scripted fallback
        logger.info("Gemini client not available - frontend will use scripted guidance")
        raise HTTPException(
            status_code=503,
            detail="AI Mentor unavailable - using scripted guidance"
        )

    view = payload.get("view") or "DASHBOARD"
    period_status = payload.get("periodStatus") or "OPEN"
    tasks = payload.get("tasks") or {}
    last_event = payload.get("lastEvent") or ""

    # Normalize booleans defensively
    ap_mismatch = bool(tasks.get("apMismatch", False))
    revenue_unrecognized = bool(tasks.get("revenueUnrecognized", False))
    suspense_balance = bool(tasks.get("suspenseBalance", False))

    system_prompt = """
You are the AI Mentor ("The Controller") inside a Month-End Close training game for an AI-native ERP.

You talk to a learner who is acting as a Controller closing the books for a single period.

Tone:
- Professional: use precise accounting and ERP language.
- Encouraging: guide the learner; do not criticize.
- Precise: reference concrete concepts like sub-ledger vs. general ledger, ASC 606, and suspense clearing.

Vocabulary rules (MUST follow):
- Say "Validation Exception" (never "error").
- Say "Post to Ledger" (never "Save").
- Say "Reconcile" (never "Fix").

Context you will receive:
- view: which workspace the learner is in (DASHBOARD, AP_MODULE, REV_REC_MODULE, GL_RECON_MODULE).
- periodStatus: OPEN or CLOSED.
- tasks: which Validation Exceptions are still open:
  - apMismatch: true/false – AP sub-ledger does not match GL until invoice is Posted to Ledger.
  - revenueUnrecognized: true/false – revenue schedule not generated; revenue must be recognized over time.
  - suspenseBalance: true/false – Suspense account holds unreconciled items.
- lastEvent: most recent user action (e.g. ATTEMPTED_CLOSE_WITH_ISSUES, AP_RESOLVED, REV_REC_RESOLVED, GL_RECON_RESOLVED, PERIOD_CLOSED).

Your job:
- Write 1–3 sentences addressing what the learner should focus on next given this state.
- Make the guidance feel reactive to lastEvent when present (e.g., congratulate them after AP_RESOLVED).
- Do NOT ask the learner questions; give them clear direction.
- Stay within the Month-End Close scenario; do not invent new modules or tasks.
""".strip()

    state_blob = (
        f"view={view}, periodStatus={period_status}, "
        f"apMismatch={ap_mismatch}, revenueUnrecognized={revenue_unrecognized}, "
        f"suspenseBalance={suspense_balance}, lastEvent={last_event or 'NONE'}"
    )

    try:
        from google.genai import types

        prompt = (
            f"{system_prompt}\n\n"
            f"Current Month-End Close state:\n{state_blob}\n\n"
            "Write the mentor's next message now (1–3 sentences)."
        )

        config_kw = {"temperature": 0.25, "max_output_tokens": 256}
        try:
            # Reuse same timeout style as other Gemini calls
            from rag import _REQUEST_TIMEOUT_MS  # type: ignore[attr-defined]
            config_kw["http_options"] = types.HttpOptions(timeout=_REQUEST_TIMEOUT_MS)
        except Exception:
            pass

        response = client.models.generate_content(
            model="models/gemini-2.0-flash",
            contents=types.Part.from_text(prompt),
            config=types.GenerateContentConfig(**config_kw),
        )

        text = ""
        if getattr(response, "candidates", None):
            cand = response.candidates[0]
            finish = getattr(cand, "finish_reason", None) or getattr(cand, "finishReason", None)
            if str(finish).upper() not in ("BLOCKED", "SAFETY", "RECITATION"):
                part = cand.content.parts[0] if cand.content.parts else None
                if part is not None:
                    text = getattr(part, "text", None) or str(part)

        if not text or not str(text).strip():
            text = (
                "You are inside the Month-End Close workspace. Clear all Validation Exceptions "
                "in AP, Revenue Recognition, and GL Reconciliation before closing the period."
            )

        # Simple sentiment heuristic from state; UI can still override if needed.
        if period_status == "CLOSED":
            sentiment = "celebrating"
        elif last_event in ("AP_RESOLVED", "REV_REC_RESOLVED", "GL_RECON_RESOLVED"):
            sentiment = "happy"
        elif ap_mismatch or revenue_unrecognized or suspense_balance:
            sentiment = "warning"
        else:
            sentiment = "neutral"

        return {
            "sentiment": sentiment,
            "message": str(text).strip(),
        }
    except Exception as e:
        # Log the error for debugging but don't expose to user
        import traceback
        logger.error(f"Gemini mentor call failed: {e}")
        logger.error(traceback.format_exc())

        # Return None to signal frontend to use its scripted fallback
        # Frontend has comprehensive scripted messages that handle all states
        raise HTTPException(
            status_code=503,
            detail="AI Mentor temporarily unavailable - using scripted guidance"
        )

# Serve static PDF brief
static_dir = os.path.join(os.path.dirname(__file__), "static")
if os.path.isdir(static_dir):
    app.mount("/static", StaticFiles(directory=static_dir), name="static")

# Serve frontend build (Vite React app)
frontend_dist = os.path.join(os.path.dirname(__file__), "frontend", "dist")
if os.path.isdir(frontend_dist):
    # Serve static assets (JS, CSS, images) from /assets
    assets_dir = os.path.join(frontend_dist, "assets")
    if os.path.isdir(assets_dir):
        app.mount("/assets", StaticFiles(directory=assets_dir), name="assets")

    # Serve other static files (favicon, etc.)
    @app.get("/favicon.ico")
    @app.get("/vite.svg")
    async def serve_static_files(request):
        file_path = os.path.join(frontend_dist, request.url.path.lstrip("/"))
        if os.path.isfile(file_path):
            return FileResponse(file_path)
        return {"detail": "Not Found"}


def check_db():
    """Test database connectivity."""
    return "connected" if check_connection() else "disconnected"


@app.get("/health")
def health():
    """Health check for Render and frontend."""
    return {
        "status": "healthy",
        "database": check_db(),
    }


@app.get("/api/competitors/sources")
def competitor_sources(priority: int = 1):
    """
    List competitors being monitored with their search terms.

    Args:
        priority: Max priority level (1=top 5, 2=include mid-tier, 3=all)
    """
    from competitor_sources import get_active_competitors

    competitors = get_active_competitors(max_priority=priority)

    return [
        {
            "competitor": c.name,
            "category": c.category,
            "priority": c.priority,
            "status": "active" if c.enabled else "disabled"
        }
        for c in competitors
    ]


@app.get("/api/competitors/events")
def competitor_events(db: Session = Depends(get_db), limit: int = 50):
    """
    Capability-level competitor change events (Release Notes + Docs "Capability Change Feed").
    """
    from competitor_sources import get_recent_events

    try:
        return get_recent_events(db, limit=limit)
    except Exception:
        return []


@app.get("/api/intel/search")
def intel_search(q: str = "", count: int = 8, freshness: str = "month"):
    """Live You.com web + news search. Returns { web, news, query } for the given query."""
    try:
        from you_com import live_search
        result = live_search(q.strip(), count=min(max(1, count), 20), freshness=freshness)
        return result
    except Exception as e:
        return {"web": [], "news": [], "query": q or "", "error": str(e)[:200]}


@app.post("/api/competitors/crawl")
def competitor_crawl(
    db: Session = Depends(get_db),
    priority: int = 1,
    freshness: str = "week",
    max_competitors: int | None = None
):
    """
    Trigger a crawl using You.com live search for competitor intelligence.

    Args:
        priority: Max priority level (1=top 5, 2=include mid-tier, 3=all)
        freshness: Time filter for You.com search ("day", "week", "month", "year")
        max_competitors: Optional limit on number of competitors to crawl (for testing)

    Returns detailed statistics about the crawl.
    """
    from competitor_sources import crawl_sources

    try:
        stats = crawl_sources(
            db,
            max_priority=priority,
            freshness=freshness,
            max_competitors=max_competitors
        )
        return {"status": "ok", **stats}
    except Exception as e:
        import traceback
        return {"status": "error", "error": str(e)[:500], "traceback": traceback.format_exc()[:1000]}


@app.get("/api/intel/customer")
def intel_customer_search(name: str = "", db: Session = Depends(get_db)):
    """You.com customer search (Chunk 4). Returns RAG-style items; uses cache when available."""
    try:
        from you_com import customer_search
        items = customer_search((name or "").strip(), db=db, max_items=5)
        return {"items": items, "query": name or ""}
    except Exception as e:
        return {"items": [], "query": name or "", "error": str(e)[:200]}


@app.get("/api/intel/explainer")
def intel_explainer_search(term: str = "", db: Session = Depends(get_db)):
    """You.com accounting/ERP explainer search (Chunk 4). Returns RAG-style items; uses cache."""
    try:
        from you_com import explainer_search
        items = explainer_search((term or "").strip(), db=db, max_items=5)
        return {"items": items, "query": term or ""}
    except Exception as e:
        return {"items": [], "query": term or "", "error": str(e)[:200]}


# --- Learning pathways (Chunk 1) ---
@app.get("/api/learning/paths")
def api_learning_paths():
    """List all learning paths (id, title, description, module_count)."""
    return get_all_paths()


@app.get("/api/learning/paths/{path_id}")
def api_learning_path(path_id: str):
    """Get a single path with full modules (ordered)."""
    path = get_path(path_id)
    if path is None:
        return {"detail": "Path not found"}
    return path


# --- Skill Map + Knowledge Graph (ERP concepts) ---
@app.get("/api/learning/concept-graph")
def api_concept_graph():
    """Full ERP concept graph: concepts with children and dependencies."""
    return get_concept_graph()


@app.get("/api/learning/concepts/{concept_id}")
def api_concept(concept_id: str):
    """Single concept with depends_on details and children."""
    concept = get_concept(concept_id)
    if concept is None:
        return {"detail": "Concept not found"}
    return concept


@app.get("/api/learning/recommend-next")
def api_recommend_next(completed: str = ""):
    """Concepts ready to learn next (all dependencies satisfied). completed = comma-separated concept ids."""
    completed_ids = [x.strip() for x in (completed or "").split(",") if x.strip()]
    return get_recommend_next(completed_ids)


@app.get("/api/render/usage")
def render_usage():
    """Render usage — workspaces, services, bandwidth. Key from env only."""
    from render_usage import get_usage
    return get_usage()


# Catch-all route to serve frontend index.html for client-side routing
# This must be LAST so API routes are matched first
@app.get("/{full_path:path}")
async def serve_frontend(full_path: str):
    """Serve React frontend for all non-API routes (client-side routing)."""
    frontend_dist = os.path.join(os.path.dirname(__file__), "frontend", "dist")
    index_file = os.path.join(frontend_dist, "index.html")

    # If frontend build exists, serve index.html
    if os.path.isfile(index_file):
        return FileResponse(index_file)

    # Fallback for development (no frontend build yet)
    return {
        "detail": "Frontend not built. Run: cd frontend && npm install && npm run build",
        "path": full_path,
    }
