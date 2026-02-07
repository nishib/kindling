"""Seed database with Velora demo data (Notion, GitHub, Slack mock content)."""
import json
import os
from datetime import datetime

from sqlalchemy import delete, select, func
from database import SessionLocal, engine
from models import Base, KnowledgeItem, CompetitorIntel

# Mock embedding when Gemini key not set
import numpy as np


def _get_embedding(text: str):
    """Use Gemini embedding if GEMINI_API_KEY is set, else mock 768-dim."""
    try:
        from rag import get_embedding as gemini_embed
        emb = gemini_embed(text, task_type="RETRIEVAL_DOCUMENT")
        if emb and len(emb) == 768:
            return emb
    except Exception:
        pass
    np.random.seed(hash(text) % (2**32))
    return np.random.randn(768).tolist()


def create_tables():
    """Create all database tables."""
    Base.metadata.create_all(bind=engine)
    print("✅ Database tables created")


def seed_notion_data(db):
    """Load Notion pages into database."""
    path = os.path.join(os.path.dirname(__file__), "mock_data", "velora_notion.json")
    with open(path) as f:
        data = json.load(f)
    for page in data["pages"]:
        item = KnowledgeItem(
            source="notion",
            content=page["content"],
            embedding=_get_embedding(page["content"]),
            metadata_={
                "title": page["title"],
                "page_id": page["id"],
                "created": page["created"],
            },
            created_at=datetime.utcnow(),
        )
        db.add(item)
    db.commit()
    print(f"✅ Loaded {len(data['pages'])} Notion pages")


def seed_github_data(db):
    """Load GitHub repos into database."""
    path = os.path.join(os.path.dirname(__file__), "mock_data", "velora_github.json")
    with open(path) as f:
        data = json.load(f)
    for repo in data["repositories"]:
        item = KnowledgeItem(
            source="github",
            content=repo["readme"],
            embedding=_get_embedding(repo["readme"]),
            metadata_={
                "repo_name": repo["name"],
                "language": repo["language"],
                "last_commit": repo["last_commit"],
            },
            created_at=datetime.utcnow(),
        )
        db.add(item)
    db.commit()
    print(f"✅ Loaded {len(data['repositories'])} GitHub repos")


def seed_slack_data(db):
    """Load Slack messages into database."""
    path = os.path.join(os.path.dirname(__file__), "mock_data", "velora_slack.json")
    with open(path) as f:
        data = json.load(f)
    for msg in data["messages"]:
        item = KnowledgeItem(
            source="slack",
            content=msg["content"],
            embedding=_get_embedding(msg["content"]),
            metadata_={
                "channel": msg["channel"],
                "author": msg["author"],
                "timestamp": msg["timestamp"],
            },
            created_at=datetime.utcnow(),
        )
        db.add(item)
    db.commit()
    print(f"✅ Loaded {len(data['messages'])} Slack messages")


def seed_competitor_intel(db):
    """Add competitor intelligence (You.com-style data)."""
    competitors = [
        {
            "name": "Intercom",
            "intel_type": "pricing",
            "content": "Intercom raised prices 15% in January 2024. Entry plan now $74/month. Enterprise plans start at $50k/year. Focusing on upmarket enterprise deals.",
            "source_url": "https://www.intercom.com/pricing",
        },
        {
            "name": "Zendesk",
            "intel_type": "product",
            "content": "Zendesk acquired AI startup Ultimate.ai for $400M. Integrating AI agents into Suite by Q2 2024. Still lacks native e-commerce integrations.",
            "source_url": "https://techcrunch.com/zendesk-ultimate",
        },
        {
            "name": "Gorgias",
            "intel_type": "market",
            "content": "Gorgias hit 12,000 customers, $25M ARR. Strong in fashion/beauty verticals. Main weakness: expensive for small merchants ($60/month minimum).",
            "source_url": "https://www.gorgias.com/blog/growth",
        },
        {
            "name": "Intercom",
            "intel_type": "product",
            "content": "Intercom launched Fin AI for customer support in 2024. Focus on enterprise workflows and Salesforce integration. Limited e-commerce native features compared to Gorgias.",
            "source_url": "https://www.intercom.com/product",
        },
        {
            "name": "Zendesk",
            "intel_type": "pricing",
            "content": "Zendesk Suite pricing starts at $55/agent/month. Enterprise tier required for advanced AI features. Many SMBs find it costly for support-only use cases.",
            "source_url": "https://www.zendesk.com/pricing",
        },
    ]
    for comp in competitors:
        item = CompetitorIntel(
            competitor_name=comp["name"],
            intel_type=comp["intel_type"],
            content=comp["content"],
            source_url=comp["source_url"],
            created_at=datetime.utcnow(),
        )
        db.add(item)
    db.commit()
    print(f"✅ Loaded {len(competitors)} competitor intelligence items")


def main():
    """Seed database with Velora demo data."""
    print("🚀 Starting database seed...")
    create_tables()
    db = SessionLocal()

    # Check if database already has data (skip seeding on redeploy)
    try:
        existing_count = db.scalar(select(func.count()).select_from(KnowledgeItem))
        if existing_count > 0:
            print(f"⚠️ Database already has {existing_count} items. Skipping seed to preserve data.")
            print("   (To force reseed, manually clear the database first)")
            db.close()
            return
    except Exception as e:
        print(f"⚠️ Could not check existing data: {e}")

    try:
        db.execute(delete(KnowledgeItem))
        db.execute(delete(CompetitorIntel))
        db.commit()
        print("✅ Cleared existing data")
    except Exception as e:
        db.rollback()
        print(f"⚠️ Clear (optional): {e}")
    try:
        seed_notion_data(db)
        seed_github_data(db)
        seed_slack_data(db)
        seed_competitor_intel(db)
        total_items = db.scalar(select(func.count()).select_from(KnowledgeItem))
        total_intel = db.scalar(select(func.count()).select_from(CompetitorIntel))
        print(f"\n📊 Seed complete!")
        print(f"   - Knowledge items: {total_items}")
        print(f"   - Competitor intel: {total_intel}")
        print(f"   - Ready for demo! 🎉")
    except Exception as e:
        print(f"❌ Error seeding database: {e}")
        db.rollback()
    finally:
        db.close()


if __name__ == "__main__":
    main()
