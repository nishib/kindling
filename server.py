"""FastAPI application for OnboardAI."""
import os
from contextlib import asynccontextmanager

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
    """Startup: create tables and enable pgvector."""
    Base.metadata.create_all(bind=engine)
    db = next(get_db())
    try:
        init_pgvector(db)
    finally:
        db.close()
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
    """RAG Q&A: embed question, semantic search, Gemini synthesis with citations."""
    q = (req.question or "").strip()
    if not q:
        return AskResponse(answer="Please ask a question about Velora.", citations=[])
    result = ask(db, q)
    return AskResponse(answer=result["answer"], citations=result["citations"])


@app.get("/api/sync/status")
def sync_status(db: Session = Depends(get_db)):
    """Return last_sync_at and next_sync_at for dashboard (Phase 3)."""
    from composio_sync import get_sync_status
    return get_sync_status(db)


@app.post("/api/sync/trigger")
def sync_trigger(db: Session = Depends(get_db)):
    """Trigger Composio sync manually (e.g. from webhook or dashboard)."""
    from composio_sync import run_sync
    result = run_sync(db)
    return {"status": "ok", **result}


@app.get("/api/intel/feed")
def intel_feed(db: Session = Depends(get_db)):
    """Competitive Intelligence Feed (Phase 4) — cached You.com results."""
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


@app.post("/api/intel/refresh")
def intel_refresh(db: Session = Depends(get_db)):
    """Refresh competitor intel from You.com and cache in DB (Phase 4)."""
    from you_com import refresh_competitor_intel
    added = refresh_competitor_intel(db)
    return {"status": "ok", "added": added}
