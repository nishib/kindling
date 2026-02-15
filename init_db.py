#!/usr/bin/env python3
"""Initialize database tables and pgvector extension."""
from sqlalchemy import text
from database import engine, init_pgvector, SessionLocal
from models import Base

def main():
    print("Initializing database...")

    # Test connection
    try:
        with engine.connect() as conn:
            result = conn.execute(text("SELECT version()"))
            version = result.scalar()
            print(f"✓ Connected to PostgreSQL: {version[:50]}...")
    except Exception as e:
        print(f"✗ Database connection failed: {e}")
        return False

    # Enable pgvector
    try:
        db = SessionLocal()
        init_pgvector(db)
        db.close()
        print("✓ pgvector extension enabled")
    except Exception as e:
        print(f"✗ Failed to enable pgvector: {e}")
        return False

    # Create all tables
    try:
        Base.metadata.create_all(bind=engine)
        print("✓ Database tables created")

        # List created tables
        with engine.connect() as conn:
            result = conn.execute(text("""
                SELECT tablename
                FROM pg_tables
                WHERE schemaname = 'public'
                ORDER BY tablename
            """))
            tables = [row[0] for row in result]
            print(f"\nCreated tables ({len(tables)}):")
            for table in tables:
                print(f"  - {table}")
    except Exception as e:
        print(f"✗ Failed to create tables: {e}")
        return False

    print("\n✓ Database initialization complete!")
    return True

if __name__ == "__main__":
    success = main()
    exit(0 if success else 1)
