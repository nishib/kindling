# Ignition — Lighting the fire for modern ERP fluency

## What This Is

Ignition is a learning product dedicated to the **accounting space**, **ERP space**, and everything needed to know about **Campfire’s major customers**. It combines structured learning paths, a customer hub with one-click briefs, a glossary, and RAG-powered Q&A fed by You.com, optional Perplexity, and optional ingestion (Firecrawl last).

## Core Value

Campfire employees and stakeholders learn accounting and ERP fundamentals at their own pace, get instant “what to know before a call” briefs for key customers, and stay current on customer and market news—all in one place, with answers tailored to knowledge level and cited sources.

---

## Phased implementation (chunks)

Work is split into chunks. **Start with Learning pathways**; **Firecrawl is last.**

| Chunk | Focus | Deliverables |
|-------|--------|--------------|
| **1. Learning pathways** | Accounting & ERP structured learning | Modules (Accounting 101 → GL → revenue recognition; ERP 101 → legacy → Campfire), short text per module, “Ask the assistant,” optional quiz. Learn section in UI. |
| **2. Glossary** | Curated terms for chat + browse | Terms (GL, revenue recognition, multi-entity, etc.) in DB or `knowledge_items`; “What is [term]?” in chat; optional glossary page. |
| **3. Customer hub** | Customer cards + prepare brief | Customer cards (what they do, why Campfire, talking points); You.com + optional Gemini extraction; “Prepare for [Customer]” one-click brief. Customers section in UI. |
| **4. Customer & market brief + You.com** | Briefs and search extension | Customer & market brief (customer news + accounting/ERP industry via You.com + structured-brief pattern). Extend You.com to customer search and accounting/ERP explainer search; cache and feed RAG. |
| **5. Perplexity (optional)** | Second source for answers | Optional Perplexity integration for cited, up-to-date answers (e.g. “Explain revenue recognition”, “What does Replit do?”). |
| **6. Firecrawl (last)** | Ingest from URLs | Scrape and ingest customer sites, Crunchbase, accounting/ERP pages into `knowledge_items`. Optional; implement after above. |

---

## Requirements by chunk

### Validated

(None yet — ship to validate)

### Chunk 1 — Learning pathways

- [ ] **Accounting path**: Structured modules (e.g. Accounting 101 → General ledger → Revenue recognition); short text per module.
- [ ] **ERP path**: Structured modules (e.g. ERP 101 → Legacy vs modern → Campfire’s place); short text per module.
- [ ] “Ask the assistant” from each module (suggested questions or pass module context into chat).
- [ ] Optional quiz per module or at path end (Gemini-generated or fixed).
- [ ] **Learn** section in UI: list paths, show modules, next/previous, optional completion state.
- [ ] API: e.g. `GET /api/learning/paths`, `GET /api/learning/paths/:id/modules`, optionally `POST /api/learning/quiz` (generate or serve quiz).

### Chunk 2 — Glossary

- [ ] Curated terms (GL, revenue recognition, multi-entity, ERP, etc.) stored in DB or `knowledge_items` with metadata (e.g. `type: glossary`).
- [ ] “What is [term]?” in chat returns definition + related terms (RAG or direct lookup).
- [ ] Optional glossary page in UI: search/filter, list terms.
- [ ] API: e.g. `GET /api/glossary`, `GET /api/glossary/:term` or rely on RAG with glossary in knowledge.

### Chunk 3 — Customer hub

- [ ] Customer cards: what they do, why Campfire, talking points, “What to know before a call.”
- [ ] Data from You.com search per customer + optional Gemini extraction (one-pager from search results).
- [ ] “Prepare for [Customer]” one-click brief: customer card + recent intel + suggested questions.
- [ ] **Customers** section in UI: list customers, card detail, “Prepare for [Customer]” button.
- [ ] API: e.g. `GET /api/customers`, `GET /api/customers/:id`, `POST /api/customers/:id/prepare-brief`; customer intel model or extended intel table.

### Chunk 4 — Customer & market brief + You.com

- [ ] **Customer & market brief**: Separate brief for customer news + accounting/ERP industry (You.com + same structured-brief pattern as product brief).
- [ ] Extend You.com to **customer search** (per major customer) and **accounting/ERP explainer** search; cache results in DB and feed into RAG.
- [ ] API: e.g. `GET /api/brief/customer-market`; extend `you_com.py` with customer and explainer queries.

### Chunk 5 — Perplexity (optional)

- [ ] Optional Perplexity API integration for selected queries (e.g. “Explain revenue recognition”, “What does Replit do?”).
- [ ] Blend or fallback with Gemini RAG when Perplexity is enabled; cited answers in response.

### Chunk 6 — Firecrawl (last)

- [ ] Firecrawl (or Jina) integration: scrape and ingest customer sites, Crunchbase, accounting/ERP pages into `knowledge_items`.
- [ ] Background or on-demand job to refresh ingested URLs; embeddings updated for RAG.

### Cross-cutting

- [ ] Assessment questions for ERP/accounting/customer familiarity; building block progression and answer simplification by knowledge level.
- [ ] Infrastructure: Render, PostgreSQL + pgvector, FastAPI, React (Learn, Customers, Ask, Intel).

### Out of Scope

- Multi-company support — Campfire-only for now
- User authentication — focus on core learning experience first
- Progress tracking across sessions — optional later
- Mobile app — web interface sufficient

---

## Context

**About Campfire.ai:**
- AI-native ERP platform for finance & accounting teams
- Customers: Replit, PostHog, Decagon, Heidi Health, CloudZero, and 100+ companies
- Competing with NetSuite, QuickBooks, Oracle, SAP; key differentiators: automation, multi-entity, Ember AI (Claude)

**Problem Space:**
- Need to understand accounting and ERP fundamentals, not just Campfire
- Need to know major customers (what they do, why Campfire, talking points) before calls
- Need a single place for customer + market news and learning

**Technical Approach:**
- **Chunks 1–4**: You.com, Gemini, existing RAG; learning paths, glossary, customer hub, customer & market brief.
- **Chunk 5**: Optional Perplexity for cited answers.
- **Chunk 6 (last)**: Firecrawl (or Jina) for URL ingestion into `knowledge_items`.

## Constraints

- **Knowledge adaptability**: Answers must adapt to user level (beginner / intermediate / advanced)
- **API costs**: Prefer free tiers; Perplexity and Firecrawl optional
- **Simplicity**: Clear sections (Learn, Customers, Ask, Intel) without unnecessary complexity

## Key Decisions

| Decision | Rationale |
|----------|-----------|
| Learning pathways first | Establishes structure and content; no new infra. |
| Glossary before customer hub | Shared RAG/knowledge foundation; simple to add. |
| Customer hub before Firecrawl | You.com + Gemini enough for customer cards; Firecrawl adds richness later. |
| Firecrawl last | Ingest is optional and more complex; build value with paths, glossary, customers, briefs first. |
| You.com extended in Chunk 4 | Customer & market brief and RAG enrichment in same chunk. |
| Perplexity optional | Better cited answers when enabled; not required for core flow. |

---
*Last updated: 2026-02-11 — phased chunks: Learning pathways first, Firecrawl last*
