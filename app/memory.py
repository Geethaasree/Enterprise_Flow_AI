"""Redis memory, cache, locks, rate limits (Phase 8).

# ponytail: one module; split if Redis surface grows.
"""

from __future__ import annotations

import json
import logging
import time
import uuid
from collections.abc import Iterator
from contextlib import contextmanager
from dataclasses import asdict, dataclass
from typing import Any

from app.redis_client import get_redis

logger = logging.getLogger(__name__)

SESSION_TTL = 60 * 60 * 24  # 24h
CACHE_TTL_DEFAULT = 60
BIZ_TTL = 60 * 60 * 24 * 30
RATE_WINDOW = 60
RATE_MAX_DEFAULT = 30
MAX_TURNS_KEEP = 20
SUMMARY_EVERY = 6


@dataclass
class Turn:
    role: str  # user | assistant | system
    content: str
    ts: float
    meta: dict[str, Any] | None = None


def _sess_key(session_id: str) -> str:
    return f"ef:session:{session_id}"


def _sum_key(session_id: str) -> str:
    return f"ef:summary:{session_id}"


def _biz_key(customer_code: str) -> str:
    return f"ef:biz:{customer_code.upper()}"


def _cache_key(ns: str, key: str) -> str:
    return f"ef:cache:{ns}:{key}"


def _rate_key(bucket: str) -> str:
    return f"ef:rate:{bucket}"


def _lock_key(name: str) -> str:
    return f"ef:lock:{name}"


# --- conversation / short-term ---


def append_turn(
    session_id: str,
    role: str,
    content: str,
    *,
    meta: dict[str, Any] | None = None,
    ttl: int = SESSION_TTL,
) -> list[dict[str, Any]]:
    r = get_redis()
    key = _sess_key(session_id)
    turn = Turn(role=role, content=content, ts=time.time(), meta=meta)
    r.rpush(key, json.dumps(asdict(turn)))
    r.ltrim(key, -MAX_TURNS_KEEP, -1)
    r.expire(key, ttl)
    turns = get_turns(session_id)
    if len(turns) >= SUMMARY_EVERY and len(turns) % SUMMARY_EVERY == 0:
        refresh_summary(session_id, turns)
    return turns


def get_turns(session_id: str) -> list[dict[str, Any]]:
    r = get_redis()
    raw = r.lrange(_sess_key(session_id), 0, -1)
    out: list[dict[str, Any]] = []
    for item in raw:
        try:
            out.append(json.loads(item))
        except json.JSONDecodeError:
            continue
    return out


def refresh_summary(session_id: str, turns: list[dict[str, Any]] | None = None) -> str:
    """Deterministic rolling summary (no LLM)."""
    turns = turns if turns is not None else get_turns(session_id)
    if not turns:
        return ""
    # keep early bullets + note last intents
    bullets: list[str] = []
    for t in turns[:-3]:
        role = t.get("role", "?")
        content = (t.get("content") or "")[:120].replace("\n", " ")
        bullets.append(f"{role}: {content}")
    summary = " | ".join(bullets[-8:])  # cap
    get_redis().set(_sum_key(session_id), summary, ex=SESSION_TTL)
    return summary


def get_summary(session_id: str) -> str:
    return get_redis().get(_sum_key(session_id)) or ""


def build_context_bundle(
    session_id: str | None,
    *,
    customer_code: str | None = None,
    max_recent: int = 4,
) -> dict[str, Any]:
    """Selective context — never dump full history into every call."""
    bundle: dict[str, Any] = {
        "session_id": session_id,
        "summary": "",
        "recent_turns": [],
        "business_memory": {},
    }
    if session_id:
        turns = get_turns(session_id)
        bundle["recent_turns"] = turns[-max_recent:]
        bundle["summary"] = get_summary(session_id)
        if not bundle["summary"] and len(turns) > max_recent:
            bundle["summary"] = refresh_summary(session_id, turns)
    if customer_code:
        bundle["business_memory"] = get_business_memory(customer_code)
    return bundle


