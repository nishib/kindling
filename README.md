## Kindling — Sparking ERP fluency

**Kindling is an internal tool that helps Campfire teams build ERP intuition by combining structured learning with hands‑on simulation.**

Today it ships three main pieces:

- **ERP Skill Map + Knowledge Graph** — a navigable map of core ERP and accounting concepts (GL, revenue recognition, integrations, etc.) with dependencies and “recommended next” suggestions.
- **Learning paths** — two short, opinionated paths for **Accounting fundamentals** and **ERP fundamentals** with concise, markdown‑formatted modules.
- **Simulated ERP scenarios** — a decision‑driven “practice environment” where you debug synthetic revenue and integration issues with an AI coach and synthetic datasets.
- **Competitive intelligence** — You.com‑powered web + news search and a cached ERP competitor feed (NetSuite, SAP, QuickBooks, Oracle).

The original customer hub / glossary / Firecrawl plans are not implemented in this repo and are no longer described here.

---

## What’s implemented

- **Skill Map & concept graph**
  - Backend: `erp_concept_graph.py` exposes concepts, dependencies, and “recommend next” via:
    - `GET /api/learning/concept-graph`
    - `GET /api/learning/concepts/{concept_id}`
    - `GET /api/learning/recommend-next?completed=...`
  - Frontend: `App.jsx` renders a **Skill Map + Knowledge Graph** section with:
    - Clickable concepts and full detail (description, why it matters, dependencies).
    - A “Recommended next” rail that calls `/api/learning/recommend-next`.

- **Learning paths**
  - Backend: `learning_paths.py` defines two in‑code paths:
    - `accounting` — Accounting 101 → GL → revenue recognition.
    - `erp` — ERP 101 → legacy vs modern → Campfire’s place.
  - API:
    - `GET /api/learning/paths` — list of paths with module counts.
    - `GET /api/learning/paths/{path_id}` — ordered modules with markdown content.
  - Frontend: `App.jsx` pulls these endpoints and renders modules in the Learn view.

- **Competitive intelligence (You.com)**
  - Backend:
    - `you_com.py` wraps You.com search and caching into `CompetitorIntel` and `YouComCache`.
    - `server.py` exposes:
      - `GET /api/intel/feed` — cached competitor feed.
      - `POST /api/intel/refresh` — refresh competitor intel.
      - `GET /api/intel/search` — live web + news search.
      - `GET /api/intel/customer` and `/api/intel/explainer` — customer and explainer search with caching.
  - Frontend: `App.jsx` shows:
    - A live search box that calls `/api/intel/search`.
    - A cached feed with “Refresh intel” calling `/api/intel/refresh`.

- **Simulated ERP scenarios**
  - Backend:
    - `scenarios.py` + `scenario_engine/` implement templates, synthetic data, a rules engine, and an AI coach.
    - Routes under `/api/scenarios`:
      - `GET /api/scenarios` — list available scenario templates.
      - `POST /api/scenarios/{scenario_id}/start` — start a run (DB + in‑memory fallback).
      - `POST /api/scenarios/{run_id}/decision` — apply a choice and advance state.
      - `POST /api/scenarios/{run_id}/coach` — ask an AI coach about the current run.
      - `GET /api/scenarios/{run_id}/debrief` — debrief summary, metrics, strengths, and suggested next scenarios.
    - Data is persisted in Postgres when available (`ERPScenarioRun`, `ERPScenarioEvent`) but also kept in an in‑memory store so scenarios still work if the DB is down.
  - Frontend:
    - `ScenariosView.jsx` — left rail of scenarios, runner panel, and debrief view.
    - `ScenarioRunner.jsx` — step‑by‑step scenario UI with:
      - Synthetic company snapshot.
      - Synthetic datasets (invoices, integration events, failed webhooks, journal entries).
      - Scenario choices and metrics (simulated hours, revenue error %, open recon issues, audit risk).
      - AI Coach side panel (`/api/scenarios/{run_id}/coach`).
    - `ScenarioDebrief.jsx` — post‑run metrics, strengths, opportunities, concepts to review, and recommended next scenarios.

- **RAG + Gemini**
  - `rag.py` implements a Gemini‑backed RAG pipeline over `KnowledgeItem` and `CompetitorIntel` using pgvector.
  - `generate_daily_brief` creates a JSON daily brief from recent knowledge + intel.
  - The endpoints that call this are not wired into the current UI, but the module and models (`KnowledgeItem`, `CompetitorIntel`, `YouComCache`, `SyncState`) are ready for use.

---

## Tech stack

| Layer | Choice |
|-------|--------|
| **API** | FastAPI (Python) with pgvector + SQLAlchemy |
| **Frontend** | React + Vite (single‑page app served by FastAPI in production) |
| **Database** | PostgreSQL with `pgvector` for embeddings and scenario state |
| **Embeddings & LLM** | Google Gemini for embeddings, RAG answers, and daily brief generation |
| **External intel** | You.com for competitive and explainer search, cached in Postgres |
| **Hosting** | Render (see `render.yaml`) |

Secrets (API keys, DB URLs) are read from the environment only (e.g. `.env` locally, Render env vars in production).

---

## Running locally

**Backend**

```bash
python -m venv .venv
source .venv/bin/activate      # or .venv\Scripts\activate on Windows
pip install -r requirements.txt

# Example Postgres URL; adjust to your local setup
export DATABASE_URL=postgresql://postgres:postgres@localhost:5432/onboardai

# Optional: set keys for Gemini and You.com
export GEMINI_API_KEY=...
export YOU_API_KEY=...

uvicorn server:app --reload --port 8000
```

**Frontend (dev)** — from repo root:

```bash
npm install
npm run dev
```

or from `frontend/`:

```bash
cd frontend
npm install
npm run dev
```

Open `http://localhost:3000`.

---

## Key API endpoints

- **Health**
  - `GET /health`

- **Learning**
  - `GET /api/learning/paths`
  - `GET /api/learning/paths/{path_id}`
  - `GET /api/learning/concept-graph`
  - `GET /api/learning/concepts/{concept_id}`
  - `GET /api/learning/recommend-next?completed=...`

- **Competitive intelligence**
  - `GET /api/intel/feed`
  - `POST /api/intel/refresh`
  - `GET /api/intel/search?q=...`
  - `GET /api/intel/customer?name=...`
  - `GET /api/intel/explainer?term=...`

- **Simulated scenarios**
  - `GET /api/scenarios`
  - `POST /api/scenarios/{scenario_id}/start`
  - `POST /api/scenarios/{run_id}/decision`
  - `POST /api/scenarios/{run_id}/coach`
  - `GET /api/scenarios/{run_id}/debrief`

---

## Environment variables

| Key | Purpose |
|-----|---------|
| `DATABASE_URL` | Postgres connection string (includes pgvector) |
| `GEMINI_API_KEY` | Gemini API key for embeddings, answers, and briefs |
| `YOU_API_KEY` | You.com API key for competitive and explainer search |
| `RENDER_API_KEY` | Optional: used by `/api/render/usage` to show Render usage |

---

## URLs

- **API:** `http://localhost:8000`
- **Health:** `http://localhost:8000/health`
- **Frontend:** `http://localhost:3000`
- **PDF brief:** `http://localhost:8000/static/onboarding_brief.pdf`
