# Interview talking points

## One-liner
EnterpriseFlow is a **portfolio** multi-agent order platform: natural language → FastAPI → RBAC → LangGraph specialists → MCP tools → deterministic services → Postgres/Redis, with RAG policies, HITL approvals, and MLflow eval — not a mock chat UI.

## Architecture soundbites
- **LLM never owns money or stock** — pricing/inventory/credit live in services; agents only call MCP.
- **Supervisor is deterministic** (keywords) so demos are stable; Grok is optional for chat polish.
- **HITL** uses LangGraph `interrupt` + same checkpointer for pause/resume; thresholds in one module.
- **RAG** = pgvector chunks + hashed embeddings (swap real model when needed); citations always returned.
- **API-led** layers are **labeled simulators** (Experience→Process→System→SAP field map), not fake MuleSoft claims.

## Security
- JWT HS256; body role **cannot** escalate.
- Prompt-injection deny-list on workflow free text.
- PII redact on session/response paths.
- Tests blocked from Coolify prod DB (`conftest` + `run-db-tests.sh`).

## Tradeoffs to say out loud
- In-process MemorySaver checkpointer → multi-replica resume needs shared store.
- Hashed embeddings OK for small distinct policies; production would use a real embedding model.
- Demo users/passwords are interview conveniences — lock with `EF_AUTH_REQUIRED` + real IdP later.
- Bare-IP HTTPS is self-signed; path `/ef` on Traefik is the shareable URL.

## Metrics you can show
- `POST /evaluations/run` → real `pass_rate` / latency (not hard-coded).
- MLflow file store nested spans: workflow / agent / tool / rag / llm.
