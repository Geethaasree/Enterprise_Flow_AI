"""MLflow-backed workflow tracing.

# ponytail: file store only; remote tracking URI when ops wants a server.
"""

from __future__ import annotations

import logging
import os
import time
from collections.abc import Iterator
from contextlib import contextmanager
from contextvars import ContextVar
from pathlib import Path
from typing import Any

logger = logging.getLogger(__name__)

try:
    from langgraph.errors import GraphBubbleUp, GraphInterrupt

    _INTERRUPT_TYPES: tuple = (GraphInterrupt, GraphBubbleUp)
except Exception:
    _INTERRUPT_TYPES = ()

_run_id: ContextVar[str | None] = ContextVar("ef_mlflow_run", default=None)
_token_totals: ContextVar[dict[str, int] | None] = ContextVar("ef_token_totals", default=None)

_DEFAULT_URI = str(Path(__file__).resolve().parents[2] / "mlruns")


def tracking_uri() -> str:
    from app.databricks_path import apply_databricks_env

    apply_databricks_env()
    return os.environ.get("MLFLOW_TRACKING_URI") or f"file:{_DEFAULT_URI}"


def _ensure_mlflow():
    import mlflow

    mlflow.set_tracking_uri(tracking_uri())
    exp = os.environ.get("MLFLOW_EXPERIMENT", "enterpriseflow")
    mlflow.set_experiment(exp)
    return mlflow


@contextmanager
def workflow_run(
    *,
    name: str,
    request_id: str,
    workflow_id: str,
    session_id: str | None = None,
    tags: dict[str, str] | None = None,
) -> Iterator[str | None]:
    """Root MLflow run for one workflow. Yields run_id (or None if disabled)."""
    if os.environ.get("EF_MLFLOW", "1") in {"0", "false", "no"}:
        yield None
        return

    mlflow = _ensure_mlflow()
    token_bag = {"prompt_tokens": 0, "completion_tokens": 0, "total_tokens": 0}
    tok_tokens = _token_totals.set(token_bag)
    t0 = time.perf_counter()
    rid_tok = None
    try:
        with mlflow.start_run(run_name=name) as run:
            run_id = run.info.run_id
            rid_tok = _run_id.set(run_id)
            mlflow.set_tags(
                {
                    "request_id": request_id,
                    "workflow_id": workflow_id,
                    **({"session_id": session_id} if session_id else {}),
                    **(tags or {}),
                }
            )
            mlflow.log_param("workflow_id", workflow_id)
            mlflow.log_param("request_id", request_id)
            try:
                yield run_id
            finally:
                try:
                    elapsed_ms = (time.perf_counter() - t0) * 1000
                    mlflow.log_metric("latency_ms", elapsed_ms)
                    bag = _token_totals.get() or token_bag
                    mlflow.log_metric("prompt_tokens", bag.get("prompt_tokens", 0))
                    mlflow.log_metric("completion_tokens", bag.get("completion_tokens", 0))
                    mlflow.log_metric("total_tokens", bag.get("total_tokens", 0))
                except Exception as e:
                    logger.warning("mlflow_workflow_metrics_failed err=%s", e)
                if rid_tok is not None:
                    _run_id.reset(rid_tok)
    except _INTERRUPT_TYPES:
        raise
    except Exception as e:
        logger.warning("mlflow_workflow_run_failed err=%s", e)
        yield None
    finally:
        _token_totals.reset(tok_tokens)


@contextmanager
def span(name: str, *, kind: str = "span", attrs: dict[str, Any] | None = None) -> Iterator[None]:
    """Nested run span under active workflow run."""
    parent = _run_id.get()
    if not parent or os.environ.get("EF_MLFLOW", "1") in {"0", "false", "no"}:
        yield
        return
    mlflow = _ensure_mlflow()
    t0 = time.perf_counter()
    try:
        with mlflow.start_run(run_name=f"{kind}:{name}", nested=True):
            mlflow.set_tag("span.kind", kind)
            mlflow.set_tag("span.name", name)
            if attrs:
                for k, v in list(attrs.items())[:20]:
                    try:
                        mlflow.log_param(k[:250], str(v)[:250])
                    except Exception:
                        pass
            try:
                yield
            finally:
                try:
                    mlflow.log_metric("latency_ms", (time.perf_counter() - t0) * 1000)
                except Exception:
                    pass
    except _INTERRUPT_TYPES:
        raise
    except Exception as e:
        logger.warning("mlflow_span_failed name=%s err=%s", name, e)
        yield


def log_outcome(status: str, *, error: str | None = None, extra: dict[str, Any] | None = None) -> None:
    if not _run_id.get():
        return
    try:
        mlflow = _ensure_mlflow()
        mlflow.set_tag("outcome", status)
        mlflow.log_param("outcome_status", status)
        if error:
            mlflow.set_tag("error", error[:250])
        if extra:
            for k, v in extra.items():
                mlflow.log_param(f"out_{k}"[:250], str(v)[:250])
    except Exception as e:
        logger.warning("mlflow_log_outcome_failed err=%s", e)


def record_tokens(prompt: int = 0, completion: int = 0, total: int | None = None) -> None:
    bag = _token_totals.get()
    if bag is None:
        return
    bag["prompt_tokens"] = bag.get("prompt_tokens", 0) + int(prompt or 0)
    bag["completion_tokens"] = bag.get("completion_tokens", 0) + int(completion or 0)
    bag["total_tokens"] = bag.get("total_tokens", 0) + int(
        total if total is not None else (prompt or 0) + (completion or 0)
    )


def list_recent_runs(limit: int = 20) -> list[dict[str, Any]]:
    try:
        _ensure_mlflow()
        from mlflow.tracking import MlflowClient

        client = MlflowClient()
        exp = client.get_experiment_by_name(os.environ.get("MLFLOW_EXPERIMENT", "enterpriseflow"))
        if not exp:
            return []
        runs = client.search_runs(
            experiment_ids=[exp.experiment_id],
            order_by=["attributes.start_time DESC"],
            max_results=limit,
        )
        out = []
        for r in runs:
            out.append(
                {
                    "run_id": r.info.run_id,
                    "name": r.info.run_name,
                    "status": r.info.status,
                    "start_time": r.info.start_time,
                    "end_time": r.info.end_time,
                    "tags": dict(r.data.tags or {}),
                    "metrics": dict(r.data.metrics or {}),
                    "params": dict(r.data.params or {}),
                }
            )
        return out
    except Exception as e:
        logger.warning("mlflow_list_runs_failed err=%s", e)
        return []
