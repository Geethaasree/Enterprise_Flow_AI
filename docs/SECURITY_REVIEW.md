# Security / hardening review (Phase 17)

## Done / OK
- JWT HS256; elevated roles only from Bearer or `X-Role`
- Body role clamp (no admin escalation)
- Prompt injection scan on workflow free text
- PII redaction helpers on session paths
- MCP tool RBAC + 403 UNAUTHORIZED
- Non-root containers; secrets via env / gitignored `deploy/prod.env`
- Pytest refused against live Coolify DB
- Startup warns if `EF_JWT_SECRET` default in production

## Residual (portfolio OK; tighten for real prod)
- Demo users hard-coded passwords (`admin`/`admin`) — swap IdP
- `EF_AUTH_REQUIRED=0` default — enable for lock-down
- CORS default `*` — set `CORS_ORIGINS` to UI origin
- MemorySaver checkpointer not shared across replicas
- Hashed embeddings not cryptographic privacy of policy text
- Coolify HTTPS on bare IP is self-signed

## Error handling
- ServiceError / ToolError → structured HTTP codes (409 stock, 403 auth, 400 validation)
- GraphInterrupt re-raised through MLflow spans (HITL safe)

## Performance (honest)
- RAG full-scan cosine over small corpus — fine for demo; IVF/HNSW later
- Single uvicorn worker in image — scale with replicas + shared Redis/DB
