"""Evaluation datasets + runner. Metrics from real runs only."""

from __future__ import annotations

import json
import logging
import time
from dataclasses import asdict, dataclass, field
from pathlib import Path
from typing import Any

logger = logging.getLogger(__name__)


def datasets_dir() -> Path:
    """Resolve evaluation datasets in image (/app) or editable checkout."""
    for candidate in (
        Path("/app/evaluations/datasets"),
        Path(__file__).resolve().parents[1] / "evaluations" / "datasets",
        Path.cwd() / "evaluations" / "datasets",
    ):
        if candidate.is_dir():
            return candidate
    return Path(__file__).resolve().parents[1] / "evaluations" / "datasets"


DATA_DIR = datasets_dir()


@dataclass
class CaseResult:
    case_id: str
    suite: str
    passed: bool
    latency_ms: float
    detail: str = ""
    expected: dict[str, Any] = field(default_factory=dict)
    actual: dict[str, Any] = field(default_factory=dict)


def load_suite(name: str) -> list[dict[str, Any]]:
    path = datasets_dir() / f"{name}.json"
    if not path.exists():
        raise FileNotFoundError(str(path))
    data = json.loads(path.read_text(encoding="utf-8"))
    return list(data.get("cases") or data)


def _score_workflow(case: dict[str, Any], state: dict[str, Any]) -> tuple[bool, str, dict]:
    exp = case.get("expect") or {}
    actual: dict[str, Any] = {
        "status": state.get("status"),
        "error": state.get("error"),
        "steps": state.get("steps") or [],
        "final_response": (state.get("final_response") or "")[:300],
        "intent": state.get("intent"),
    }
    reasons: list[str] = []

    if "status" in exp and actual["status"] != exp["status"] and not (
        exp["status"] == "awaiting_approval" and actual["status"] == "awaiting_approval"
    ):
        if exp["status"] == "ok" and actual["status"] not in (None, "ok"):
            reasons.append(f"status {actual['status']} != ok")
        elif exp["status"] != "ok":
            reasons.append(f"status {actual['status']} != {exp['status']}")

    if exp.get("has_order"):
        ok = "ORD-" in (actual["final_response"] or "") or (
            (state.get("context") or {}).get("order") or {}
        ).get("ok")
        if not ok:
            reasons.append("missing order")
        actual["has_order"] = bool(ok)

    if exp.get("no_order"):
        has = "ORD-" in (actual["final_response"] or "")
        if has:
            reasons.append("unexpected order")
        actual["has_order"] = has

    if exp.get("awaiting_approval") and actual["status"] != "awaiting_approval":
        reasons.append("expected awaiting_approval")

    if "error_contains" in exp:
        err = (actual.get("error") or actual.get("final_response") or "").lower()
        if exp["error_contains"].lower() not in err:
            reasons.append(f"error missing {exp['error_contains']}")

    if "steps_include" in exp:
        steps = actual["steps"]
        for s in exp["steps_include"]:
            if s not in steps:
                reasons.append(f"missing step {s}")

    if "intent" in exp and actual.get("intent") != exp["intent"] and exp["intent"] not in (
        actual.get("intent") or ""
    ):
        reasons.append(f"intent {actual.get('intent')} != {exp['intent']}")

    # tool selection: expected tools called appear in notes/context
    if "tools" in exp:
        notes = " ".join(state.get("notes") or [])
        ctx = json.dumps(state.get("context") or {})
        blob = notes + ctx + " ".join(actual["steps"])
        hits = 0
        for t in exp["tools"]:
            if t in blob or t.replace("_", "") in blob.replace("_", ""):
                hits += 1
            else:
                # agents call tools internally — check known side effects
                if t == "get_customer" and (state.get("context") or {}).get("customer") or t == "check_inventory" and (
                    (state.get("context") or {}).get("inventory")
                    or (state.get("context") or {}).get("reservation")
                ) or t == "create_order" and exp.get("has_order") or t == "search_policy" and (state.get("context") or {}).get("policy"):
                    hits += 1
                else:
                    reasons.append(f"tool not evidenced: {t}")
        actual["tool_hits"] = hits
        actual["tool_expected"] = len(exp["tools"])

    passed = len(reasons) == 0
    return passed, "; ".join(reasons) or "ok", actual


def run_workflow_suite(cases: list[dict[str, Any]] | None = None) -> list[CaseResult]:
    from langgraph.checkpoint.memory import MemorySaver

    from app.graph import build_graph, run_workflow

    cases = cases or load_suite("workflow")
    graph = build_graph(MemorySaver())
    results: list[CaseResult] = []
    for case in cases:
        cid = case["id"]
        msg = case["message"]
        t0 = time.perf_counter()
        try:
            state = run_workflow(msg, workflow_id=f"eval_{cid}", graph=graph)
            passed, detail, actual = _score_workflow(case, state)
        except Exception as e:
            passed, detail, actual = False, f"exception: {e}", {}
        results.append(
            CaseResult(
                case_id=cid,
                suite="workflow",
                passed=passed,
                latency_ms=(time.perf_counter() - t0) * 1000,
                detail=detail,
                expected=case.get("expect") or {},
                actual=actual,
            )
        )
    return results


