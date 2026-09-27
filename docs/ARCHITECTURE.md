# Architecture

```text
Browser ──► Coolify Traefik :80/:443
              PathPrefix /ef ──► ef-frontend (Next.js basePath=/ef)
                                    rewrite /backend/* ──► ef-api :8000
                                                           │
                    ┌──────────────────────────────────────┤
                    │ Auth JWT / X-Role / RBAC             │
                    │ LangGraph supervisor + specialists   │
                    │ MCP tools ──► enterprise services    │
                    │ RAG (pgvector) + Redis memory        │
                    │ MLflow file spans + eval runner      │
                    │ Experience/Process/System/SAP sim    │
                    └──────────┬───────────────┬───────────┘
                               ▼               ▼
                         ef-db (pgvector)  ef-redis
```

## Trust boundaries

| Layer | Owns |
|-------|------|
| FastAPI + security | authn/z, injection scan, PII redact |
| LangGraph agents | orchestration only |
| MCP tools | permissioned tool bus |
| Services | money, stock, credit (never LLM) |
| RAG | grounded policy citations |
| Redis | session, biz memory, locks, rate limits |

## Public surface (this VPS)

- UI: `http://<ip>/ef/login`
- API: internal only via Next `/ef/backend/*`
- Postgres/Redis: not published
