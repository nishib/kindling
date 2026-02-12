"""Celery worker for OnboardAI. Scheduled sync removed; add tasks as needed."""
import os
from pathlib import Path

from celery import Celery
from dotenv import load_dotenv

load_dotenv(Path(__file__).resolve().parent / ".env")

app = Celery(
    "onboardai",
    broker=os.getenv("REDIS_URL", "redis://localhost:6379"),
    backend=os.getenv("REDIS_URL", "redis://localhost:6379"),
)

app.conf.timezone = "UTC"
