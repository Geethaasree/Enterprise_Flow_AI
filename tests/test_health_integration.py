"""Integration health checks against live Docker Compose services."""

import os

import pytest
from fastapi.testclient import TestClient

from app.config import get_settings
from app.db import reset_engine
from app.main import create_app
from app.redis_client import reset_redis

pytestmark = pytest.mark.skipif(
    os.getenv("EF_INTEGRATION") != "1",
    reason="Set EF_INTEGRATION=1 with local Postgres/Redis running",
)


@pytest.fixture()
def client(monkeypatch):
    # Prefer host ports published by compose
    monkeypatch.setenv(
        "DATABASE_URL",
        os.getenv(
            "DATABASE_URL",
            "postgresql+psycopg://enterpriseflow:enterpriseflow@localhost:5432/enterpriseflow",
        ),
    )
    monkeypatch.setenv(
        "REDIS_URL",
        os.getenv("REDIS_URL", "redis://localhost:6379/0"),
    )
    get_settings.cache_clear()
    reset_engine()
    reset_redis()
    yield TestClient(create_app())
    get_settings.cache_clear()
    reset_engine()
    reset_redis()


def test_health_db(client):
    r = client.get("/health/db")
    assert r.status_code == 200
    assert r.json()["status"] == "ok"


def test_health_redis(client):
    r = client.get("/health/redis")
    assert r.status_code == 200
    assert r.json()["status"] == "ok"