def context_prompt_block(bundle: dict[str, Any]) -> str:
    """Compact text block for agents / notes."""
    parts: list[str] = []
    if bundle.get("summary"):
        parts.append(f"Prior summary: {bundle['summary']}")
    recent = bundle.get("recent_turns") or []
    if recent:
        lines = [f"{t.get('role')}: {(t.get('content') or '')[:80]}" for t in recent]
        parts.append("Recent:\n" + "\n".join(lines))
    biz = bundle.get("business_memory") or {}
    if biz:
        parts.append("Business memory: " + json.dumps(biz, default=str)[:300])
    return "\n".join(parts)


# --- long-term business memory ---


def set_business_memory(customer_code: str, data: dict[str, Any], *, ttl: int = BIZ_TTL) -> None:
    r = get_redis()
    key = _biz_key(customer_code)
    flat = {k: json.dumps(v) if not isinstance(v, str) else v for k, v in data.items()}
    if flat:
        r.hset(key, mapping=flat)
        r.expire(key, ttl)


def merge_business_memory(customer_code: str, data: dict[str, Any], *, ttl: int = BIZ_TTL) -> dict[str, Any]:
    cur = get_business_memory(customer_code)
    cur.update(data)
    set_business_memory(customer_code, cur, ttl=ttl)
    return cur


def get_business_memory(customer_code: str) -> dict[str, Any]:
    raw = get_redis().hgetall(_biz_key(customer_code)) or {}
    out: dict[str, Any] = {}
    for k, v in raw.items():
        try:
            out[k] = json.loads(v)
        except (json.JSONDecodeError, TypeError):
            out[k] = v
    return out


# --- cache ---


def cache_get(ns: str, key: str) -> Any | None:
    raw = get_redis().get(_cache_key(ns, key))
    if raw is None:
        return None
    try:
        return json.loads(raw)
    except json.JSONDecodeError:
        return raw


def cache_set(ns: str, key: str, value: Any, *, ttl: int = CACHE_TTL_DEFAULT) -> None:
    get_redis().set(_cache_key(ns, key), json.dumps(value, default=str), ex=ttl)


def cache_delete(ns: str, key: str) -> None:
    get_redis().delete(_cache_key(ns, key))


# --- distributed lock ---


@contextmanager
def distributed_lock(
    name: str,
    *,
    ttl_seconds: float = 10.0,
    wait_seconds: float = 5.0,
    poll: float = 0.05,
) -> Iterator[bool]:
    """Redis SET NX lock. Yields True if acquired.

    # ponytail: no Redlock; single Redis is enough for this stack.
    """
    r = get_redis()
    token = uuid.uuid4().hex
    key = _lock_key(name)
    deadline = time.monotonic() + wait_seconds
    acquired = False
    while time.monotonic() < deadline:
        if r.set(key, token, nx=True, px=int(ttl_seconds * 1000)):
            acquired = True
            break
        time.sleep(poll)
    try:
        yield acquired
    finally:
        if acquired:
            # release only if we still own it
            cur = r.get(key)
            if cur == token:
                r.delete(key)


# --- rate limit (fixed window) ---


def rate_limit_allow(bucket: str, *, limit: int = RATE_MAX_DEFAULT, window: int = RATE_WINDOW) -> tuple[bool, dict[str, int]]:
    """Return (allowed, meta). Increments counter for bucket."""
    r = get_redis()
    key = _rate_key(bucket)
    # fixed window via INCR + EXPIRE
    count = r.incr(key)
    if count == 1:
        r.expire(key, window)
    ttl = r.ttl(key)
    meta = {"count": int(count), "limit": limit, "window": window, "ttl": int(ttl or 0)}
    return count <= limit, meta


def clear_session(session_id: str) -> None:
    r = get_redis()
    r.delete(_sess_key(session_id), _sum_key(session_id))
