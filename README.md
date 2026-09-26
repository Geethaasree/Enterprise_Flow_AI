# EnterpriseFlow AI

Production-style enterprise agentic order platform (portfolio).

## Phase 1 — Foundation

Runnable backend skeleton:

- FastAPI API
- PostgreSQL + Redis via Docker Compose
- Health endpoints
- Structured JSON logging
- Config via environment / `.env`
- Pytest

## Quick start

```bash
cp .env.example .env
docker compose up --build -d
curl -s http://localhost:8010/health
curl -s http://localhost:8010/health/db
curl -s http://localhost:8010/health/redis
```

## Local tests (without full stack)

```bash
python3 -m venv .venv
source .venv/bin/activate
pip install -e ".[dev]"
# unit/config tests only:
pytest -q tests/test_config.py tests/test_health_unit.py
```

With Compose running, integration tests:

```bash
DATABASE_URL=postgresql+psycopg://enterpriseflow:enterpriseflow@localhost:5432/enterpriseflow \
REDIS_URL=redis://localhost:6379/0 \
pytest -q
```

## Health endpoints

| Method | Path | Purpose |
|--------|------|---------|
| GET | `/health` | Process liveness |
| GET | `/health/db` | PostgreSQL connectivity |
| GET | `/health/redis` | Redis connectivity |
| GET | `/llm/status` | Grok credential status (no secret values) |
| POST | `/llm/chat` | Smoke chat against Grok |
| POST | `/workflows/run` | Run LangGraph workflow (Phase 3) |
| GET | `/workflows/{id}` | Read checkpointed workflow state |
| POST | `/enterprise/seed` | Seed ACME + demo products |
| GET | `/enterprise/customers/{code}` | Customer + contract |
| GET | `/enterprise/inventory/{sku}` | Stock levels |
| POST | `/enterprise/inventory/reserve` | Reserve stock |
| GET | `/enterprise/pricing/quote` | Deterministic price quote |
| POST | `/enterprise/orders` | Create draft/reserved order |
| GET | `/mcp/tools` | List MCP tools |
| POST | `/mcp/call` | Invoke MCP tool (X-Role header) |
| POST | `/rag/ingest` | Ingest policy documents |
| POST | `/rag/search` | Policy similarity search + citations |
| GET | `/workflows/session/{id}` | Session turns + summary |
| GET | `/workflows/memory/business/{code}` | Long-term customer memory |
| GET | `/approvals` | List pending approvals |
| POST | `/approvals/{id}/decide` | Approve/reject + resume graph |
| GET/POST | `/sap/*` | SAP-style simulator (KUNNR/MATNR/…) |
| GET/POST | `/system/*` | System API (canonical DTOs over SAP) |
| POST | `/process/orders` | Process API orchestration |
| POST | `/experience/orders` | Experience API channel DTO |
| POST | `/evaluations/run` | Run eval suites + log MLflow metrics |
| GET | `/evaluations/runs` | Recent MLflow runs (file store) |
| POST | `/auth/token` | Issue JWT (demo users) |

## Phase 12 — Security

JWT (HS256) + RBAC. Elevated roles require `Authorization: Bearer` or `X-Role` header — never body alone. Prompt injection blocked on `/workflows/run`. PII redacted in session/response text.

## Phase 11 — MLflow

File tracking URI (`MLFLOW_TRACKING_URI`, default `./mlruns`). Workflow/agent/tool/RAG/LLM spans are nested runs. Evaluation datasets live under `evaluations/datasets/`.

## Phase 4 — Database

SQLAlchemy models + Alembic + seed (ACME, Laptop Pro 14). Migrations run on API boot.

Supervisor routes to order / inventory / general stubs. Checkpointing uses
in-memory `MemorySaver` (process-local). Real specialists arrive in Phase 7.

```bash
curl -s http://localhost:8010/workflows/run \
  -H 'Content-Type: application/json' \
  -d '{"message":"Create an order for 100 laptops for ACME."}'
```

Set `XAI_API_KEY` in `.env`, **or** leave empty to reuse Hermes SuperGrok OAuth
from `~/.hermes/auth.json` (same subscription as this VPS Hermes session).

Live LLM tests:

```bash
EF_LIVE_LLM=1 pytest -q tests/test_llm_live.py
```

Source of truth: `./specs/` and `HERMES_GIT_WORKFLOW.md`.

## Secrets

Never commit `.env`. Use `.env.example` placeholders only.
