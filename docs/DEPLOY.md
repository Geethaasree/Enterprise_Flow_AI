# Deploy / Coolify (Phase 16)

## Public URL (this VPS)

| Surface | URL |
|---------|-----|
| UI | `http://163.192.122.138/ef` (HTTPS via Coolify Traefik `:443` when certs present) |
| Login | `http://163.192.122.138/ef/login` — `admin` / `admin` |
| API | **not public** — browser uses Next rewrite `/ef/backend/*` → `api:8000` |

Postgres and Redis are internal Docker network only.

## One-shot deploy on this host

```bash
cd /home/ubuntu/enterpriseflow-ai/enterprise-flow-ai
cp deploy/prod.env.example deploy/prod.env   # set POSTGRES_PASSWORD, EF_JWT_SECRET
# optional: XAI_API_KEY=... or mount Hermes auth (default path in compose)

sudo tee /data/coolify/proxy/dynamic/enterpriseflow.yaml \
  < deploy/traefik-enterpriseflow.yaml

sudo docker compose -f docker-compose.coolify.yml --env-file deploy/prod.env up -d --build
```

Verify:

```bash
curl -sf http://127.0.0.1/ef/login -o /dev/null -w '%{http_code}\n'
curl -sf http://127.0.0.1/ef/backend/health
curl -sf --connect-timeout 8 http://163.192.122.138/ef/login -o /dev/null -w '%{http_code}\n'
```

## CI (GitHub Actions)

`deploy/github-ci.yml (copy to .github/workflows/ci.yml when PAT has workflow scope)` on `main` / PRs:

1. Ruff + pytest (Postgres + Redis service containers)
2. Docker build API + frontend (`NEXT_BASE_PATH=/ef`) + MCP

No production secrets in CI. Deploy remains compose-on-VPS (or Coolify UI webhook later).

## Env

See `deploy/prod.env.example`. Never commit `deploy/prod.env`.

| Var | Purpose |
|-----|---------|
| `POSTGRES_PASSWORD` | DB |
| `EF_JWT_SECRET` | JWT signing |
| `XAI_API_KEY` | optional Grok key |
| `HERMES_AUTH_JSON` | host path to Hermes `auth.json` (compose default) |
| `NEXT_BASE_PATH` | baked at frontend **build** (`/ef` for public) |

## Architecture

```
Internet → Coolify Traefik :80/:443
              PathPrefix /ef  →  ef-frontend:3000
                                   │ rewrite /backend/*
                                   ▼
                                ef-api:8000
                                   ├─ ef-db (pgvector)
                                   └─ ef-redis
```

## Rollback

```bash
sudo docker compose -f docker-compose.coolify.yml --env-file deploy/prod.env down
# optional: sudo rm /data/coolify/proxy/dynamic/enterpriseflow.yaml
```
