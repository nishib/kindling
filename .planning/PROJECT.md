# Campfire ERP Onboarding Assistant

## What This Is

An intelligent onboarding assistant for new Campfire.ai employees that assesses their ERP knowledge, teaches foundational concepts in progressive building blocks, and connects them to Campfire's specific context through real company data. The system adapts explanations based on knowledge level and supplements with real-time industry research.

## Core Value

New Campfire employees gain ERP fluency at their own pace through personalized learning that meets them where they are - from "What does ERP stand for?" to understanding Campfire's competitive positioning against NetSuite - all grounded in real company knowledge and industry context.

## Requirements

### Validated

(None yet — ship to validate)

### Active

**Assessment & Personalization:**
- [ ] Explicit assessment questions to gauge ERP knowledge level
- [ ] Building block progression (basic → intermediate → advanced concepts)
- [ ] Answer simplification based on detected knowledge level
- [ ] Progressive learning path that builds on confirmed understanding

**ERP Knowledge Foundation:**
- [ ] Fundamental concepts: What is ERP, why it matters, core components
- [ ] Traditional ERP landscape: NetSuite, SAP, Oracle, QuickBooks
- [ ] Modern/AI-native ERP evolution and industry trends
- [ ] Finance & accounting ERP specifics (general ledger, revenue automation, etc.)
- [ ] Campfire's approach and competitive differentiators

**Company Context Integration:**
- [ ] Real Notion sync: Company docs, projects, rules, onboarding materials
- [ ] Real Slack sync: Team conversations, culture, historical context
- [ ] RAG pipeline retrieves relevant company-specific examples
- [ ] Citations link back to specific Notion pages and Slack threads

**You.com Intelligence:**
- [ ] Real-time ERP industry trends and market intelligence
- [ ] Learning resource discovery (articles, guides, comparisons)
- [ ] Competitor analysis (NetSuite, SAP, QuickBooks features/positioning)
- [ ] Supplemental explanations with authoritative external sources

**Agent Capabilities:**
- [ ] Interactive Q&A that adapts to user knowledge level
- [ ] Composio integrations sync Notion and Slack automatically
- [ ] Scheduled syncs keep company knowledge current
- [ ] Simple React interface for conversational learning

**Infrastructure:**
- [ ] Deployed on Render with background jobs
- [ ] PostgreSQL with pgvector for semantic search
- [ ] FastAPI backend for API and agent logic
- [ ] Background worker for scheduled syncs

### Out of Scope

- Multi-company support — Campfire-only for now
- User authentication — focus on core learning experience first
- Progress tracking across sessions — stateless Q&A for v1
- Mobile app — web interface sufficient
- Real-time collaboration — async learning focus
- Advanced analytics — track basics only

## Context

**About Campfire.ai:**
- AI-native ERP platform for finance & accounting teams
- Competing with legacy systems (NetSuite, QuickBooks, Oracle, SAP)
- Built for venture-funded startups seeking high-velocity finance operations
- Ember AI: Conversational interface powered by Anthropic's Claude
- Key differentiators: Automation, multi-entity management, intuitive AI-first design
- Customers: Replit, PostHog, Decagon, Heidi Health, CloudZero, and 100+ companies
- Funding: $100M+ raised (Series B led by Accel & Ribbit)

**Problem Space:**
- New employees at ERP companies need to understand:
  1. ERP fundamentals (what it is, why it matters)
  2. Industry landscape (competitors, legacy vs modern)
  3. Company-specific approach (how Campfire differs)
  4. Internal context (projects, culture, rules)
- Knowledge levels vary wildly (finance background vs software eng vs sales)
- Generic onboarding doesn't adapt to individual understanding
- Manual onboarding consumes founder/manager time

**Learning Philosophy:**
- **Building blocks**: Start with "What is ERP?" and progressively build complexity
- **Adaptive depth**: Simplify for beginners, add nuance for experienced folks
- **Real examples**: Connect concepts to actual Campfire projects (from Notion)
- **Industry context**: Supplement with You.com research on ERP trends
- **Company grounding**: Use real Slack conversations to show culture/context

**Technical Approach:**
- **Composio**: Sync real Notion (company docs) and Slack (team conversations)
- **You.com**: Fetch ERP industry intelligence, learning resources, competitor analysis
- **Render**: Host FastAPI backend + PostgreSQL + cron jobs
- **RAG Pipeline**: Semantic search over company knowledge + external research
- **Free/Sponsored APIs**: Gemini for embeddings/LLM, sponsor credits where available

**Assessment Strategy:**
Explicit questions before diving into topics:
- "Have you worked with ERP systems before?"
- "Do you know what general ledger means?"
- "Are you familiar with NetSuite or QuickBooks?"
- "What's your role at Campfire?" (finance vs eng vs sales context)

Based on answers, adjust:
- Vocabulary (avoid jargon for beginners)
- Depth (overview vs technical details)
- Examples (analogies for concepts vs direct explanations)
- Resources (introductory articles vs advanced comparisons)

## Constraints

- **Real data only**: No fake/mock company data - use actual Notion/Slack content
- **Knowledge adaptability**: Must genuinely adjust to user level, not one-size-fits-all
- **Composio access**: Requires proper Notion and Slack authentication
- **API costs**: Prefer free tiers (Gemini), use sponsor credits wisely
- **Simplicity**: Focus on core learning experience, not complex features

## Key Decisions

| Decision | Rationale | Outcome |
|----------|-----------|---------|
| Explicit assessment questions | Clear signal of knowledge level vs inferring from behavior | — Pending |
| Building block progression | ERP concepts have natural hierarchy (basics → advanced) | — Pending |
| Real Notion/Slack data | Authentic company context beats fabricated examples | — Pending |
| You.com for learning resources | Industry trends + authoritative sources supplement teaching | — Pending |
| Simplified answers + resources | Dual approach: adjust explanation AND provide external learning | — Pending |
| FastAPI + PostgreSQL + React | Familiar stack, pgvector for semantic search | — Pending |
| Gemini for embeddings/LLM | Free tier sufficient, avoid OpenAI costs | — Pending |
| No progress tracking v1 | Stateless Q&A simpler to build, iterate based on usage | — Pending |

---
*Last updated: 2026-02-11 after vision pivot to Campfire ERP onboarding*
