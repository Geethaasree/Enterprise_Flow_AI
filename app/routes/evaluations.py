"""Evaluation + MLflow inspection API."""

from __future__ import annotations

from fastapi import APIRouter
from fastapi.responses import JSONResponse

from app.eval_runner import run_all_and_log
from app.observability import list_recent_runs, tracking_uri

router = APIRouter(prefix="/evaluations", tags=["evaluations"])


@router.get("/runs")
def evaluation_runs(limit: int = 20):
    runs = list_recent_runs(limit=limit)
    return {
        "status": "ok",
        "tracking_uri": tracking_uri(),
        "count": len(runs),
        "runs": runs,
    }


@router.post("/run")
def run_evaluations():
    summary = run_all_and_log(log_mlflow=True)
    if not summary.get("n"):
        return JSONResponse(
            {"status": "error", "message": summary.get("note") or "No evaluation data available."},
            status_code=404,
        )
    return {"status": "ok", "summary": summary}
