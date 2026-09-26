# Databricks integration path (Phase 14)

Local Compose remains the default. Databricks is an **optional** enterprise
tracking / lakehouse path. No Databricks account is required to run this repo.

## Architecture (target)

```
Browser (Next.js :3010)
        │
        ▼
FastAPI API  ── MCP tools ── Postgres / Redis
        │
        ├── Grok (xAI) LLM
        ├── LangGraph workflows + human approval
        ├── pgvector RAG
        └── MLflow client
                │
     ┌──────────┴──────────┐
     ▼                     ▼
file:./mlruns          Databricks MLflow
(local default)        (workspace experiment)
                           │
                           ▼
                    Unity Catalog / Delta
                    (orders, eval artifacts)
```

Same application code. Backend is selected by env:

| Mode | When | `MLFLOW_TRACKING_URI` |
|------|------|------------------------|
| Local file | default | unset or `file:./mlruns` |
| Databricks workspace | `DATABRICKS_HOST` + `DATABRICKS_TOKEN` | auto `databricks` if unset |
| Self-hosted MLflow | ops provides server | `https://mlflow.example.com` |

## Env (secrets via CLI / Coolify — never commit)

```bash
# Workspace
DATABRICKS_HOST=https://<workspace>.cloud.databricks.com
DATABRICKS_TOKEN=dapi...
# Optional SQL warehouse for future Delta reads
DATABRICKS_HTTP_PATH=/sql/1.0/warehouses/<id>
DATABRICKS_MLFLOW_EXPERIMENT=/Users/<you>/enterpriseflow
# Or set explicitly:
# MLFLOW_TRACKING_URI=databricks
# MLFLOW_EXPERIMENT=enterpriseflow
```

Python adapter: `app/databricks_path.py` (called from MLflow setup).  
Status (no secrets): `GET /health/observability`.

## MLflow integration path

Already instrumented in `app/observability.py`:

- Root run per workflow (`workflow_run`)
- Nested spans: agent / tool / rag / llm
- Eval suite metrics via `POST /evaluations/run` → `app/eval_runner.py`

On Databricks, those runs land in the workspace MLflow UI under the experiment
name. Tags already include `request_id`, `workflow_id`, `session_id`, outcome.

Install (already in project deps when using mlflow):

```bash
pip install mlflow databricks-sdk  # sdk only if you add jobs/SQL later
```

Verify without UI:

```bash
export DATABRICKS_HOST=... DATABRICKS_TOKEN=...
export MLFLOW_TRACKING_URI=databricks
curl -s localhost:8010/health/observability
# {"backend":"databricks","databricks_configured":true,...}
curl -s -X POST localhost:8010/evaluations/run -H 'Content-Type: application/json' -d '{}'
```

## Evaluation workflow (same API, remote store)

1. Seed policies / enterprise data (local or CI).
2. `POST /evaluations/run` — runs `evaluations/datasets/*.json`.
3. Metrics: `pass_rate`, `latency_ms_p50`, per-suite rates; artifact JSON logged.
4. Interview UI **Evaluations** page triggers the same endpoint.
5. On Databricks: open **Experiments → enterpriseflow** and compare runs.

## Deployment sketch (Databricks Jobs — optional)

Not required for the portfolio demo. Credible path:

1. Build API image (Phase 15 production Dockerfile).
2. Push to registry reachable by Databricks.
3. Databricks Job → task type **Docker** or **Notebook** that:
   - sets `DATABASE_URL` / `REDIS_URL` to managed endpoints (or VPC peer)
   - sets Databricks MLflow env as above
   - runs `uvicorn app.main:app` **or** batch `python -m app.eval_runner`
4. Model Serving is **out of scope** — Grok stays external via xAI; Databricks
   holds traces + evals + future feature tables, not the chat model.

## What stays local-only by design

- Postgres + Redis Compose (or managed cloud DB later)
- Next.js frontend
- Grok credentials (xAI / Hermes OAuth)
- Human approval queue

## Acceptance

- [x] Documented architecture + env matrix
- [x] MLflow path works with file store without Databricks
- [x] Optional adapter flips tracking URI when Databricks env is set
- [x] Eval workflow unchanged (`/evaluations/run`)
- [x] No hard dependency on Databricks packages at import time
