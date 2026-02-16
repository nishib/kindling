"""PostgreSQL connection with pgvector for OnboardAI."""
import os
import time
import logging
from pathlib import Path

from sqlalchemy import create_engine, text
from sqlalchemy.orm import sessionmaker
from dotenv import load_dotenv

logger = logging.getLogger(__name__)

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

# Create engine with connection pooling and automatic reconnection
engine = create_engine(
    DATABASE_URL,
    pool_pre_ping=True,  # Test connections before using them
    pool_size=5,  # Number of connections to maintain
    max_overflow=10,  # Additional connections when pool is exhausted
    pool_recycle=3600,  # Recycle connections after 1 hour
    connect_args={"connect_timeout": 10}  # Connection timeout in seconds
)
SessionLocal = sessionmaker(autocommit=False, autoflush=False, bind=engine)


def get_db():
    """Dependency yielding a database session."""
    db = SessionLocal()
    try:
        yield db
    finally:
        db.close()


def check_connection(retry_count=3, retry_delay=1):
    """
    Verify database is reachable with retry logic.

    Args:
        retry_count: Number of retry attempts
        retry_delay: Initial delay between retries (exponential backoff)

    Returns True if connected, False otherwise.
    """
    for attempt in range(retry_count):
        try:
            with engine.connect() as conn:
                conn.execute(text("SELECT 1"))
            if attempt > 0:
                logger.info(f"Database connection successful after {attempt + 1} attempts")
            return True
        except Exception as e:
            if attempt < retry_count - 1:
                wait_time = retry_delay * (2 ** attempt)
                logger.warning(f"Database connection attempt {attempt + 1} failed: {e}. Retrying in {wait_time}s...")
                time.sleep(wait_time)
            else:
                logger.error(f"Database connection failed after {retry_count} attempts: {e}")
    return False


def init_pgvector(db_session):
    """Enable pgvector extension on the database with retry logic."""
    max_retries = 3
    for attempt in range(max_retries):
        try:
            db_session.execute(text("CREATE EXTENSION IF NOT EXISTS vector"))
            db_session.commit()
            logger.info("pgvector extension enabled successfully")
            return True
        except Exception as e:
            db_session.rollback()
            if attempt < max_retries - 1:
                logger.warning(f"Failed to enable pgvector (attempt {attempt + 1}): {e}. Retrying...")
                time.sleep(1 * (2 ** attempt))
            else:
                logger.error(f"Failed to enable pgvector after {max_retries} attempts: {e}")
                raise
    return False


def ensure_connection():
    """
    Ensure database connection is active. Returns True if connected, False otherwise.
    Useful for pre-flight checks before database operations.
    """
    return check_connection(retry_count=3, retry_delay=1)
