"""Redis client helpers (connectivity only in Phase 1)."""

from __future__ import annotations

import redis

from app.config import Settings, get_settings

_client: redis.Redis | None = None


def get_redis(settings: Settings | None = None) -> redis.Redis:
    global _client
    if _client is None:
        cfg = settings or get_settings()
        _client = redis.Redis.from_url(cfg.redis_url, decode_responses=True)
    return _client


def reset_redis() -> None:
    """Test helper: drop cached client."""
    global _client
    if _client is not None:
        try:
            _client.close()
        except OSError:
            # already closed
            pass
    _client = None


def check_redis(settings: Settings | None = None) -> bool:
    client = get_redis(settings)
    return client.ping() is True
