"""
Phase 3: Composio sync — Notion, GitHub, Slack.
Credentials from environment only: COMPOSIO_API_KEY, COMPOSIO_PROJECT_ID.
"""
import base64
import os
from datetime import datetime, timedelta
from typing import Any, Optional

import httpx
from sqlalchemy.orm import Session

from models import KnowledgeItem, SyncState

# Read from env only; never hardcode or log
_BASE = "https://backend.composio.dev/api/v3"
_ENTITY_ID = "onboardai_velora"
_SYNC_INTERVAL_HOURS = 6


def _headers() -> dict:
    key = os.environ.get("COMPOSIO_API_KEY")
    if not key:
        return {}
    return {"x-api-key": key, "Content-Type": "application/json"}


def _get(path: str, params: Optional[dict] = None) -> Optional[dict]:
    if not _headers():
        return None
    try:
        r = httpx.get(f"{_BASE}{path}", headers=_headers(), params=params or {}, timeout=30.0)
        r.raise_for_status()
        return r.json()
    except Exception:
        return None


def _post(path: str, body: dict) -> Optional[dict]:
    if not _headers():
        return None
    try:
        r = httpx.post(f"{_BASE}{path}", headers=_headers(), json=body, timeout=60.0)
        r.raise_for_status()
        return r.json()
    except Exception:
        return None


def list_connections(toolkit_slugs: Optional[list[str]] = None) -> list[dict]:
    """List connected accounts for the project. Returns list of {id, user_id, toolkit.slug}."""
    params = {}
    if toolkit_slugs:
        params["toolkit_slugs"] = toolkit_slugs
    data = _get("/connected_accounts", params=params)
    if not data or "items" not in data:
        return []
    return data.get("items", [])


def execute_tool(tool_slug: str, connected_account_id: str, arguments: Optional[dict] = None) -> Optional[dict]:
    """Execute a Composio tool. Returns response data or None."""
    body = {"connected_account_id": connected_account_id}
    if arguments:
        body["arguments"] = arguments
    data = _post(f"/tools/execute/{tool_slug}", body)
    if not data:
        return None
    return data.get("data") if isinstance(data.get("data"), dict) else data


def _embed(text: str) -> Optional[list]:
    try:
        from rag import get_embedding
        return get_embedding(text, task_type="RETRIEVAL_DOCUMENT")
    except Exception:
        return None


def _upsert_knowledge(db: Session, source: str, content: str, metadata_: dict) -> None:
    if not content or not content.strip():
        return
    emb = _embed(content)
    item = KnowledgeItem(
        source=source,
        content=content[:100000],
        embedding=emb,
        metadata_=metadata_,
        created_at=datetime.utcnow(),
    )
    db.add(item)


