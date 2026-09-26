"""Phase 14 — Databricks path is optional and env-driven."""

from __future__ import annotations

import os

from app.databricks_path import (
    apply_databricks_env,
    databricks_configured,
    observability_status,
    tracking_backend,
)


def test_default_backend_is_file(monkeypatch):
    monkeypatch.delenv("MLFLOW_TRACKING_URI", raising=False)
    monkeypatch.delenv("DATABRICKS_HOST", raising=False)
    monkeypatch.delenv("DATABRICKS_TOKEN", raising=False)
    assert tracking_backend() == "file"
    assert databricks_configured() is False
    info = apply_databricks_env()
    assert info["applied"] is False
    assert info["backend"] == "file"


def test_databricks_env_sets_tracking_uri(monkeypatch):
    monkeypatch.delenv("MLFLOW_TRACKING_URI", raising=False)
    monkeypatch.setenv("DATABRICKS_HOST", "https://adb-demo.cloud.databricks.com")
    monkeypatch.setenv("DATABRICKS_TOKEN", "dapi-test-token")
    info = apply_databricks_env()
    assert info["databricks_configured"] is True
    assert info["applied"] is True
    assert os.environ["MLFLOW_TRACKING_URI"] == "databricks"
    assert tracking_backend() == "databricks"


def test_explicit_uri_not_overridden(monkeypatch):
    monkeypatch.setenv("MLFLOW_TRACKING_URI", "file:/tmp/ef-mlruns")
    monkeypatch.setenv("DATABRICKS_HOST", "https://adb-demo.cloud.databricks.com")
    monkeypatch.setenv("DATABRICKS_TOKEN", "dapi-test-token")
    info = apply_databricks_env()
    assert info["applied"] is False
    assert os.environ["MLFLOW_TRACKING_URI"] == "file:/tmp/ef-mlruns"
    assert tracking_backend() == "file"


def test_status_hides_token(monkeypatch):
    monkeypatch.setenv("DATABRICKS_HOST", "https://adb-demo.cloud.databricks.com")
    monkeypatch.setenv("DATABRICKS_TOKEN", "dapi-secret")
    monkeypatch.setenv("MLFLOW_TRACKING_URI", "databricks")
    st = observability_status()
    blob = str(st)
    assert "dapi-secret" not in blob
    assert st["databricks_configured"] is True
    assert st["backend"] == "databricks"