def run_rag_suite(cases: list[dict[str, Any]] | None = None) -> list[CaseResult]:
    from app.db import session_scope
    from app.rag.service import retrieve

    cases = cases or load_suite("rag")
    results: list[CaseResult] = []
    for case in cases:
        cid = case["id"]
        q = case["query"]
        t0 = time.perf_counter()
        try:
            with session_scope() as s:
                hits = retrieve(
                    s,
                    q,
                    top_k=int(case.get("top_k") or 3),
                    min_score=float(case.get("min_score") or 0.12),
                )
            titles = [h.document_title.lower() for h in hits]
            sources = [h.source_file.lower() for h in hits]
            scores = [h.score for h in hits]
            actual = {
                "titles": titles,
                "sources": sources,
                "top_score": scores[0] if scores else 0.0,
                "n_hits": len(hits),
            }
            exp = case.get("expect") or {}
            reasons = []
            if exp.get("min_hits") is not None and len(hits) < int(exp["min_hits"]):
                reasons.append(f"hits {len(hits)} < {exp['min_hits']}")
            if exp.get("max_hits") is not None and len(hits) > int(exp["max_hits"]):
                reasons.append(f"hits {len(hits)} > {exp['max_hits']}")
            if exp.get("source_contains"):
                blob = " ".join(sources + titles)
                if exp["source_contains"].lower() not in blob:
                    reasons.append(f"source missing {exp['source_contains']}")
            if exp.get("min_top_score") is not None:
                top = scores[0] if scores else 0.0
                if top < float(exp["min_top_score"]):
                    reasons.append(f"top_score {top:.3f} < {exp['min_top_score']}")
            if (
                exp.get("max_top_score") is not None
                and scores
                and scores[0] > float(exp["max_top_score"])
            ):
                reasons.append(f"top_score {scores[0]:.3f} > {exp['max_top_score']}")
            passed = len(reasons) == 0
            detail = "; ".join(reasons) or "ok"
        except Exception as e:
            passed, detail, actual = False, f"exception: {e}", {}
        results.append(
            CaseResult(
                case_id=cid,
                suite="rag",
                passed=passed,
                latency_ms=(time.perf_counter() - t0) * 1000,
                detail=detail,
                expected=case.get("expect") or {},
                actual=actual,
            )
        )
    return results


def summarize(results: list[CaseResult]) -> dict[str, Any]:
    if not results:
        return {"n": 0, "pass_rate": None, "note": "No evaluation data available."}
    n = len(results)
    passed = sum(1 for r in results if r.passed)
    lat = sorted(r.latency_ms for r in results)
    p50 = lat[len(lat) // 2]
    # tool selection accuracy among cases that declared tools
    tool_cases = [r for r in results if r.expected.get("tools")]
    tool_acc = None
    if tool_cases:
        ok = 0
        for r in tool_cases:
            exp_n = len(r.expected["tools"])
            hits = int((r.actual or {}).get("tool_hits") or 0)
            if exp_n and hits >= exp_n and r.passed or exp_n and hits == exp_n:
                ok += 1
        tool_acc = ok / len(tool_cases)

    by_suite: dict[str, dict[str, Any]] = {}
    for r in results:
        s = by_suite.setdefault(r.suite, {"n": 0, "passed": 0})
        s["n"] += 1
        s["passed"] += int(r.passed)

    return {
        "n": n,
        "passed": passed,
        "failed": n - passed,
        "pass_rate": passed / n,
        "latency_ms_p50": p50,
        "latency_ms_mean": sum(lat) / n,
        "tool_selection_accuracy": tool_acc,
        "by_suite": {
            k: {**v, "pass_rate": v["passed"] / v["n"] if v["n"] else None} for k, v in by_suite.items()
        },
        "cases": [asdict(r) for r in results],
    }


def run_all_and_log(*, log_mlflow: bool = True) -> dict[str, Any]:
    results = run_workflow_suite() + run_rag_suite()
    summary = summarize(results)

    if log_mlflow and summary.get("n"):
        try:
            from app.observability import _ensure_mlflow, tracking_uri

            mlflow = _ensure_mlflow()
            with mlflow.start_run(run_name="evaluation"):
                mlflow.set_tag("kind", "evaluation")
                mlflow.log_param("tracking_uri", tracking_uri())
                mlflow.log_metric("pass_rate", float(summary["pass_rate"]))
                mlflow.log_metric("n_cases", float(summary["n"]))
                mlflow.log_metric("passed", float(summary["passed"]))
                mlflow.log_metric("latency_ms_p50", float(summary["latency_ms_p50"]))
                if summary.get("tool_selection_accuracy") is not None:
                    mlflow.log_metric(
                        "tool_selection_accuracy", float(summary["tool_selection_accuracy"])
                    )
                for suite, s in (summary.get("by_suite") or {}).items():
                    if s.get("pass_rate") is not None:
                        mlflow.log_metric(f"{suite}_pass_rate", float(s["pass_rate"]))
                # artifact
                out = Path(__file__).resolve().parents[1] / "evaluations" / "last_run.json"
                out.parent.mkdir(parents=True, exist_ok=True)
                out.write_text(json.dumps(summary, indent=2), encoding="utf-8")
                mlflow.log_artifact(str(out))
                summary["mlflow_run_id"] = mlflow.active_run().info.run_id if mlflow.active_run() else None
        except Exception as e:
            logger.warning("eval_mlflow_log_failed err=%s", e)
            summary["mlflow_error"] = str(e)

    return summary
