# Ignition — Lighting the fire for modern ERP fluency

**Ignition helps Campfire teams learn the accounting and ERP space and everything they need to know about Campfire’s major customers** — structured learning paths, customer hub with one-click briefs, glossary, and RAG-powered Q&A. Integrates **You.com**, **Gemini**, and optionally **Perplexity**; **Firecrawl** is last.

---

## Build order (chunks)

Work is split into phases. **Start with Learning pathways**; **Firecrawl is last.**

| Chunk | Focus |
|-------|--------|
| **1. Learning pathways** | Accounting & ERP structured modules (Accounting 101 → GL → revenue recognition; ERP 101 → legacy → Campfire). Short text per module, “Ask the assistant,” optional quiz. **Learn** section in UI. |
| **2. Glossary** | Curated terms (GL, revenue recognition, multi-entity, etc.) in DB or `knowledge_items`. “What is [term]?” in chat + optional glossary page. |
| **3. Customer hub** | Customer cards (what they do, why Campfire, talking points). You.com + optional Gemini extraction. **“Prepare for [Customer]”** one-click brief. **Customers** section in UI. |
| **4. Customer & market brief + You.com** | Customer & market brief (customer news + accounting/ERP industry). Extend You.com to customer search and accounting/ERP explainer search; cache and feed RAG. |
| **5. Perplexity (optional)** | Optional second source for cited, up-to-date answers. |
| **6. Firecrawl (last)** | Scrape and ingest customer sites, Crunchbase, accounting/ERP pages into `knowledge_items`. |

---

## Business use case

Campfire teams need to:

- **Learn** accounting and ERP fundamentals (GL, revenue recognition, legacy vs modern ERP, Campfire’s place).
- **Prepare for customer calls** with one place for customer cards and a “Prepare for [Customer]” one-click brief.
- **Stay current** on customer and market news (customer & market brief) and competitive intel.

This product provides (by chunk):

- **Chunk 1** — **Accounting & ERP learning paths** with structured modules, “Ask the assistant,” and optional quiz.
- **Chunk 2** — **Glossary** for “What is [term]?” in chat and an optional glossary page.
- **Chunk 3** — **Customer hub** with customer cards and “Prepare for [Customer]” one-click brief.
- **Chunk 4** — **Customer & market brief** and extended You.com (customer + accounting/ERP search) for RAG.
- **Chunk 5** — **Perplexity** (optional) for cited answers.
- **Chunk 6** — **Firecrawl** (last): ingest from customer and educational URLs.

---

## Tech stack and why

| Layer | Choice | Why |
|-------|--------|-----|
| **API** | FastAPI (Python) | Async-ready, OpenAPI, simple dependency injection for DB and env. |
| **Frontend** | React + Vite | Fast dev loop, proxy to API; sections: Learn, Customers, Ask, Intel. |
| **Database** | PostgreSQL + pgvector | Relational data + vector similarity for RAG; knowledge, intel, glossary, customer data. |
| **Embeddings & LLM** | Google Gemini | 768-d embeddings and generative answers; optional extraction, quiz generation. |
| **Search / intel** | You.com | Competitor intel (existing); extend to customer + accounting/ERP search (Chunk 4); cache and feed RAG. |
| **Optional** | Perplexity | Second source for cited answers (Chunk 5). |
| **Optional (last)** | Firecrawl | Ingest customer and educational pages into `knowledge_items` (Chunk 6). |
| **Scheduling** | Celery + Redis | Optional background tasks. |
| **Hosting** | Render | Web service, worker, Postgres (pgvector) from `render.yaml`. |

Secrets (API keys) are read from the environment only (e.g. `.env` locally, Render env vars in production).

---

## AI integrations (by chunk)

| Provider | Role | Chunk |
|----------|------|--------|
| **Gemini** | RAG embeddings + LLM; optional extraction (customer one-pagers), quiz generation. | All |
| **You.com** | Competitor intel (existing); extend to customer + accounting/ERP search; cache and feed RAG. | 4 |
| **Perplexity** | Optional: cited, up-to-date answers. | 5 |
| **Firecrawl** | Optional, **last**: scrape and ingest customer sites, Crunchbase, accounting/ERP pages into `knowledge_items`. | 6 |
| **Render** | Hosting + optional usage API. | — |

---