def sync_notion(db: Session, connected_account_id: str) -> int:
    """Fetch Notion pages via Composio and store in DB. Returns count of items added."""
    added = 0
    # Search for pages
    out = execute_tool("NOTION_SEARCH_NOTION_PAGE", connected_account_id, {"query": ""})
    if not out:
        return 0
    results = out.get("results") if isinstance(out, dict) else None
    if not results and isinstance(out, list):
        results = out
    if not results:
        return 0
    page_ids = []
    for r in results if isinstance(results, list) else []:
        pid = r.get("id") if isinstance(r, dict) else None
        if pid:
            page_ids.append(pid)
    for page_id in page_ids[:20]:
        fetch = execute_tool("NOTION_FETCH_BLOCK_CONTENTS", connected_account_id, {"block_id": page_id})
        if not fetch:
            fetch = execute_tool("NOTION_FETCH_DATA", connected_account_id, {"resource_id": page_id})
        text_parts = []
        if isinstance(fetch, dict):
            if fetch.get("content"):
                text_parts.append(str(fetch.get("content")))
            for key in ("title", "plain_text", "rich_text"):
                if fetch.get(key):
                    text_parts.append(str(fetch[key]) if not isinstance(fetch[key], list) else " ".join(str(x) for x in fetch[key]))
            children = fetch.get("children") or fetch.get("blocks") or []
            for c in children[:50]:
                if isinstance(c, dict) and c.get("plain_text"):
                    text_parts.append(c["plain_text"])
                elif isinstance(c, dict) and c.get("rich_text"):
                    text_parts.append(" ".join(t.get("plain_text", "") for t in (c["rich_text"] if isinstance(c["rich_text"], list) else []))
        content = " ".join(text_parts).strip() or f"Page {page_id}"
        _upsert_knowledge(db, "notion", content, {"page_id": page_id, "title": content[:200], "created": datetime.utcnow().isoformat()})
        added += 1
    return added


def sync_github(db: Session, connected_account_id: str) -> int:
    """Fetch GitHub repos and READMEs via Composio. Returns count added."""
    added = 0
    out = execute_tool("GITHUB_REPOS_LIST_FOR_AUTHENTICATED_USER", connected_account_id, {"per_page": 10})
    if not out:
        return 0
    repos = out.get("repos") or out.get("data") or (out if isinstance(out, list) else [])
    if not isinstance(repos, list):
        repos = [out] if out else []
    for repo in repos[:10]:
        if not isinstance(repo, dict):
            continue
        owner = repo.get("owner", {}).get("login") if isinstance(repo.get("owner"), dict) else repo.get("owner")
        name = repo.get("name") or repo.get("repo")
        if not owner or not name:
            continue
        readme_out = execute_tool("GITHUB_REPOS_GET_README", connected_account_id, {"owner": owner, "repo": name})
        if not readme_out:
            continue
        content = readme_out.get("content") or readme_out.get("text") or str(readme_out)
        if isinstance(content, dict):
            content = content.get("content") or content.get("body") or str(content)
        if isinstance(content, str) and content.startswith("data:"):
            try:
                content = base64.b64decode(content.split(",", 1)[-1]).decode("utf-8", errors="replace")
            except Exception:
                pass
        _upsert_knowledge(db, "github", content or f"README {owner}/{name}", {"repo_name": name, "owner": owner, "created": datetime.utcnow().isoformat()})
        added += 1
    return added


def sync_slack(db: Session, connected_account_id: str) -> int:
    """Fetch Slack #general and #product history via Composio. Returns count added."""
    added = 0
    channels_out = execute_tool("SLACK_CONVERSATIONS_LIST", connected_account_id, {"limit": 50})
    if not channels_out:
        return 0
    ch_list = channels_out.get("channels") or channels_out.get("data") or (channels_out if isinstance(channels_out, list) else [])
    if not isinstance(ch_list, list):
        ch_list = []
    channel_ids = {}
    for ch in ch_list:
        if not isinstance(ch, dict):
            continue
        name = (ch.get("name") or "").lower()
        cid = ch.get("id")
        if name in ("general", "product") and cid:
            channel_ids[name] = cid
    for ch_name, ch_id in channel_ids.items():
        hist = execute_tool("SLACK_CONVERSATIONS_HISTORY", connected_account_id, {"channel": ch_id, "limit": 30})
        if not hist:
            continue
        messages = hist.get("messages") or hist.get("data") or (hist if isinstance(hist, list) else [])
        if not isinstance(messages, list):
            continue
        for msg in messages[:30]:
            if not isinstance(msg, dict):
                continue
            text = msg.get("text") or msg.get("content") or ""
            if not text:
                continue
            user = msg.get("user") or msg.get("username") or "unknown"
            ts = msg.get("ts") or datetime.utcnow().isoformat()
            _upsert_knowledge(db, "slack", text, {"channel": f"#{ch_name}", "author": user, "timestamp": ts, "created": datetime.utcnow().isoformat()})
            added += 1
    return added


def _set_sync_state(db: Session, key: str, value: Any) -> None:
    row = db.get(SyncState, key)
    if row:
        row.value = value
        row.updated_at = datetime.utcnow()
    else:
        db.add(SyncState(key=key, value=value))
    db.commit()


def _get_sync_state(db: Session, key: str) -> Any:
    row = db.get(SyncState, key)
    return row.value if row and row.value else None


def run_sync(db: Session) -> dict:
    """
    Run full Composio sync: list connections, fetch Notion/GitHub/Slack, store in DB.
    Updates last_sync_at. Returns {notion, github, slack, last_sync_at, next_sync_at}.
    """
    result = {"notion": 0, "github": 0, "slack": 0, "last_sync_at": None, "next_sync_at": None}
    if not _headers():
        return result
    connections = list_connections(["notion", "github", "slack"])
    by_toolkit = {}
    for c in connections:
        if not isinstance(c, dict):
            continue
        tid = (c.get("toolkit") or {}).get("slug") if isinstance(c.get("toolkit"), dict) else c.get("toolkit")
        if tid:
            by_toolkit.setdefault(tid, []).append(c.get("id"))
    for toolkit, ids in by_toolkit.items():
        if not ids:
            continue
        ca_id = ids[0]
        if toolkit == "notion":
            result["notion"] = sync_notion(db, ca_id)
        elif toolkit == "github":
            result["github"] = sync_github(db, ca_id)
        elif toolkit == "slack":
            result["slack"] = sync_slack(db, ca_id)
    db.commit()
    now = datetime.utcnow()
    next_at = now + timedelta(hours=_SYNC_INTERVAL_HOURS)
    _set_sync_state(db, "last_sync_at", now.isoformat())
    _set_sync_state(db, "next_sync_at", next_at.isoformat())
    result["last_sync_at"] = now.isoformat()
    result["next_sync_at"] = next_at.isoformat()
    return result


def get_sync_status(db: Session) -> dict:
    """Return last_sync_at and next_sync_at for dashboard."""
    last = _get_sync_state(db, "last_sync_at")
    next_ = _get_sync_state(db, "next_sync_at")
    if not next_ and last:
        try:
            dt = datetime.fromisoformat(last.replace("Z", "+00:00"))
            next_ = (dt + timedelta(hours=_SYNC_INTERVAL_HOURS)).isoformat()
        except Exception:
            pass
    if not next_:
        # Default: next sync in 6 hours so dashboard always shows something
        next_ = (datetime.utcnow() + timedelta(hours=_SYNC_INTERVAL_HOURS)).isoformat()
    return {"last_sync_at": last, "next_sync_at": next_}
