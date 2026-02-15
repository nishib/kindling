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

**Prerequisites**
- Python 3.11+
- Node.js 18+
- PostgreSQL 15+ with pgvector extension

**Backend**

```bash
# Create and activate virtual environment
python3 -m venv .venv
source .venv/bin/activate      # or .venv\Scripts\activate on Windows

# Install dependencies
pip install -r requirements.txt

# Configure environment (create .env file or export variables)
export DATABASE_URL=postgresql://user:password@localhost:5432/onboardai
export GEMINI_API_KEY=your_gemini_key
export YOU_API_KEY=your_you_com_key
export RENDER_API_KEY=your_render_key  # Optional

# Start backend server
./start-backend.sh
# Or manually: uvicorn server:app --reload --host 0.0.0.0 --port 8001
```

**Frontend (dev)**

```bash
cd frontend
npm install
npm run dev
# Opens on http://localhost:5173 with API proxy to backend on port 8001
```

Or use the convenience script:
```bash
./start-frontend.sh
```

**Database Setup**

If running PostgreSQL locally:
```bash
# Install PostgreSQL with pgvector
# On macOS: brew install postgresql pgvector
# On Ubuntu: apt-get install postgresql postgresql-contrib

# Create database
createdb onboardai

# Enable pgvector extension
psql onboardai -c "CREATE EXTENSION vector;"
```

---

## Environment variables

| Key | Purpose |
|-----|---------|
| `DATABASE_URL` | Postgres connection string (includes pgvector) |
| `GEMINI_API_KEY` | Gemini API key for embeddings, answers, and briefs |
| `YOU_API_KEY` | You.com API key for competitive and explainer search |
| `RENDER_API_KEY` | Optional: used by `/api/render/usage` to show Render usage |

---

## Deployment on Render

This project is configured for deployment on Render with PostgreSQL.

**1. Create PostgreSQL Database**

- Go to Render Dashboard → New → PostgreSQL
- Name: `kindling-db` (or your preferred name)
- Region: Choose closest to your users
- Plan: Choose based on needs (Free tier available)
- After creation, note the **Internal Database URL**

**2. Create Web Service**

- Go to Render Dashboard → New → Web Service
- Connect your GitHub repository
- Configure:
  - **Name**: `kindling`
  - **Environment**: `Python`
  - **Build Command**: `./build.sh`
  - **Start Command**: `./start.sh`
  - **Instance Type**: Choose based on needs

**3. Set Environment Variables**

In the Render dashboard, add these environment variables:

```
DATABASE_URL=<your-render-postgres-internal-url>
GEMINI_API_KEY=<your-gemini-api-key>
YOU_API_KEY=<your-you-com-api-key>
RENDER_API_KEY=<your-render-api-key>
```

**4. Enable pgvector**

After database creation, enable the pgvector extension:

```bash
# Connect to your Render database via psql
psql <your-database-external-url>

# Enable pgvector
CREATE EXTENSION IF NOT EXISTS vector;
```

**5. Deploy**

- Commit and push your changes
- Render will automatically build and deploy
- Check the deployment logs for any issues
- Visit your app URL: `https://kindling.onrender.com` (or your chosen name)

**Health Check**

Once deployed, verify the service is running:
```bash
curl https://your-app.onrender.com/health
```

Should return:
```json
{
  "status": "healthy",
  "database": "connected"
}
```

**Troubleshooting**

- **Database connection issues**: Ensure `DATABASE_URL` uses the internal URL and includes `sslmode=require`
- **Build failures**: Check that `build.sh` has execute permissions (`chmod +x build.sh`)
- **Frontend not loading**: Verify frontend build completed in build logs
- **API errors**: Check environment variables are set correctly in Render dashboard