## Technical implementation

### High-level flow

1. **Knowledge** — RAG uses `knowledge_items` (manual/seed for Chunks 1–2; optional Firecrawl in Chunk 6) and Gemini embeddings. Glossary in DB or `knowledge_items`.
2. **Learning paths** — Stored as config or DB; modules have short text and optional quiz (Chunk 1).
3. **Customer intel** — You.com per customer + optional Gemini extraction; customer cards and “Prepare for [Customer]” (Chunk 3).
4. **Customer & market brief** — You.com (customer + accounting/ERP news) → structured brief (Chunk 4).
5. **RAG Q&A** — Question → embedding → similarity over knowledge + intel (+ optional Perplexity in Chunk 5) → Gemini synthesis → answer + citations.

### Core components (current + planned by chunk)

- **`server.py`** — Health, `/api/ask`, `/api/brief`, `/api/intel/*`. **Chunk 1**: `/api/learning/paths`, `/api/learning/paths/:id/modules`. **Chunk 2**: `/api/glossary`. **Chunk 3**: `/api/customers`, `/api/customers/:id`, `/api/customers/:id/prepare-brief`. **Chunk 4**: `/api/brief/customer-market`; extend `you_com.py`.
- **`rag.py`** — Embedding, pgvector, context from knowledge + intel, Gemini synthesis; glossary and customer context as chunks land.
- **`models.py`** — `KnowledgeItem`, `CompetitorIntel`, `SyncState`; **Chunk 2**: glossary (or metadata on KnowledgeItem); **Chunk 3**: customer card / customer intel; **Chunk 6**: ingestion state if needed.
- **Frontend** — **Learn** (Chunk 1), **Glossary** (Chunk 2), **Customers** (Chunk 3), **Ask**, **Intel**; briefs (existing + Chunk 4).

---

## Technical details relevant to autonomy

1. **Secrets only in environment** — All API keys via `os.environ` / `.env`.
2. **Worker** — Celery for background ingest (e.g. Chunk 6) and refresh.
3. **Resilient startup** — App starts even if DB is down; `/health` reports status.
4. **RESTful API** — All features exposed as HTTP endpoints.
5. **Single deploy** — `render.yaml` for web service, worker, Postgres (pgvector).
6. **Caching** — Intel (competitor + customer) in DB; RAG and feeds read from DB.
7. **No frontend secrets** — Backend proxies to You.com, Perplexity, etc.

---

## Run the full stack (local)

**Terminal 1 — Backend**

```bash
source .venv/bin/activate   # or .venv\Scripts\activate on Windows
pip install -r requirements.txt
docker-compose up -d postgres redis
export DATABASE_URL=postgresql://postgres:postgres@localhost:5432/onboardai
uvicorn server:app --reload --port 8000
```

**Terminal 2 — Frontend** (from repo root)

```bash
npm install
npm run dev
```

Or from `frontend/`: `cd frontend && npm install && npm run dev`.

Open **http://localhost:3000**.

---

## Deploy on Render

1. Connect the repo; use the Blueprint from `render.yaml`.
2. Set env vars: `DATABASE_URL`, `REDIS_URL`, `GEMINI_API_KEY`, `YOU_API_KEY`; optionally `PERPLEXITY_API_KEY`, `FIRECRAWL_API_KEY`, `RENDER_API_KEY`.
3. Deploy.

---

## API keys (reference)

| Key | Purpose | Chunk |
|-----|--------|--------|
| **GEMINI_API_KEY** | RAG embeddings + LLM ([Google AI Studio](https://aistudio.google.com/)). | All |
| **YOU_API_KEY** | Competitor + (Chunk 4) customer + accounting/ERP search ([You.com API](https://api.you.com)). | 4 |
| **PERPLEXITY_API_KEY** | Optional: cited answers ([Perplexity API](https://docs.perplexity.ai)). | 5 |
| **FIRECRAWL_API_KEY** | Optional, **last**: ingest customer and educational pages. | 6 |
| **RENDER_API_KEY** | Optional: usage (workspaces, services, bandwidth). | — |

---

## URLs

- **API:** http://localhost:8000  
- **Health:** http://localhost:8000/health  
- **Frontend:** http://localhost:3000  
- **PDF brief:** http://localhost:8000/static/onboarding_brief.pdf  
