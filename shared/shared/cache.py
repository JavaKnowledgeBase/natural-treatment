"""Tier 1 (shared reference) / Tier 2 (per-session) Redis cache helpers.

There is no database in this system -- Redis is the only stateful component.
Tier 1 keys (`ref:*`) hold non-PII herb/compound/symptom/rule data loaded
from the seed bundle and are shared across all sessions. Tier 2 keys
(`session:{sid}:*`) hold everything about one user's session, are namespaced
per session, and are hard-deleted on purge -- see `purge_session`.
"""
from __future__ import annotations

import json
import os
import time
from typing import Any, Optional

import redis.asyncio as redis

SESSION_TTL_SECONDS = int(os.environ.get("SESSION_IDLE_TIMEOUT_SECONDS", "1800"))
REF_TTL_SECONDS = 6 * 60 * 60
LIVE_FALLBACK_TTL_SECONDS = 60 * 60

_client: Optional[redis.Redis] = None


def get_redis() -> redis.Redis:
    global _client
    if _client is None:
        url = os.environ.get("REDIS_URL", "redis://localhost:6379/0")
        _client = redis.from_url(url, decode_responses=True)
    return _client


# ---------------------------------------------------------------------------
# Tier 1 -- shared reference cache (no PII)
# ---------------------------------------------------------------------------

def _ref_key(kind: str, item_id: str) -> str:
    return f"ref:{kind}:{item_id}"


async def set_ref(kind: str, item_id: str, value: dict[str, Any], ttl: int = REF_TTL_SECONDS) -> None:
    r = get_redis()
    await r.set(_ref_key(kind, item_id), json.dumps(value), ex=ttl)


async def get_ref(kind: str, item_id: str) -> Optional[dict[str, Any]]:
    r = get_redis()
    raw = await r.get(_ref_key(kind, item_id))
    return json.loads(raw) if raw else None


async def list_ref_ids(kind: str) -> list[str]:
    r = get_redis()
    prefix = f"ref:{kind}:"
    ids = []
    async for key in r.scan_iter(match=f"{prefix}*"):
        ids.append(key[len(prefix):])
    return ids


async def list_refs(kind: str) -> list[dict[str, Any]]:
    ids = await list_ref_ids(kind)
    items = []
    for item_id in ids:
        value = await get_ref(kind, item_id)
        if value is not None:
            items.append(value)
    return items


async def set_kb_version(version: str) -> None:
    r = get_redis()
    await r.set("ref:kb_version", version)


async def get_kb_version() -> Optional[str]:
    r = get_redis()
    return await r.get("ref:kb_version")


# ---------------------------------------------------------------------------
# Tier 2 -- per-session cache (PII, TTL'd, purged on exit)
# ---------------------------------------------------------------------------

def _session_prefix(sid: str) -> str:
    return f"session:{sid}:"


async def _touch(sid: str) -> None:
    """Slide the TTL forward on every key belonging to this session."""
    r = get_redis()
    prefix = _session_prefix(sid)
    async for key in r.scan_iter(match=f"{prefix}*"):
        await r.expire(key, SESSION_TTL_SECONDS)


async def create_session(sid: str) -> None:
    r = get_redis()
    now = time.time()
    await r.hset(
        f"{_session_prefix(sid)}meta",
        mapping={"session_id": sid, "current_step": "greeting", "created_at": now, "last_active_at": now},
    )
    await r.hset(f"{_session_prefix(sid)}profile", mapping={"_placeholder": "1"})
    await _touch(sid)


async def get_meta(sid: str) -> Optional[dict[str, Any]]:
    r = get_redis()
    data = await r.hgetall(f"{_session_prefix(sid)}meta")
    return data or None


async def set_step(sid: str, step: str) -> None:
    r = get_redis()
    await r.hset(f"{_session_prefix(sid)}meta", mapping={"current_step": step, "last_active_at": time.time()})
    await _touch(sid)


async def get_profile(sid: str) -> dict[str, Any]:
    r = get_redis()
    data = await r.hgetall(f"{_session_prefix(sid)}profile")
    data.pop("_placeholder", None)
    for field in ("medications", "allergies", "chronic_conditions"):
        if field in data:
            data[field] = json.loads(data[field])
    return data


async def update_profile(sid: str, fields: dict[str, Any]) -> None:
    """Only ever called from an extraction pass over free text the user
    volunteered -- no code path in this system prompts for these fields."""
    r = get_redis()
    encoded = {}
    for key, value in fields.items():
        encoded[key] = json.dumps(value) if isinstance(value, list) else value
    if encoded:
        await r.hset(f"{_session_prefix(sid)}profile", mapping=encoded)
        await _touch(sid)


async def append_chat_message(sid: str, role: str, text: str) -> None:
    r = get_redis()
    await r.xadd(f"{_session_prefix(sid)}chat", {"role": role, "text": text, "ts": time.time()})
    await _touch(sid)


async def get_chat_history(sid: str) -> list[dict[str, Any]]:
    r = get_redis()
    entries = await r.xrange(f"{_session_prefix(sid)}chat")
    return [{"role": fields["role"], "text": fields["text"], "ts": float(fields["ts"])} for _, fields in entries]


async def add_cached_item(sid: str, cache_name: str, item_id: str, value: dict[str, Any]) -> None:
    r = get_redis()
    await r.hset(f"{_session_prefix(sid)}{cache_name}", item_id, json.dumps(value))
    await _touch(sid)


async def remove_cached_item(sid: str, cache_name: str, item_id: str) -> None:
    r = get_redis()
    await r.hdel(f"{_session_prefix(sid)}{cache_name}", item_id)
    await _touch(sid)


async def list_cached_items(sid: str, cache_name: str) -> list[dict[str, Any]]:
    r = get_redis()
    raw = await r.hgetall(f"{_session_prefix(sid)}{cache_name}")
    return [json.loads(v) for v in raw.values()]


async def push_list_item(sid: str, list_name: str, value: dict[str, Any]) -> None:
    r = get_redis()
    await r.rpush(f"{_session_prefix(sid)}{list_name}", json.dumps(value))
    await _touch(sid)


async def get_list(sid: str, list_name: str) -> list[dict[str, Any]]:
    r = get_redis()
    raw = await r.lrange(f"{_session_prefix(sid)}{list_name}", 0, -1)
    return [json.loads(v) for v in raw]


async def clear_list(sid: str, list_name: str) -> None:
    r = get_redis()
    await r.delete(f"{_session_prefix(sid)}{list_name}")


async def purge_session(sid: str) -> int:
    """Hard-delete every Tier 2 key for this session. Non-blocking via UNLINK."""
    r = get_redis()
    prefix = _session_prefix(sid)
    keys = [key async for key in r.scan_iter(match=f"{prefix}*")]
    if keys:
        await r.unlink(*keys)
    return len(keys)


async def session_exists(sid: str) -> bool:
    r = get_redis()
    return await r.exists(f"{_session_prefix(sid)}meta") == 1
