# EnterpriseFlow AI — Execution Rules

These rules are mandatory for implementation.

This document controls how the project must be built.

---

# 1. General Rule

Implement the project incrementally.

Do not attempt to build all 17 phases simultaneously.

Only implement the phase explicitly requested.

A later phase must not be silently implemented early unless a small supporting change is strictly necessary.

---

# 2. Source of Truth

The files inside `/specs` are the primary project specification.

Before implementing a phase:

1. Read all files in `/specs`.
2. Identify the current phase.
3. Identify dependencies.
4. Implement only the requested scope.
5. Run relevant tests.
6. Report what was actually implemented.

Do not claim functionality that has not been implemented and tested.

---

# 3. No Fake Functionality

Never create fake implementations merely to make the application appear complete.

Do not:

* hard-code agent responses
* hard-code successful order creation
* fake MLflow traces
* fake evaluation scores
* fake inventory
* fake approval results
* fake RAG citations
* fake tool calls
* fabricate API responses

Deterministic seed data is allowed.

Mock enterprise systems are allowed.

Simulators must be clearly identified as simulators.

---

# 4. No Fabricated Metrics

Never invent:

* accuracy
* latency
* evaluation score
* retrieval score
* token usage
* cost
* success rate

Metrics must come from actual executions.

If no metric exists yet, display:

```text
No evaluation data available.
```

rather than inventing a value.

---

# 5. Secrets

Never commit:

* API keys
* passwords
* tokens
* private certificates
* production credentials
* database credentials

Use environment variables.

Provide `.env.example`.

Example:

```text
XAI_API_KEY=
XAI_MODEL=
DATABASE_URL=
REDIS_URL=
MLFLOW_TRACKING_URI=
JWT_SECRET=
```

Never ask the user to paste a secret into source code.

---

# 6. LLM Security Boundary

The LLM must never have:

* unrestricted database access
* unrestricted shell access
* unrestricted filesystem access
* unrestricted network access
* unrestricted HTTP access
* direct credential access

LLM actions must go through controlled tools/services.

---

# 7. Deterministic Business Logic

The following must not depend solely on LLM reasoning:

* price calculation
* discount calculation
* inventory count
* authorization
* approval threshold
* order persistence
* financial totals
* credit checks
* permission checks

Use deterministic Python services.

---

# 8. Authorization

Authorization must occur before privileged tool execution.

Do not rely on the LLM to decide whether a user is authorized.

Example:

```text
User
 ↓
LLM
 ↓
Requested tool
 ↓
Authorization middleware
 ↓
Permission check
 ↓
Tool execution
```

---

# 9. Validation

Validate all external input using typed schemas.

Use Pydantic or equivalent.

Validate:

* API requests
* tool inputs
* agent outputs
* database writes
* configuration
* approval actions

Reject malformed data early.

---

# 10. Idempotency

Mutating enterprise operations must support idempotency where appropriate.

Especially:

```text
create_order
reserve_inventory
create_shipment
cancel_order
```

Repeated requests must not accidentally create duplicate orders or duplicate reservations.

---

# 11. Transactions

Business-critical database operations must use transactions.

Examples:

```text
reserve inventory
create order
create order items
record audit event
```

Where appropriate, these operations should succeed or fail atomically.

---

# 12. Inventory Concurrency

Inventory is concurrency-sensitive.

Do not assume:

```text
check_inventory
reserve_inventory
```

is automatically safe.

Use appropriate transaction isolation, locking, or atomic database operations.

Avoid aggressive inventory caching.

---

# 13. Agent Architecture

Do not create one giant "super agent".

Use:

```text
Supervisor
 ├── Customer
 ├── Inventory
 ├── Pricing
 └── Policy/RAG
```

Specialists must have clear responsibilities.

---

# 14. LangGraph

Use LangGraph for:

* state
* routing
* branching
* approval pauses
* workflow continuation
* graph execution

Do not replace LangGraph with manually chained LLM calls.

---

# 15. MCP

MCP should provide a controlled tool interface.

Each tool requires:

* schema
* validation
* authorization
* implementation
* error handling
* logging

Do not create tools that expose arbitrary SQL.

Never create:

```text
execute_sql(query)
```

as an agent tool.

---

# 16. RAG

RAG must use actual documents.

Every retrieved document chunk must preserve metadata.

The system should distinguish:

```text
retrieved source
```

from:

```text
LLM-generated explanation
```

Do not claim that the LLM "knows" company policy if the answer is supposed to come from RAG.

---

# 17. Prompt Injection

Retrieved documents and user messages must be treated as untrusted content.

Do not allow retrieved text to override:

* system instructions
* authorization
* business rules
* tool permissions
* approval requirements

Implement explicit trust boundaries.

---

# 18. Memory

Memory must be selective.

Do not send all historical messages to every model call.

Use:

* recent messages
* summaries
* relevant business memory
* relevant retrieved documents

Only include information required for the current task.

---

# 19. Redis

Redis must not become the only source of truth for business data.

Persistent business records belong in PostgreSQL.

Redis may store:

* cache
* session state
* locks
* temporary workflow state
* rate-limit counters

---

# 20. Provider Abstraction

Do not hard-code Grok calls into every agent.

Use a provider abstraction.

Agents should depend on an LLM interface.

