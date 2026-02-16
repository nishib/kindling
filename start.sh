#!/usr/bin/env bash
# Render start script
set -e

echo "Initializing database..."
python -c "
from database import engine, init_pgvector, get_db, ensure_connection
from models import Base

if ensure_connection():
    print('Creating tables...')
    Base.metadata.create_all(bind=engine)
    db = next(get_db())
    try:
        init_pgvector(db)
        print('Database initialized successfully')
    finally:
        db.close()
else:
    print('Warning: Database unavailable. Will retry on requests.')
"

echo "Starting server on port ${PORT:-8000}..."
exec python -m uvicorn server:app --host 0.0.0.0 --port ${PORT:-8000}
