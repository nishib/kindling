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
  - Backend: `erp_concept_graph.py` stores the ERP concept graph and supports “recommended next” based on completed concepts.
  - Frontend: `App.jsx` renders a **Skill Map + Knowledge Graph** section with clickable concepts, full detail (description, why it matters, dependencies), and a “Recommended next” rail.

- **Learning paths**
  - Backend: `learning_paths.py` defines two in‑code paths:
    - `accounting` — Accounting 101 → GL → revenue recognition.
    - `erp` — ERP 101 → legacy vs modern → Campfire’s place.
  - Frontend: `App.jsx` loads these paths and renders modules in the Learn view.

- **Competitive intelligence (You.com)**
  - Backend: `you_com.py` wraps You.com search and caching into `CompetitorIntel` and `YouComCache` for competitor and explainer intel.
  - Frontend: `App.jsx` shows a live search box plus a cached competitor feed with a “Refresh intel” action.

- **Simulated ERP scenarios**
  - Backend: `scenarios.py` + `scenario_engine/` implement templates, synthetic data, a rules engine, and an AI coach. Scenario runs are stored in Postgres when available and mirrored in an in‑memory store so they still work if the DB is down.
  - Frontend:
    - `ScenariosView.jsx` — left rail of scenarios, runner panel, and debrief view.
    - `ScenarioRunner.jsx` — step‑by‑step scenario UI with a synthetic company snapshot, synthetic datasets (invoices, integration events, failed webhooks, journal entries), scenario choices, metrics, and an AI Coach side panel.
    - `ScenarioDebrief.jsx` — post‑run metrics, strengths, opportunities, concepts to review, and recommended next scenarios.

- **RAG + Gemini**
  - `rag.py` implements a Gemini‑backed RAG pipeline over `KnowledgeItem` and `CompetitorIntel` using pgvector.
  - `generate_daily_brief` creates a JSON daily brief from recent knowledge + intel.

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

**Frontend (dev)**

Use the React/Vite dev server from either the repo root or the `frontend` directory to run the UI locally.

---

## Environment variables

| Key | Purpose |
|-----|---------|
| `DATABASE_URL` | Postgres connection string (includes pgvector) |
| `GEMINI_API_KEY` | Gemini API key for embeddings, answers, and briefs |
| `YOU_API_KEY` | You.com API key for competitive and explainer search |
| `RENDER_API_KEY` | Optional: used by `/api/render/usage` to show Render usage |