This allows future support for another provider.

---

# 21. Error Handling

Errors must be structured.

Do not expose stack traces to end users.

Use appropriate categories such as:

```text
ValidationError
AuthenticationError
AuthorizationError
NotFoundError
ConflictError
ExternalServiceError
LLMProviderError
ToolExecutionError
ApprovalRequired
```

Return safe user-facing messages.

Log technical details internally.

---

# 22. Retries

Retries must be bounded.

Do not retry indefinitely.

Use exponential backoff where appropriate.

Do not automatically retry non-idempotent operations unless idempotency is guaranteed.

---

# 23. Timeouts

External calls must have explicit timeouts.

This includes:

* Grok
* MCP
* external enterprise APIs
* database operations
* Redis operations

---

# 24. Logging

Use structured logging.

Every major workflow should contain:

```text
request_id
session_id
component
operation
status
duration
```

Do not log secrets.

Do not unnecessarily log sensitive personal data.

---

# 25. Testing

Every phase must add appropriate tests.

Minimum categories:

```text
unit tests
integration tests
API tests
agent tests
security tests
```

Later phases should also include:

```text
RAG evaluation
workflow evaluation
end-to-end tests
```

---

# 26. Test Before Claiming Completion

A phase is not complete merely because files exist.

Before reporting completion:

1. Run tests.
2. Run lint.
3. Run type checks where configured.
4. Run relevant services.
5. Verify critical workflow paths.
6. Fix failures.
7. Report remaining known issues.

---

# 27. Documentation

Update documentation when behavior changes.

At minimum maintain:

```text
README.md
architecture documentation
environment configuration documentation
local setup instructions
deployment instructions
API documentation
```

Do not document functionality that does not exist.

---

# 28. Docker

Every service must have reproducible startup.

Avoid "works only on my machine" dependencies.

Use:

* Dockerfiles
* Compose
* health checks
* environment configuration

---

# 29. Local Development

A new developer should be able to approximately run:

```bash
git clone <repo>
cd enterprise-flow-ai

cp .env.example .env

docker compose up --build
```

and reach the application.

Document any additional setup.

---

# 30. Database Migrations

Use Alembic or equivalent.

Never depend on manually modifying a production database.

Schema changes must be represented by migrations.

---

# 31. Seed Data

Seed data must be:

* deterministic
* documented
* safe to rerun
* suitable for tests

Do not depend on external production data.

---

# 32. External Enterprise Integrations

Initially use simulators.

Examples:

```text
MuleSoft-style API simulator
SAP-style API simulator
CRM simulator
ERP simulator
```

Do not falsely represent these as actual enterprise systems.

Keep adapters replaceable.

---

# 33. Databricks

Databricks integration must not prevent local execution.

Use configuration/adapter boundaries.

Local mode should work without Databricks credentials.

---

# 34. MLflow

MLflow must not be required for basic local functionality if it is unavailable.

The application should degrade gracefully where appropriate.

Do not silently discard critical production observability.

---

# 35. Frontend

The frontend must consume actual backend APIs.

Do not create static demo data solely for visual appearance.

Demo seed data is acceptable when it comes from the backend.

---

# 36. UI

The interface should make agentic behavior inspectable.

Where appropriate show:

* agent
* action
* tool
* status
* source
* approval
* result

Avoid exposing internal secrets or sensitive system information.

---

# 37. Dependency Discipline

Do not add technology merely because it is popular.

Before introducing a new dependency, ask:

1. Is it required?
2. Does it materially simplify the architecture?
3. Is it already provided by the existing stack?
4. Does it increase operational complexity?

Avoid unnecessary additions such as Kubernetes, Kafka, multiple vector databases, or multiple agent frameworks.

---

# 38. Phase Isolation

Do not implement future phases prematurely.

For example:

During Phase 1, do not build:

* Grok integration
* LangGraph agents
* MCP
* RAG
* MLflow
* frontend
* Databricks

unless a tiny placeholder is strictly required by the phase.

---

# 39. Git Discipline

After each completed phase:

```bash
git status
git add .
git commit
```

Recommended tags:

```text
phase-01-foundation
phase-02-grok
phase-03-langgraph
phase-04-database
phase-05-mcp
phase-06-rag
phase-07-agents
phase-08-memory
phase-09-approval
phase-10-integrations
phase-11-mlflow
phase-12-security
phase-13-frontend
phase-14-databricks
phase-15-production-docker
phase-16-coolify
phase-17-hardening
```

Do not commit broken phases.

---

# 40. Reporting Rule

After each phase, report:

```text
Implemented:
- ...

Tests:
- ...

Verified:
- ...

Files added/changed:
- ...

Known limitations:
- ...

Not implemented yet:
- ...
```

Never say "fully production ready" unless the acceptance criteria actually support that claim.

---

# 41. Stop Condition

If a requirement is ambiguous and implementing it could materially affect architecture, stop and ask for clarification.

If the requirement is minor and the intended behavior is obvious from the specifications, make the smallest reasonable assumption and document it.

Do not silently invent major architecture.

---

# 42. Final Principle

The objective is not to produce the largest codebase.

The objective is to produce a:

* working
* testable
* secure
* observable
* explainable
* enterprise-oriented
* genuinely agentic

application that can survive technical inspection by an interviewer.
