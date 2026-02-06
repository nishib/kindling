# OnboardAI

## What This Is

OnboardAI is an autonomous AI agent that onboards new hires at early-stage startups by continuously learning from internal tools (Notion, GitHub, Slack) and external research (competitor intelligence, market trends). New employees get personalized context about the domain, competitors, and current projects without founders repeating explanations. The agent runs 24/7, auto-updating as company data changes.

## Core Value

New hires get accurate, cited answers to onboarding questions within seconds, sourced from both internal company knowledge and real-time external research - without any manual curation.

## Requirements

### Validated

(None yet — ship to validate)

### Active

- [ ] Agent answers onboarding questions with citations from multiple sources
- [ ] Composio integrations sync data from Notion, GitHub, and Slack automatically
- [ ] You.com integration researches competitors and provides market intelligence
- [ ] Agent demonstrates autonomous operation (scheduled syncs, webhook triggers)
- [ ] Demo shows full pipeline: sync → research → answer with citations
- [ ] Competitive Intelligence Feed displays auto-updated competitor activity
- [ ] RAG pipeline retrieves relevant context from vector embeddings
- [ ] Simple React interface for Q&A and viewing intelligence feeds
- [ ] Deployed on Render with background jobs and persistent storage
- [ ] Demo data (fictional Velora company) pre-seeded and realistic

### Out of Scope

- Production-ready error handling — hackathon demo quality sufficient
- Multi-tenant architecture — single company demo only
- User authentication — not needed for demo
- Email notifications — show UI only, don't actually send
- Advanced analytics dashboard — show core metrics only
- Mobile app — web interface only
- Real-time chat — async Q&A sufficient for demo

## Context

**Hackathon Context:**
- Timeline: 3 hours to build
- Demo: 3 minutes to show judges
- Judging criteria: Autonomy, Idea, Technical Implementation, Tool Use (3 sponsors), Presentation
- Sponsors: Composio (integrations), You.com (search/research), Render (deployment)
- Personal motivation: Experienced onboarding pain firsthand at early-stage startups

**Problem Space:**
- Startups lose 20-40 hours per new hire on manual onboarding
- Founders repeat same context about competitors, market, projects
- New employees take weeks to build domain mental models
- Documentation becomes stale quickly as startups evolve

**Demo Company (Fictional):**
- Name: Velora
- Product: AI-powered customer support platform for e-commerce
- Team size: 15 people, seed-funded
- Competitors: Intercom, Zendesk, Gorgias
- Domain: Clear, relatable, easy to research

**Technical Approach:**
- Composio: Multi-tool integration nervous system (Notion, GitHub, Slack, Google Drive)
- You.com: External intelligence layer (competitor monitoring, industry research)
- Render: Infrastructure (FastAPI backend, PostgreSQL, cron jobs, webhooks)
- RAG Pipeline: Semantic search with citations over combined internal + external knowledge
- Free APIs: Use sponsor credits and free tiers (Gemini for embeddings/LLM)

**Build vs Mock Strategy:**
- BUILD: Smart Q&A, Composio syncing, You.com research, RAG pipeline, cron jobs, webhooks
- MOCK: 5-page PDF brief (pre-generate), dashboard visualizations, email notifications
- Focus: Demo autonomy and sponsor integration, not production polish

## Constraints

- **Timeline**: 3 hours total build time — extreme focus required
- **Cost**: Free APIs only (sponsor credits, Gemini, no OpenAI)
- **Sponsor Coverage**: Must showcase all 3 sponsors prominently in demo
- **Demo Length**: 3 minutes to show full pipeline working
- **Data**: All demo data must be pre-seeded and realistic
- **Scope**: Hackathon-quality code, not production-ready
- **Deployment**: Must be live on Render for autonomy proof

## Key Decisions

| Decision | Rationale | Outcome |
|----------|-----------|---------|
| Fictional demo company (Velora) | Cleaner data, no permission issues, controllable narrative | — Pending |
| FastAPI + PostgreSQL + React | Fast to build, pgvector built-in, familiar stack | — Pending |
| Pre-generate PDF brief | Too slow/risky for live demo, focus on Q&A autonomy | — Pending |
| Gemini for embeddings/LLM | Free tier, sponsor credits limited, avoid OpenAI costs | — Pending |
| Mock dashboard visualizations | Time-intensive, not core to autonomy demonstration | — Pending |
| 6-hour sync schedule + webhooks | Shows both scheduled autonomy and instant reactivity | — Pending |

---
*Last updated: 2026-02-06 after initialization*
