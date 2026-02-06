# OnboardAI

AI-powered onboarding for Velora employees. Built for hackathon demo with **Composio**, **You.com**, and **Render**.

## Quick start (local)

```bash
# Backend
python3 -m venv .venv && source .venv/bin/activate  # or: .venv\Scripts\activate on Windows
pip install -r requirements.txt
# Set DATABASE_URL (or use default postgresql://postgres:postgres@localhost:5432/onboardai)
# For Phase 2 RAG: copy .env.example to .env and set GEMINI_API_KEY (never commit .env)
uvicorn server:app --reload

# DB + seed (requires PostgreSQL with pgvector)
docker-compose up -d postgres redis
export DATABASE_URL=postgresql://postgres:postgres@localhost:5432/onboardai
python seed_data.py
# Optional: with GEMINI_API_KEY set, seed_data uses real embeddings; else run: python embed_all.py

# Frontend
cd frontend && npm install && npm run dev
```

- API: http://localhost:8000  
- Health: http://localhost:8000/health  
- Frontend: http://localhost:3000  
- PDF brief: http://localhost:8000/static/onboarding_brief.pdf  

## Deploy (Render)

1. Connect repo to Render; use `render.yaml` (web + worker + PostgreSQL with `vector` extension).
2. Add env vars in Render dashboard: `DATABASE_URL` (from DB), `REDIS_URL`, and when ready:
   - **GEMINI_API_KEY** (Phase 2 – RAG)
   - **COMPOSIO_API_KEY** (Phase 3 – Notion/GitHub/Slack)
   - **YOU_API_KEY** (Phase 4 – competitor research)

## When to get API keys

| Key              | When        | Where / use |
|------------------|------------|-------------|
| **GEMINI_API_KEY** | Phase 2 (RAG) | [Google AI Studio](https://aistudio.google.com/) – embeddings + LLM |
| **COMPOSIO_API_KEY** | Phase 3 (sync) | [Composio](https://app.composio.dev) – Notion, GitHub, Slack |
| **YOU_API_KEY** | Phase 4 (intel) | [You.com API](https://api.you.com) – competitor research |

No keys required for Phase 1 (foundation + demo data).

## Sponsor integrations

- **Composio**: Notion, GitHub, Slack sync (Phase 3); worker + cron (Phase 5).
- **You.com**: Competitor intelligence feed + research in answers (Phase 4).
- **Render**: Hosting (API, worker, PostgreSQL); `render.yaml` + dashboard.
