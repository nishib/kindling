"""RAG pipeline: Gemini embeddings, pgvector search, Gemini LLM synthesis with citations."""
import os
from typing import Optional

from sqlalchemy import select
from sqlalchemy.orm import Session

from models import KnowledgeItem, CompetitorIntel

# API key from environment only; never hardcode or log
_GEMINI_KEY = "GEMINI_API_KEY"
_EMBED_MODEL = "models/gemini-embedding-001"
_LLM_MODEL = "models/gemini-2.0-flash"
_EMBED_DIM = 768
_TOP_K = 5


def _client():
    """Return Gemini client if key is set, else None. Key is read from env only."""
    api_key = os.environ.get(_GEMINI_KEY)
    if not api_key:
        return None
    try:
        from google import genai
        return genai.Client(api_key=api_key)
    except Exception:
        return None


def get_embedding(text: str, task_type: str = "RETRIEVAL_QUERY") -> Optional[list]:
    """
    Get 768-dim embedding from Gemini. task_type: RETRIEVAL_QUERY for questions,
    RETRIEVAL_DOCUMENT for documents. Returns None if key missing or API fails.
    """
    client = _client()
    if not client:
        return None
    try:
        from google.genai import types
        config = types.EmbedContentConfig(
            task_type=task_type,
            output_dimensionality=_EMBED_DIM,
        )
        result = client.models.embed_content(
            model=_EMBED_MODEL,
            contents=text,
            config=config,
        )
        if not result.embeddings:
            return None
        emb = result.embeddings[0]
        values = getattr(emb, "values", None) or getattr(emb, "embedding", None)
        if values is None and hasattr(emb, "__iter__"):
            values = list(emb)
        return values if isinstance(values, list) else list(values) if values else None
    except Exception:
        return None


def search_similar(db: Session, query_embedding: list, k: int = _TOP_K):
    """Return up to k KnowledgeItems nearest to query_embedding (cosine distance)."""
    if not query_embedding or len(query_embedding) != _EMBED_DIM:
        return []
    try:
        stmt = (
            select(KnowledgeItem)
            .where(KnowledgeItem.embedding.isnot(None))
            .order_by(KnowledgeItem.embedding.cosine_distance(query_embedding))
            .limit(k)
        )
        return list(db.scalars(stmt).all())
    except (AttributeError, TypeError):
        # Fallback: order by id when .cosine_distance not available (e.g. older pgvector)
        stmt = (
            select(KnowledgeItem)
            .where(KnowledgeItem.embedding.isnot(None))
            .order_by(KnowledgeItem.id)
            .limit(k)
        )
        return list(db.scalars(stmt).all())


def _format_context(item: KnowledgeItem) -> dict:
    """Build citation-friendly context from a KnowledgeItem."""
    meta = item.metadata_ or {}
    title = meta.get("title") or meta.get("repo_name") or meta.get("channel") or item.source
    if meta.get("author"):
        title = f"{title} ({meta['author']})"
    snippet = (item.content or "")[:400].strip()
    if len((item.content or "")) > 400:
        snippet += "..."
    return {
        "source": item.source,
        "title": str(title),
        "snippet": snippet,
        "content": item.content,
    }


def _competitor_context_items(db: Session, limit: int = 5) -> list[dict]:
    """Fetch recent competitor intel (You.com cache) for RAG context."""
    from sqlalchemy import select
    stmt = (
        select(CompetitorIntel)
        .order_by(CompetitorIntel.created_at.desc())
        .limit(limit)
    )
    rows = list(db.scalars(stmt).all())
    return [
        {"source": "you_com", "title": f"{r.competitor_name} ({r.intel_type})", "snippet": (r.content or "")[:300], "content": r.content}
        for r in rows
    ]


def generate_answer(question: str, context_items: list, competitor_context: Optional[list] = None) -> tuple[str, list]:
    """
    Use Gemini to synthesize an answer from retrieved contexts + optional competitor intel.
    Returns (answer_text, citations). citations: list of {source, title, snippet} for UI.
    """
    client = _client()
    contexts = [_format_context(it) for it in context_items]
    if competitor_context:
        contexts.extend(competitor_context)
    citations = [{"source": c["source"], "title": c["title"], "snippet": c["snippet"]} for c in contexts]

    if not client or not contexts:
        if not contexts:
            return "I couldn't find relevant information in the knowledge base. Try rephrasing or ask about Velora's product, team, or competitors.", []
        # Fallback: concatenate snippets
        answer = "Based on the following sources:\n\n"
        for c in contexts:
            answer += f"[{c['source']}: {c['title']}]\n{c['snippet']}\n\n"
        return answer.strip(), citations

    try:
        from google.genai import types
        context_blob = "\n\n---\n\n".join(
            f"[Source: {c['source']} – {c['title']}]\n{c['content']}" for c in contexts
        )
        prompt = f"""You are an onboarding assistant for Velora, an AI customer support startup. Answer the question using ONLY the provided context (internal knowledge and competitor intelligence). Be concise and cite sources (e.g. "According to [Notion: Product Strategy]..." or "[You.com: Intercom pricing]...").

Context:
{context_blob}

Question: {question}

Answer (2–4 short paragraphs, cite sources):"""

        response = client.models.generate_content(
            model=_LLM_MODEL,
            contents=types.Part.from_text(prompt),
            config=types.GenerateContentConfig(
                temperature=0.2,
                max_output_tokens=1024,
            ),
        )
        text = None
        if response.candidates:
            part = response.candidates[0].content.parts[0] if response.candidates[0].content.parts else None
            if part:
                text = getattr(part, "text", None) or str(part)
        if not text:
            text = "I couldn't generate an answer. Please try rephrasing."
        return text.strip(), citations
    except Exception:
        if contexts:
            fallback = "Based on the available sources:\n\n"
            for c in contexts:
                fallback += f"• [{c['source']}] {c['title']}: {c['snippet']}\n"
            return fallback.strip(), citations
        return "An error occurred while generating the answer.", []


def ask(db: Session, question: str) -> dict:
    """
    Full RAG: embed question, search knowledge + competitor intel (You.com cache), generate answer.
    Returns {answer, citations}. Competitor intel is included so answers cite You.com research.
    """
    import numpy as np
    query_embedding = get_embedding(question, task_type="RETRIEVAL_QUERY")
    if not query_embedding:
        np.random.seed(hash(question) % (2**32))
        query_embedding = np.random.randn(_EMBED_DIM).tolist()
    items = search_similar(db, query_embedding, k=_TOP_K)
    competitor_context = _competitor_context_items(db, limit=5)
    answer, citations = generate_answer(question, items, competitor_context=competitor_context)
    return {"answer": answer, "citations": citations}
