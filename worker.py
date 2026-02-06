"""Celery worker for OnboardAI - scheduled Composio sync every 6 hours."""
import os
from pathlib import Path

from celery import Celery
from celery.schedules import crontab
from dotenv import load_dotenv

# Load .env so COMPOSIO_API_KEY etc. are available in worker
load_dotenv(Path(__file__).resolve().parent / ".env")

app = Celery(
    "onboardai",
    broker=os.getenv("REDIS_URL", "redis://localhost:6379"),
    backend=os.getenv("REDIS_URL", "redis://localhost:6379"),
)

# Every 6 hours
app.conf.beat_schedule = {
    "composio-sync-every-6h": {
        "task": "worker.sync_data_sources",
        "schedule": crontab(minute=0, hour="*/6"),
    },
}
app.conf.timezone = "UTC"


@app.task
def sync_data_sources():
    """Run Composio sync (Notion, GitHub, Slack) and store in DB."""
    from database import SessionLocal
    from composio_sync import run_sync
    db = SessionLocal()
    try:
        result = run_sync(db)
        return {"status": "sync completed", **result}
    finally:
        db.close()
