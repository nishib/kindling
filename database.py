"""PostgreSQL connection with pgvector for OnboardAI."""
import os
from pathlib import Path

from sqlalchemy import create_engine, text
from sqlalchemy.orm import sessionmaker
from dotenv import load_dotenv

# Load .env from project root (next to this file) so key is ready regardless of cwd
load_dotenv(Path(__file__).resolve().parent / ".env")

DATABASE_URL = os.getenv(
    "DATABASE_URL",
    "postgresql://postgres:postgres@localhost:5432/onboardai",
)

# Render Postgres (and many cloud providers) require SSL
if DATABASE_URL and "render.com" in DATABASE_URL and "sslmode" not in DATABASE_URL:
    DATABASE_URL = DATABASE_URL + ("&" if "?" in DATABASE_URL else "?") + "sslmode=require"

# psycopg2 expects postgresql://; Render sometimes gives postgres://
if DATABASE_URL and DATABASE_URL.startswith("postgres://"):
    DATABASE_URL = "postgresql://" + DATABASE_URL[len("postgres://") :]

engine = create_engine(DATABASE_URL)
SessionLocal = sessionmaker(autocommit=False, autoflush=False, bind=engine)


def get_db():
    """Dependency yielding a database session."""
    db = SessionLocal()
    try:
        yield db
    finally:
        db.close()


def init_pgvector(db_session):
    """Enable pgvector extension on the database."""
    db_session.execute(text("CREATE EXTENSION IF NOT EXISTS vector"))
    db_session.commit()
