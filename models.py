"""SQLAlchemy models for OnboardAI."""
from datetime import datetime
from sqlalchemy import Column, Integer, String, Text, DateTime, JSON
from sqlalchemy.ext.declarative import declarative_base
from pgvector.sqlalchemy import Vector

Base = declarative_base()


class KnowledgeItem(Base):
    """Internal knowledge from Notion, GitHub, Slack."""
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
