"""FastAPI application for OnboardAI."""
import os
from contextlib import asynccontextmanager
from pathlib import Path

from dotenv import load_dotenv

# Load .env from repo root so RENDER_API_KEY etc. work when set locally
load_dotenv(Path(__file__).resolve().parent / ".env")

from fastapi import Depends, FastAPI
from fastapi.middleware.cors import CORSMiddleware
from fastapi.staticfiles import StaticFiles
from pydantic import BaseModel
from sqlalchemy import text
from sqlalchemy.orm import Session

from database import engine, get_db, init_pgvector
from models import Base
from rag import ask


@asynccontextmanager
async def lifespan(app: FastAPI):
    """Startup: create tables and enable pgvector. Tolerate DB unavailable so app still starts."""
    try:
        Base.metadata.create_all(bind=engine)
        db = next(get_db())
        try:
            init_pgvector(db)
        finally:
            db.close()
    except Exception:
        pass  # DB may be unavailable; /health will report disconnected
    yield


app = FastAPI(title="OnboardAI", lifespan=lifespan)

app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# Serve static PDF brief
static_dir = os.path.join(os.path.dirname(__file__), "static")
if os.path.isdir(static_dir):
    app.mount("/static", StaticFiles(directory=static_dir), name="static")


def check_db():
    """Test database connectivity."""
    try:
        with engine.connect() as conn:
            conn.execute(text("SELECT 1"))
        return "connected"
    except Exception:
        return "disconnected"


@app.get("/health")
def health():
    """Health check for Render and frontend."""
    return {
        "status": "healthy",
        "database": check_db(),
    }


class AskRequest(BaseModel):
    question: str


class AskResponse(BaseModel):
    answer: str
    citations: list[dict]


@app.post("/api/ask", response_model=AskResponse)
def api_ask(req: AskRequest, db: Session = Depends(get_db)):
    """RAG Q&A (Phase 2 – Gemini): embed, semantic search, synthesis with citations."""
    q = (req.question or "").strip()
    if not q:
        return AskResponse(answer="Please ask a question about Velora.", citations=[])
    try:
        result = ask(db, q)
        return AskResponse(answer=result["answer"], citations=result["citations"])
    except Exception as e:
        return AskResponse(
            answer="The knowledge base is unavailable. Ensure the database is running and seeded.",
            citations=[],
        )


@app.get("/api/sync/status")
def sync_status(db: Session = Depends(get_db)):
    """Return last_sync_at and next_sync_at for dashboard (Phase 3 – Composio)."""
    try:
        from composio_sync import get_sync_status
        return get_sync_status(db)
    except Exception:
        from datetime import datetime, timedelta
        return {"last_sync_at": None, "next_sync_at": (datetime.utcnow() + timedelta(hours=6)).isoformat()}


@app.post("/api/sync/trigger")
def sync_trigger(db: Session = Depends(get_db)):
    """Trigger Composio sync manually (Phase 3 – Composio)."""
    try:
        from composio_sync import run_sync
        result = run_sync(db)
        return {"status": "ok", **result}
    except Exception as e:
        return {"status": "error", "error": str(e)[:200]}


@app.get("/api/intel/feed")
def intel_feed(db: Session = Depends(get_db)):
    """Competitive Intelligence Feed (Phase 4 – You.com) — cached results."""
    try:
        from you_com import get_intel_feed
        rows = get_intel_feed(db, limit=20)
        return [
            {
                "id": r.id,
                "competitor": r.competitor_name,
                "type": r.intel_type,
                "content": r.content,
                "source_url": r.source_url,
                "timestamp": r.created_at.isoformat() if r.created_at else None,
            }
            for r in rows
        ]
    except Exception:
        return []


@app.post("/api/intel/refresh")
def intel_refresh(db: Session = Depends(get_db)):
    """Refresh competitor intel from You.com (Phase 4 – You.com)."""
    try:
        from you_com import refresh_competitor_intel
        added = refresh_competitor_intel(db)
        return {"status": "ok", "added": added}
    except Exception as e:
        return {"status": "error", "added": 0, "error": str(e)[:200]}


@app.get("/api/render/usage")
def render_usage():
    """Phase 5: Render usage — workspaces, services, bandwidth. Key from env only."""
    from render_usage import get_usage
    return get_usage()
