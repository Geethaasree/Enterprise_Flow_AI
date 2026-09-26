"""Optional Databricks / remote MLflow path.

# ponytail: env-only switch; no SDK required for local file store.
Local default stays file:./mlruns. Set DATABRICKS_HOST + DATABRICKS_TOKEN
(and optional DATABRICKS_HTTP_PATH for SQL warehouse) to point MLflow at
Databricks workspace tracking without code changes.
"""

from __future__ import annotations

import logging
import os
from typing import Any

logger = logging.getLogger(__name__)

_APPLIED = False


def tracking_backend() -> str:
    """Return logical backend: file | databricks | http | other."""
    uri = (os.environ.get("MLFLOW_TRACKING_URI") or "").strip().lower()
    if not uri or uri.startswith("file:"):
        return "file"
    if uri in {"databricks", "databricks-uc"} or uri.startswith("databricks"):
        return "databricks"
    if uri.startswith(("http://", "https://")):
        return "http"
    return "other"


def databricks_configured() -> bool:
    host = (os.environ.get("DATABRICKS_HOST") or "").strip()
    token = (os.environ.get("DATABRICKS_TOKEN") or "").strip()
    return bool(host and token)


def apply_databricks_env() -> dict[str, Any]:
    """If Databricks creds present, default MLFLOW_TRACKING_URI to databricks.

    Never overrides an explicit non-empty MLFLOW_TRACKING_URI.
    Safe no-op when creds missing — local file store continues to work.
    """
    global _APPLIED
    info: dict[str, Any] = {
        "databricks_configured": databricks_configured(),
        "backend": tracking_backend(),
        "applied": False,
    }
    if not databricks_configured():
        return info

    # Normalize host (workspace URL, no trailing slash)
    host = os.environ["DATABRICKS_HOST"].strip().rstrip("/")
    if not host.startswith("http"):
        host = f"https://{host}"
        os.environ["DATABRICKS_HOST"] = host

    if not (os.environ.get("MLFLOW_TRACKING_URI") or "").strip():
        os.environ["MLFLOW_TRACKING_URI"] = "databricks"
        info["applied"] = True
        logger.info("mlflow_tracking_uri_set backend=databricks host=%s", host)

    # Optional: Unity Catalog experiment naming
    if not os.environ.get("MLFLOW_EXPERIMENT"):
        os.environ["MLFLOW_EXPERIMENT"] = os.environ.get(
            "DATABRICKS_MLFLOW_EXPERIMENT", "enterpriseflow"
        )

    info["backend"] = tracking_backend()
    _APPLIED = True
    return info


def observability_status() -> dict[str, Any]:
    """Public status blob — no secrets."""
    apply_databricks_env()
    host = (os.environ.get("DATABRICKS_HOST") or "").strip()
    # mask host path only
    host_public = host.split("?")[0] if host else None
    return {
        "backend": tracking_backend(),
        "mlflow_experiment": os.environ.get("MLFLOW_EXPERIMENT", "enterpriseflow"),
        "ef_mlflow": os.environ.get("EF_MLFLOW", "1"),
        "databricks_configured": databricks_configured(),
        "databricks_host": host_public,
        "sql_warehouse_path_set": bool(os.environ.get("DATABRICKS_HTTP_PATH")),
        "tracking_uri_scheme": tracking_backend(),
    }
