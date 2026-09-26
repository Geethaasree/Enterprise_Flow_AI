"""Phase 8 Redis memory / cache / lock / rate-limit tests."""

from __future__ import annotations

import os
import uuid

import pytest

from app.memory import (
    append_turn,
    build_context_bundle,
    cache_delete,
    cache_get,
    cache_set,
    clear_session,
    distributed_lock,
    get_business_memory,
    get_summary,
    get_turns,
    merge_business_memory,
    rate_limit_allow,
    refresh_summary,
)
from app.redis_client import reset_redis

pytestmark = pytest.mark.skipif(
    not os.getenv("EF_DB_TESTS") and not os.getenv("EF_INTEGRATION"),
    reason="needs Redis",
)


@pytest.fixture(autouse=True)
def _redis():
    reset_redis()
    yield
    reset_redis()


def test_session_turns_and_summary():
    sid = f"t_{uuid.uuid4().hex[:8]}"
    clear_session(sid)
    for i in range(6):
        append_turn(sid, "user" if i % 2 == 0 else "assistant", f"msg-{i} about orders")
    turns = get_turns(sid)
    assert len(turns) == 6
    summary = get_summary(sid) or refresh_summary(sid)
    assert summary
    bundle = build_context_bundle(sid, max_recent=2)
    assert len(bundle["recent_turns"]) == 2
    assert bundle["summary"]
    clear_session(sid)
    assert get_turns(sid) == []


def test_business_memory():
    code = f"C{uuid.uuid4().hex[:6].upper()}"
    merge_business_memory(code, {"last_sku": "LAPTOP-PRO-14", "last_qty": 3})
    mem = get_business_memory(code)
    assert mem["last_sku"] == "LAPTOP-PRO-14"
    assert mem["last_qty"] == 3


def test_cache_roundtrip():
    k = f"k{uuid.uuid4().hex[:6]}"
    cache_set("test", k, {"a": 1}, ttl=30)
    assert cache_get("test", k) == {"a": 1}
    cache_delete("test", k)
    assert cache_get("test", k) is None


def test_distributed_lock_exclusive():
    name = f"lock-{uuid.uuid4().hex[:8]}"
    with distributed_lock(name, ttl_seconds=2, wait_seconds=0.2) as a:
        assert a is True
        with distributed_lock(name, ttl_seconds=2, wait_seconds=0.15) as b:
            assert b is False
    with distributed_lock(name, ttl_seconds=2, wait_seconds=0.5) as c:
        assert c is True


def test_rate_limit():
    bucket = f"rl-{uuid.uuid4().hex[:8]}"
    ok1, m1 = rate_limit_allow(bucket, limit=3, window=30)
    ok2, _ = rate_limit_allow(bucket, limit=3, window=30)
    ok3, _ = rate_limit_allow(bucket, limit=3, window=30)
    ok4, m4 = rate_limit_allow(bucket, limit=3, window=30)
    assert ok1 and ok2 and ok3
    assert not ok4
    assert m4["count"] == 4
    assert m1["limit"] == 3


def test_workflows_session_api():
    from fastapi.testclient import TestClient

    from app.main import create_app

    client = TestClient(create_app())
    sid = f"api_{uuid.uuid4().hex[:8]}"
    r1 = client.post(
        "/workflows/run",
        json={"message": "What can you do?", "session_id": sid},
    )
    assert r1.status_code == 200
    assert r1.json()["session_id"] == sid
    r2 = client.get(f"/workflows/session/{sid}")
    assert r2.status_code == 200
    body = r2.json()
    assert len(body["turns"]) >= 2
    assert body["turns"][0]["role"] == "user"
