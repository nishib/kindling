"""SQLAlchemy models for OnboardAI."""
from datetime import datetime
import uuid

from sqlalchemy import Column, Integer, String, Text, DateTime, JSON
from sqlalchemy.ext.declarative import declarative_base
from sqlalchemy.dialects.postgresql import UUID
from pgvector.sqlalchemy import Vector

Base = declarative_base()


class KnowledgeItem(Base):
    """Knowledge items for RAG (source-agnostic)."""
    __tablename__ = "knowledge_items"

    id = Column(Integer, primary_key=True, autoincrement=True)
    source = Column(String(32), nullable=False)  # notion, github, slack
    content = Column(Text, nullable=False)
    embedding = Column(Vector(768), nullable=True)
    metadata_ = Column("metadata", JSON, nullable=True)
    created_at = Column(DateTime, default=datetime.utcnow)


class CompetitorIntel(Base):
    """Competitor intelligence from You.com or cached research."""
    __tablename__ = "competitor_intel"

    id = Column(Integer, primary_key=True, autoincrement=True)
    competitor_name = Column(String(128), nullable=False)
    intel_type = Column(String(64), nullable=False)
    content = Column(Text, nullable=False)
    source_url = Column(String(512), nullable=True)
    created_at = Column(DateTime, default=datetime.utcnow)


class SyncState(Base):
    """Key-value store for sync metadata (last_sync_at, etc.)."""
    __tablename__ = "sync_state"

    key = Column(String(64), primary_key=True)
    value = Column(JSON, nullable=True)
    updated_at = Column(DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)


class YouComCache(Base):
    """Cached You.com search results for customer and accounting/ERP explainer search; feed into RAG."""
    __tablename__ = "you_com_cache"

    id = Column(Integer, primary_key=True, autoincrement=True)
    query_key = Column(
        String(256), nullable=False
    )  # normalized key, e.g. "customer:replit" or "explainer:revenue recognition"
    query_type = Column(String(32), nullable=False)  # customer | explainer
    content = Column(Text, nullable=False)
    source_url = Column(String(512), nullable=True)
    title = Column(String(512), nullable=True)
    created_at = Column(DateTime, default=datetime.utcnow)


class ERPScenarioRun(Base):
    """
    Persisted ERP scenario run state.

    We use JSON for state and synthetic data to allow fast iteration on the
    state machine and datasets without schema churn.
    """

    __tablename__ = "erp_scenario_runs"

    run_id = Column(
        UUID(as_uuid=True),
        primary_key=True,
        default=uuid.uuid4,
    )
    template_id = Column(String(128), nullable=False)
    user_session_id = Column(String(128), nullable=True)
    started_at = Column(DateTime, default=datetime.utcnow, nullable=False)
    last_updated_at = Column(DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)
    state_json = Column(JSON, nullable=False)
    synthetic_data_json = Column(JSON, nullable=False)


class ERPScenarioEvent(Base):
    """Event log for decisions within a scenario run."""

    __tablename__ = "erp_scenario_events"

    event_id = Column(
        UUID(as_uuid=True),
        primary_key=True,
        default=uuid.uuid4,
    )
    run_id = Column(UUID(as_uuid=True), nullable=False)
    step_id = Column(String(128), nullable=False)
    choice_id = Column(String(128), nullable=False)
    created_at = Column(DateTime, default=datetime.utcnow, nullable=False)
