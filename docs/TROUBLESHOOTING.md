# Troubleshooting

| Symptom | Likely cause | Fix |
|---------|--------------|-----|
| `no relevant policy found` | empty `policy_*` tables (pytest wiped live DB) | `POST /rag/ingest`; use `./scripts/run-db-tests.sh` only |
| login failed / odd status | browser hit `/backend` without `/ef` | open `http://IP/ef/login`; hard refresh |
| site can't be reached / no server | root `/` or `https://IP/` without path | use `http://IP/ef/login` (root now 307→login) |
| `:3010` / `:8010` timeout from internet | OCI blocks high ports | use Traefik **:80** `/ef` |
| HTTPS “not secure” | self-signed Coolify cert on bare IP | prefer **http://** or add a real domain + LE |
| evaluations 500 FileNotFound | datasets path after site-packages install | fixed via `/app/evaluations/datasets` resolve; rebuild API |
| Grok not configured | no `XAI_API_KEY` / auth.json | set key or mount `deploy/secrets/hermes-auth.json` |
| pytest wiped prod | `DATABASE_URL=@db:5432/enterpriseflow` | blocked by conftest; isolated `:5433` test DB |
| 403 on MCP/approvals | role viewer or body-only admin | use JWT admin or `X-Role: admin` |
| order stuck awaiting_approval | HITL discount path | `POST /approvals/{id}/decide` as manager/admin |

## Health checklist

```bash
curl -s http://127.0.0.1/ef/backend/health
curl -s http://127.0.0.1/ef/backend/health/db
curl -s http://127.0.0.1/ef/backend/health/redis
curl -s http://127.0.0.1/ef/backend/health/observability
sudo docker ps --filter name=ef-
```
