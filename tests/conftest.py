"""Safety: block pytest from wiping Coolify/live Postgres.

Use scripts/run-db-tests.sh (enterpriseflow_test on :5433).
Override only with EF_ALLOW_LIVE_DB=1 (never against prod).
"""

from __future__ import annotations

import os

import pytest


def _looks_like_live_db(url: str) -> bool:
    u = (url or "").lower()
    if not u:
        return False
    if "enterpriseflow_test" in u:
        return False
    if "@db:5432/enterpriseflow" in u:
        return True
    if "163.192.122.138" in u:
        return True
    if "@ef-db:" in u:
        return True
    return False


def pytest_configure() -> None:
    if os.getenv("EF_ALLOW_LIVE_DB") == "1":
        return
    url = os.getenv("DATABASE_URL") or ""
    if _looks_like_live_db(url):
        pytest.exit(
            "Refusing pytest against live Coolify DB. Use ./scripts/run-db-tests.sh "
            f"(DATABASE_URL={url!r})",
            returncode=2,
        )
