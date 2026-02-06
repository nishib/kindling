# OnboardAI

AI-powered onboarding for Velora employees. Built for hackathon demo with **Composio**, **You.com**, and **Render**.

## Run the full stack (local demo)

There **is** a frontend — a React app that talks to the API. Run **two terminals**:

**Terminal 1 – Backend (API)**  
From the project root (`OnboardingTool`):

```bash
# If you use conda: conda activate paibl  (or your env)
source .venv/bin/activate   # or: .venv\Scripts\activate on Windows
pip install -r requirements.txt
# Optional: start DB + Redis first, then seed
# docker-compose up -d postgres redis
# export DATABASE_URL=postgresql://postgres:postgres@localhost:5432/onboardai
# python seed_data.py
uvicorn server:app --reload --port 8000
```

**Terminal 2 – Frontend (demo UI)**  
From the project root:

```bash
cd frontend
npm install
npm run dev
```

Then open **http://localhost:3000** in your browser. The frontend proxies `/api` and `/health` to the backend at port 8000, so you get:

- **Chat** – Ask questions (RAG / Phase 2)
- **Sync status** – Last/next Composio sync + “Trigger sync” (Phase 3)
- **Competitive Intelligence Feed** – You.com intel + “Refresh intel” (Phase 4)
- **Render Usage** – Workspaces, services, bandwidth (Phase 5)

- API: http://localhost:8000  
- Health: http://localhost:8000/health  
- **Frontend (demo): http://localhost:3000**  
- PDF brief: http://localhost:8000/static/onboarding_brief.pdf  

> **Note:** `render.yaml` is **not** a command — it’s a config file you use when deploying to [Render](https://render.com) (connect repo and Render reads it).

## Quick start (minimal)

```bash
# Backend
python3 -m venv .venv && source .venv/bin/activate
pip install -r requirements.txt
uvicorn server:app --reload

# DB + seed (optional; for full RAG/sync/intel)
docker-compose up -d postgres redis
export DATABASE_URL=postgresql://postgres:postgres@localhost:5432/onboardai
python seed_data.py

# Frontend (second terminal)
cd frontend && npm install && npm run dev
```  

## Deploy (Render)

1. Connect repo to Render; use `render.yaml` (web + worker + PostgreSQL with `vector` extension).
2. Add env vars in Render dashboard: `DATABASE_URL` (from DB), `REDIS_URL`, and when ready:
   - **GEMINI_API_KEY** (Phase 2 – RAG)
   - **COMPOSIO_API_KEY** (Phase 3 – Notion/GitHub/Slack)
   - **YOU_API_KEY** (Phase 4 – competitor research)
   - **RENDER_API_KEY** (Phase 5 – usage dashboard; from Render Dashboard → Account Settings → API Keys)

## When to get API keys

| Key              | When        | Where / use |
|------------------|------------|-------------|
| **GEMINI_API_KEY** | Phase 2 (RAG) | [Google AI Studio](https://aistudio.google.com/) – embeddings + LLM |
| **COMPOSIO_API_KEY** | Phase 3 (sync) | [Composio](https://app.composio.dev) – Notion, GitHub, Slack |
| **YOU_API_KEY** | Phase 4 (intel) | [You.com API](https://api.you.com) – competitor research |
| **RENDER_API_KEY** | Phase 5 (usage) | Render Dashboard → Account Settings → API Keys – services & bandwidth |

No keys required for Phase 1 (foundation + demo data).

## Sponsor integrations (all phases)

| Phase | Sponsor   | Use | API / UI |
|-------|-----------|-----|----------|
| 1     | —         | Foundation + demo data | Seed data, mock RAG |
| 2     | **Gemini** | RAG (embeddings + LLM) | `POST /api/ask`, chat Q&A |
| 3     | **Composio** | Notion, GitHub, Slack sync | `GET /api/sync/status`, `POST /api/sync/trigger`, header + Trigger sync |
| 4     | **You.com** | Competitor intel (Intercom, Zendesk, Gorgias) | `GET /api/intel/feed`, `POST /api/intel/refresh`, feed + Refresh intel |
| 5     | **Render** | Usage (workspaces, services, bandwidth) | `GET /api/render/usage`, Render Usage section |
| 5     | **Composio** | Worker + cron (sync every 6h) | Celery worker in `render.yaml` |

- **Composio**: Notion, GitHub, Slack sync (Phase 3); worker + cron (Phase 5).
- **You.com**: Competitor intelligence feed + research in answers (Phase 4).
- **Render**: Hosting (API, worker, PostgreSQL); `render.yaml` + dashboard; Phase 5 usage (workspaces, services, bandwidth) via API.
