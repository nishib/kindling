"""Re-embed all knowledge items with Gemini (run after seed_data when GEMINI_API_KEY is set)."""
import os
import sys

from sqlalchemy import select
from database import SessionLocal
from models import KnowledgeItem
from rag import get_embedding

# Key from environment only
if not os.environ.get("GEMINI_API_KEY"):
    print("Set GEMINI_API_KEY in your environment or .env, then run again.")
    sys.exit(1)


def main():
    db = SessionLocal()
    try:
        rows = db.scalars(select(KnowledgeItem)).all()
        if not rows:
            print("No knowledge items found. Run seed_data.py first.")
            return
        updated = 0
        for item in rows:
            emb = get_embedding(item.content or "", task_type="RETRIEVAL_DOCUMENT")
            if emb and len(emb) == 768:
                item.embedding = emb
                updated += 1
        db.commit()
        print(f"Updated {updated}/{len(rows)} embeddings with Gemini.")
    finally:
        db.close()


if __name__ == "__main__":
    main()
