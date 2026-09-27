# API documentation

Interactive OpenAPI: `GET /docs` and `GET /openapi.json` on the API  
(public: `http://<ip>/ef/backend/docs` if exposed via rewrite).

## Core groups

| Group | Prefix | Notes |
|-------|--------|-------|
| Health | `/health*` | liveness, db, redis, observability |
| Auth | `/auth/token` | demo JWT |
| LLM | `/llm/*` | Grok status/chat |
| Workflows | `/workflows/*` | LangGraph run/resume/session |
| Enterprise | `/enterprise/*` | seed, customer, inventory, orders |
| MCP | `/mcp/*` | tool list + call (RBAC) |
| RAG | `/rag/*` | ingest + search |
| Approvals | `/approvals/*` | HITL decide |
| Integration | `/sap` `/system` `/process` `/experience` | labeled simulators |
| Eval | `/evaluations/*` | measured suites + MLflow |

## Auth headers

1. `Authorization: Bearer <jwt>` (preferred)
2. else `X-Role: sales|admin|…`
3. body `role` **cannot** escalate to admin/manager/finance

## Idempotency

MCP mutations accept `idempotency_key` (Redis + process fallback).
