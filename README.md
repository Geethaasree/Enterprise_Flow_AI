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

## Specs

Source of truth: `./specs/` and `HERMES_GIT_WORKFLOW.md`.

## Secrets

Never commit `.env`. Use `.env.example` placeholders only.
