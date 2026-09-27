# Setup guide

## Prerequisites

- Docker + Compose
- Python 3.12+ (local tests)
- Optional: Node 22 (frontend dev)

## Local stack

```bash
cp .env.example .env
# optional: XAI_API_KEY=...  or mount Hermes ~/.hermes/auth.json
docker compose up --build -d
curl -s http://127.0.0.1:8010/health
curl -s http://127.0.0.1:3010/login   # if frontend service up
```

## Tests

```bash
python3 -m venv .venv && source .venv/bin/activate
pip install -e ".[dev]"

# unit (no DB)
pytest -q tests/test_config.py tests/test_health_unit.py

# DB tests — isolated only (never Coolify prod)
./scripts/run-db-tests.sh
```

## Demo users (JWT)

| user | password | role |
|------|----------|------|
| admin | admin | admin |
| demo | demo | sales |
| viewer | viewer | viewer |
| manager | manager | manager |

```bash
curl -s -X POST http://127.0.0.1:8010/auth/token \
  -H 'Content-Type: application/json' \
  -d '{"username":"admin","password":"admin"}'
```

## Seed + policies

Boot entrypoint: alembic → `seed_enterprise` → `rag ingest` → uvicorn.  
Manual: `POST /enterprise/seed`, `POST /rag/ingest`.
