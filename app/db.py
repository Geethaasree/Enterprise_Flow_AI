"""Database engine helpers (connectivity only in Phase 1)."""

from __future__ import annotations

from collections.abc import Generator
from contextlib import contextmanager

from sqlalchemy import create_engine, text
from sqlalchemy.engine import Engine

from app.config import Settings, get_settings

_engine: Engine | None = None


def get_engine(settings: Settings | None = None) -> Engine:
    global _engine
    if _engine is None:
        cfg = settings or get_settings()
        _engine = create_engine(cfg.database_url, pool_pre_ping=True)
    return _engine


def reset_engine() -> None:
    """Test helper: drop cached engine."""
    global _engine
    if _engine is not None:
        _engine.dispose()
    _engine = None


@contextmanager
def db_session(settings: Settings | None = None) -> Generator:
    engine = get_engine(settings)
    with engine.connect() as conn:
        yield conn


def check_db(settings: Settings | None = None) -> bool:
    with db_session(settings) as conn:
        conn.execute(text("SELECT 1"))
    return True
