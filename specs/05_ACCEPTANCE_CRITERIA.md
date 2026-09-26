# EnterpriseFlow AI — Acceptance Criteria

This document defines what must be true for the project to be considered complete.

Do not mark an item complete unless it has actually been implemented and verified.

---

# 1. Foundation

* [ ] Python backend starts successfully.
* [ ] FastAPI starts successfully.
* [ ] PostgreSQL starts successfully.
* [ ] Redis starts successfully.
* [ ] Docker Compose starts successfully.
* [ ] Environment configuration works.
* [ ] `.env.example` exists.
* [ ] API health endpoint works.
* [ ] Database health endpoint works.
* [ ] Redis health endpoint works.
* [ ] Structured logging exists.
* [ ] Tests execute successfully.

---

# 2. Grok Integration

* [ ] xAI/Grok provider exists.
* [ ] Provider is abstracted from agents.
* [ ] API key comes from environment.
* [ ] No API key is committed.
* [ ] Normal generation works.
* [ ] Structured generation works.
* [ ] Tool/function calling support exists.
* [ ] Timeout exists.
* [ ] Retry behavior exists.
* [ ] Provider errors are handled.
* [ ] Token usage is tracked where available.

---

# 3. LangGraph

* [ ] LangGraph is used for workflow orchestration.
* [ ] Graph state exists.
* [ ] Supervisor exists.
* [ ] Routing exists.
* [ ] Workflow IDs exist.
* [ ] Checkpointing exists.
* [ ] Graph can execute a complete workflow.
* [ ] Graph can pause for approval.
* [ ] Graph can resume after approval.

---

# 4. Database

* [ ] PostgreSQL is used.
* [ ] SQLAlchemy or equivalent ORM exists.
* [ ] Alembic migrations exist.
* [ ] Customer entity exists.
* [ ] Customer contract entity exists.
* [ ] Product entity exists.
* [ ] Inventory entity exists.
* [ ] Pricing entity exists.
* [ ] Order entity exists.
* [ ] Order item entity exists.
* [ ] Approval entity exists.
* [ ] Audit entity exists.
* [ ] User/role/permission entities exist.
* [ ] Conversation entities exist.
* [ ] Workflow execution entity exists.
* [ ] Seed data exists.
* [ ] Seed data is deterministic.

---

# 5. MCP

* [ ] MCP server exists.
* [ ] Tools are typed.
* [ ] Tools validate input.
* [ ] Tools enforce authorization.
* [ ] Tools return structured results.
* [ ] Tool errors are structured.
* [ ] Tool calls are logged.
* [ ] Tool calls have request/trace IDs.
* [ ] Customer tools work.
* [ ] Inventory tools work.
* [ ] Pricing tools work.
* [ ] Order tools work.
* [ ] Shipping tools work.
* [ ] Policy tool works.
* [ ] Mutating tools support idempotency where required.
* [ ] No arbitrary SQL tool exists.

---

# 6. RAG

* [ ] pgvector is installed/configured.
* [ ] Knowledge documents exist.
* [ ] Document ingestion exists.
* [ ] Text extraction exists.
* [ ] Chunking exists.
* [ ] Metadata exists.
* [ ] Embeddings are stored.
* [ ] Similarity search works.
* [ ] Relevant policy chunks are returned.
* [ ] Citations are returned.
* [ ] Document versions are preserved.
* [ ] Effective dates can be represented.
* [ ] Retrieved text is treated as untrusted content.
* [ ] RAG tests exist.

---

# 7. Specialist Agents

* [ ] Supervisor Agent exists.
* [ ] Customer Agent exists.
* [ ] Inventory Agent exists.
* [ ] Pricing Agent exists.
* [ ] Policy/RAG Agent exists.
* [ ] Agents have defined responsibilities.
* [ ] Agents use structured outputs where appropriate.
* [ ] Agents use MCP tools.
* [ ] Agents do not directly access the database.
* [ ] Agent routing works.
* [ ] Multi-agent order workflow works.

---

# 8. Customer Workflow

* [ ] Customer can be identified.
* [ ] Customer profile can be retrieved.
* [ ] Customer contract can be retrieved.
* [ ] Credit status can be checked.
* [ ] Shipping address can be retrieved.
* [ ] Unauthorized customer access is rejected.

---

# 9. Inventory Workflow

* [ ] Product search works.
* [ ] Product lookup works.
* [ ] Inventory check works.
* [ ] Insufficient inventory is detected.
* [ ] Inventory reservation works.
* [ ] Inventory release works.
* [ ] Concurrent reservation is safe.
* [ ] Duplicate reservation behavior is controlled.

---

# 10. Pricing Workflow

* [ ] Base price can be retrieved.
* [ ] Contract pricing can be retrieved.
* [ ] Discount policy can be retrieved.
* [ ] Discount calculation is deterministic.
* [ ] Final total is deterministic.
* [ ] Approval threshold is deterministic.
* [ ] Pricing source can be explained.
* [ ] LLM does not independently determine authoritative financial values.

---

# 11. Human Approval

* [ ] Approval model exists.
* [ ] Approval request can be created.
* [ ] Workflow can pause.
* [ ] Pending approval is persisted.
* [ ] User can approve.
* [ ] User can reject.
* [ ] Workflow can resume.
* [ ] Approval authorization is enforced.
* [ ] Approval decisions are audited.

---

# 12. Memory

* [ ] Short-term graph state exists.
* [ ] Session memory exists.
* [ ] Redis is used appropriately.
* [ ] Conversation history can be stored.
* [ ] Conversation summarization exists.
* [ ] Long-term business memory exists.
* [ ] Relevant memory can be retrieved.
* [ ] Entire conversation is not blindly injected into every prompt.
* [ ] Memory retrieval has tests.

---

# 13. Context Management

* [ ] Context manager exists.
* [ ] Relevant history is selected.
* [ ] Relevant memory is selected.
* [ ] Relevant RAG context is selected.
* [ ] Untrusted content is isolated.
* [ ] Context size is controlled.
* [ ] Old conversations can be summarized.
* [ ] Context construction is testable.

---

# 14. Redis

* [ ] Redis connectivity works.
* [ ] Session state works.
* [ ] Cache works.
* [ ] TTLs are configured.
* [ ] Rate limiting works.
* [ ] Distributed lock mechanism exists where needed.
* [ ] Redis is not the source of truth for business records.
* [ ] Inventory is not dangerously cached.

---

# 15. MuleSoft-Style Integration

* [ ] Experience API exists.
* [ ] Process API exists.
* [ ] System API exists.
* [ ] APIs have clear responsibilities.
* [ ] Request/response mappings exist.
* [ ] Error handling exists.
* [ ] Simulator is clearly identified as simulated.
* [ ] Architecture is replaceable with actual MuleSoft APIs.

---

# 16. SAP Simulator

* [ ] Customer endpoint exists.
* [ ] Material endpoint exists.
* [ ] Stock endpoint exists.
* [ ] Order creation endpoint exists.
* [ ] Order retrieval endpoint exists.
* [ ] Mapping exists between application and SAP-style model.
* [ ] Failure behavior exists.
* [ ] Simulator is clearly identified as simulated.

---

# 17. MLflow

* [ ] MLflow integration exists.
* [ ] Workflow tracing exists.
* [ ] Agent tracing exists.
* [ ] Tool tracing exists.
* [ ] RAG tracing exists.
* [ ] Approval tracing exists.
* [ ] Latency is captured.
* [ ] Token usage is captured where available.
* [ ] Errors are captured.
* [ ] Evaluation datasets exist.
* [ ] Evaluation runner exists.
* [ ] Evaluation metrics come from actual runs.

---

# 18. Security

* [ ] JWT authentication exists.
* [ ] RBAC exists.
* [ ] Permission checks exist.
* [ ] Protected tools enforce permissions.
* [ ] Input validation exists.
* [ ] Rate limiting exists.
* [ ] Audit logging exists.
* [ ] PII handling exists.
* [ ] Secrets are environment-based.
* [ ] Secrets are not committed.
* [ ] Prompt injection defense exists.
* [ ] Tool authorization cannot be bypassed by the LLM.
* [ ] Unauthorized order access is rejected.
* [ ] Unauthorized order cancellation is rejected.
* [ ] Malicious input tests exist.

---

# 19. Idempotency

* [ ] Order creation is idempotent.
* [ ] Inventory reservation is idempotent where required.
* [ ] Shipment creation is idempotent where required.
* [ ] Cancellation behavior is controlled.
* [ ] Duplicate requests do not create duplicate business records.

---

# 20. Frontend

* [ ] Next.js application exists.
* [ ] Dashboard exists.
* [ ] Chat exists.
* [ ] Orders page exists.
* [ ] Approvals page exists.
* [ ] Agent trace page exists.
* [ ] Evaluations page exists.
* [ ] Knowledge page exists.
* [ ] Health page exists.
* [ ] Backend APIs are used.
* [ ] Static fake data is not used for core functionality.
* [ ] Agent workflow is visible.
* [ ] Tool calls are visible.
* [ ] RAG citations are visible.
* [ ] Approval state is visible.
* [ ] Order result is visible.

---

# 21. Observability

* [ ] Request IDs exist.
* [ ] Session IDs exist.
* [ ] Structured logs exist.
* [ ] Agent actions are traceable.
* [ ] Tool actions are traceable.
* [ ] Errors are traceable.
* [ ] Latency is measurable.
* [ ] Secrets are not logged.
* [ ] Sensitive data is minimized in logs.

---

# 22. Docker

* [ ] Backend Dockerfile exists.
* [ ] Frontend Dockerfile exists.
* [ ] MCP Dockerfile exists.
* [ ] Worker Dockerfile exists if required.
* [ ] Production Compose exists.
* [ ] Health checks exist.
* [ ] Persistent volumes exist where needed.
* [ ] Services restart appropriately.
* [ ] Internal services are not unnecessarily exposed.

---

# 23. CI/CD

* [ ] GitHub Actions exists.
* [ ] Lint runs.
* [ ] Type checks run.
* [ ] Unit tests run.
* [ ] Integration tests run.
* [ ] Security tests run.
* [ ] Agent tests run.
* [ ] Evaluation smoke test runs.
* [ ] Docker build runs.
* [ ] Failed CI blocks deployment.

---

# 24. Coolify

* [ ] Repository deploys through Coolify.
* [ ] Environment variables are configured securely.
* [ ] HTTPS works.
* [ ] Health checks work.
* [ ] Persistent storage is configured.
* [ ] Logs are accessible.
* [ ] Restart behavior works.
* [ ] PostgreSQL is not publicly exposed.
* [ ] Redis is not publicly exposed.
* [ ] Application is reachable through a public HTTPS URL.

---

# 25. Databricks

* [ ] Databricks architecture is documented.
* [ ] MLflow relationship is documented.
* [ ] Agent/model deployment path is documented.
* [ ] Evaluation path is documented.
* [ ] Local development does not require Databricks.
* [ ] No fake Databricks deployment claims are made.

---

# 26. Demo Scenario Acceptance

## Scenario 1 — Normal order

Input:

```text
Create an order for 10 Laptop Pro 14 units for ACME.
```

Expected:

* [ ] customer lookup
* [ ] product lookup
* [ ] inventory check
* [ ] pricing
* [ ] policy where needed
* [ ] order creation
* [ ] audit
* [ ] trace
* [ ] final order number

---

## Scenario 2 — Policy question

Input:

```text
What discount can ACME receive?
```

Expected:

* [ ] policy retrieval
* [ ] relevant source
* [ ] citation
* [ ] grounded response

---

## Scenario 3 — Inventory shortage

Input:

```text
Order 500 Laptop Pro 14 units for ACME.
```

Expected:

* [ ] inventory check
* [ ] shortage detected
* [ ] order not incorrectly created

---

## Scenario 4 — Approval

Input:

```text
Apply a discount above the configured approval threshold.
```

Expected:

* [ ] policy lookup
* [ ] deterministic calculation
* [ ] approval created
* [ ] graph paused
* [ ] UI shows approval
* [ ] approve/reject works
* [ ] graph resumes appropriately
* [ ] audit recorded

---

## Scenario 5 — Memory

Conversation:

```text
User:
Create an order for ACME.

User:
Use the same shipping address as before.
```

Expected:

* [ ] relevant previous context retrieved
* [ ] memory used
* [ ] unnecessary repeated question avoided

---

## Scenario 6 — MCP

Expected:

* [ ] agent invokes MCP
* [ ] MCP validates input
* [ ] authorization occurs
* [ ] service executes
* [ ] result returns to agent
* [ ] trace records tool execution

---

## Scenario 7 — Prompt injection

Input attempts to override policy/security.

Expected:

* [ ] malicious instruction is not trusted
* [ ] business policy remains authoritative
* [ ] unauthorized tool call does not execute
* [ ] event can be audited

---

## Scenario 8 — Unauthorized action

Input:

```text
Cancel an order without appropriate permission.
```

Expected:

* [ ] authorization rejects action
* [ ] no cancellation occurs
* [ ] safe error returned
* [ ] audit event recorded

---

# 27. Production Readiness

Before final completion:

* [ ] No hard-coded secrets.
* [ ] No fake production integrations.
* [ ] No fabricated metrics.
* [ ] No broken critical tests.
* [ ] No publicly exposed database.
* [ ] No publicly exposed Redis.
* [ ] Error handling reviewed.
* [ ] Security reviewed.
* [ ] Logging reviewed.
* [ ] Docker deployment verified.
* [ ] HTTPS verified.
* [ ] Backup/recovery considerations documented.
* [ ] README updated.
* [ ] Architecture diagram updated.
* [ ] Demo instructions updated.

---

# 28. Interview Readiness

An interviewer should be able to understand:

* [ ] Why LangGraph is used.
* [ ] Why MCP is used.
* [ ] Why RAG is used.
* [ ] Why pgvector is used.
* [ ] Why Redis is used.
* [ ] How memory works.
* [ ] How context is managed.
* [ ] How human approval works.
* [ ] How authorization works.
* [ ] Why LLMs do not perform authoritative business calculations.
* [ ] How MuleSoft-style API layers work.
* [ ] How SAP integration is represented.
* [ ] How MLflow is used.
* [ ] How evaluation works.
* [ ] How Docker deployment works.
* [ ] How Coolify deployment works.
* [ ] How Databricks fits into the architecture.
* [ ] How the system handles prompt injection.
* [ ] How the system handles failures.
* [ ] How the system scales.

---

# 29. Final End-to-End Acceptance Test

The following must work from the browser:

```text
User enters:

"Create an order for 10 Laptop Pro 14 units for ACME."
```

System:

```text
Authenticate user
      ↓
Create request context
      ↓
Load relevant memory
      ↓
LangGraph Supervisor
      ↓
Customer Agent
      ↓
Customer MCP tool
      ↓
Inventory Agent
      ↓
Inventory MCP tool
      ↓
Pricing Agent
      ↓
Policy/RAG
      ↓
Deterministic pricing
      ↓
Approval if necessary
      ↓
Inventory reservation
      ↓
Order creation
      ↓
Audit event
      ↓
MLflow trace
      ↓
Final response
```

The browser must display:

```text
Order created successfully

Order Number: <actual generated order number>

Customer: ACME Corporation
Items: 10 × Laptop Pro 14
Total: <actual calculated amount>

Workflow:
✓ Customer verified
✓ Inventory checked
✓ Pricing calculated
✓ Policy verified
✓ Inventory reserved
✓ Order created

Sources:
<actual policy citations>

Trace:
<actual trace/workflow identifier>
```

---

# 30. Completion Rule

The project is complete only when:

```text
All critical acceptance criteria
        +
All eight demo scenarios
        +
End-to-end order workflow
        +
Security tests
        +
Deployment verification
        +
Documentation
```

have been completed and verified.

Any unchecked critical criterion must be reported explicitly.

Never mark the project complete merely because the UI appears functional.
