# EnterpriseFlow AI — Project Specification

## 1. Project Overview

### Project Name

**EnterpriseFlow AI — Enterprise Agentic Order Management & Automation Platform**

### Objective

Build a production-style enterprise AI agent platform that demonstrates practical implementation of:

* LLM-powered agents
* Agentic workflows
* LangGraph orchestration
* Grok/xAI API integration
* Multi-agent collaboration
* MCP-based tool integration
* Retrieval-Augmented Generation (RAG)
* PostgreSQL + pgvector
* Redis caching and short-term memory
* Long-term business memory
* Context management
* Human-in-the-loop approvals
* Enterprise API integration patterns
* MuleSoft-style Experience / Process / System APIs
* SAP-style enterprise system integration
* MLflow tracing and evaluation
* Security and authorization
* Docker-based deployment
* Coolify deployment
* CI/CD
* Databricks integration/deployment path
* Production observability

The application must be suitable as a portfolio project for an **AI Agentic Developer / Enterprise AI Developer** role.

The system must be genuinely runnable.

Do not create a collection of static mock screens or hard-coded demonstrations.

The core workflow must execute through real Python services, real database operations, real agent orchestration, real API/tool calls, and real state transitions.

---

# 2. Primary User Story

The primary demonstration workflow is enterprise order management.

A user should be able to enter:

> "Create an order for 100 laptops for ACME."

The platform should:

1. Identify the customer.
2. Retrieve customer information.
3. Retrieve customer contract information.
4. Verify customer permissions/authorization.
5. Check credit status where applicable.
6. Identify the requested product.
7. Check inventory.
8. Retrieve applicable pricing.
9. Retrieve relevant pricing/discount policies using RAG.
10. Calculate pricing using deterministic business logic.
11. Determine whether approval is required.
12. Request human approval when required.
13. Reserve inventory when appropriate.
14. Create the order.
15. Persist the order.
16. Return the order number and summary.
17. Record an audit trail.
18. Record the agent/tool workflow.
19. Capture relevant MLflow tracing/evaluation information.
20. Show the workflow to the user through the frontend.

The LLM must NOT independently perform authoritative business calculations or bypass authorization/policy controls.

---

# 3. Design Principles

The following principles are mandatory.

## 3.1 LLMs reason; deterministic services decide

LLMs may:

* interpret natural language
* classify intent
* select appropriate tools
* determine workflow routing
* summarize information
* formulate responses
* reason over retrieved documents

LLMs must NOT be the final authority for:

* prices
* discounts
* inventory quantities
* customer authorization
* approval thresholds
* financial calculations
* order persistence
* security permissions
* database transactions

Those decisions must be implemented by deterministic Python services.

---

## 3.2 LangGraph controls workflow

LangGraph must control:

* workflow state
* agent transitions
* branching
* retries where appropriate
* human approval interruption/resumption
* final workflow completion

Do not implement the entire agent workflow as one giant prompt.

---

## 3.3 MCP is the tool boundary

Agents should access enterprise capabilities through typed MCP tools wherever practical.

Example:

```text
Supervisor
    ↓
Inventory Agent
    ↓
MCP tool
    ↓
Inventory service
    ↓
PostgreSQL
```

The LLM must never receive unrestricted database access.

---

## 3.4 Enterprise integrations must be layered

Enterprise API architecture should follow:

```text
Experience API
      ↓
Process API
      ↓
System API
      ↓
Enterprise System
```

Initially, MuleSoft and SAP should be represented by compatible Python/FastAPI simulators.

The application must clearly label simulated integrations as simulated.

Do not falsely claim that actual MuleSoft Anypoint or SAP infrastructure is being used unless a real integration is configured.

---

# 4. Target Architecture

```text
                         Internet
                            |
                         Coolify
                            |
              +-------------+-------------+
              |                           |
        Next.js Frontend             FastAPI API
                                          |
                              Authentication / RBAC
                                          |
                                    Request Context
                                          |
                                  Context Manager
                                          |
                                   LangGraph Graph
                                          |
                                    Supervisor
                                          |
                 +----------------+---------+----------------+
                 |                |         |                |
           Customer Agent   Inventory   Pricing Agent   Policy Agent
                              Agent
                 |                |         |                |
                 +----------------+---------+----------------+
                                          |
                                    MCP Server
                                          |
                              Enterprise Tool Layer
                                          |
                       +------------------+------------------+
                       |                  |                  |
                 Process API         System API          RAG Service
                       |                  |                  |
                 MuleSoft-style       SAP Mock         pgvector
                       |                  |
                       +--------+---------+
                                |
                           PostgreSQL
                                |
                       +--------+---------+
                       |                  |
                    Redis              MLflow
```

---

# 5. Technology Stack

## Backend

* Python 3.12+
* FastAPI
* Pydantic
* SQLAlchemy
* Alembic
* LangGraph
* LangChain where useful
* xAI/Grok API
* MCP
* PostgreSQL
* pgvector
* Redis
* MLflow
* pytest
* Ruff
* mypy or equivalent type checker

## Frontend

* Next.js
* TypeScript
* React
* modern component-based UI

## Infrastructure

* Docker
* Docker Compose
* Coolify
* GitHub Actions

## Optional enterprise platform integration

* Databricks
* MLflow
* actual MuleSoft if later available
* actual SAP if later available

---

# 6. Repository Structure

The final repository should approximately follow:

```text
enterprise-flow-ai/
│
├── specs/
│   ├── 01_PROJECT_SPEC.md
│   ├── 02_EXECUTION_RULES.md
│   ├── 03_AGENT_CONTRACTS.md
│   ├── 04_PHASE_PLAN.md
│   └── 05_ACCEPTANCE_CRITERIA.md
│
├── backend/
│   ├── app/
│   │   ├── api/
│   │   ├── agents/
│   │   ├── config/
│   │   ├── context/
│   │   ├── db/
│   │   ├── graph/
│   │   ├── integrations/
│   │   ├── mcp/
│   │   ├── memory/
│   │   ├── models/
│   │   ├── policies/
│   │   ├── rag/
│   │   ├── security/
│   │   ├── services/
│   │   ├── tools/
│   │   └── main.py
│   │
│   ├── tests/
│   ├── alembic/
│   ├── pyproject.toml
│   └── Dockerfile
│
├── frontend/
│   ├── app/
│   ├── components/
│   ├── lib/
│   ├── types/
│   ├── tests/
│   ├── package.json
│   └── Dockerfile
│
├── mcp-server/
│   ├── app/
│   ├── tests/
│   ├── pyproject.toml
│   └── Dockerfile
│
├── knowledge/
│   ├── pricing_policy.pdf
│   ├── discount_policy.pdf
│   ├── shipping_policy.pdf
│   ├── inventory_policy.pdf
│   ├── credit_policy.pdf
│   ├── order_approval_policy.pdf
│   ├── return_policy.pdf
│   └── escalation_policy.pdf
│
├── evaluations/
│   ├── datasets/
│   ├── scorers/
│   └── scripts/
│
├── infra/
│   ├── docker/
│   ├── coolify/
│   └── scripts/
│
├── .github/
│   └── workflows/
│
├── docker-compose.yml
├── docker-compose.prod.yml
├── .env.example
├── .gitignore
├── README.md
└── Makefile
```

Hermes may improve the exact structure if there is a strong engineering reason, but must preserve the architectural boundaries.

---

# 7. Grok/xAI Integration

Grok must be accessed through a provider abstraction.

Do not spread direct xAI SDK/API calls throughout the application.

Preferred conceptual interface:

```python
class LLMProvider:
    async def generate(...)
    async def generate_structured(...)
    async def generate_with_tools(...)
```

Implement an xAI/Grok provider.

Configuration must come from environment variables.

Example:

```text
XAI_API_KEY=
XAI_MODEL=
XAI_BASE_URL=
```

Never commit API keys.

The application must support:

* timeouts
* retries
* structured outputs where appropriate
* tool/function calling where appropriate
* token usage tracking where available
* request IDs
* model configuration
* error handling

The provider layer should make it possible to replace Grok later without rewriting agents.

---

# 8. Agent Architecture

The system must contain these logical agents.

## 8.1 Supervisor Agent

Responsibilities:

* interpret user intent
* identify workflow
* determine information vs action request
* coordinate specialist agents
* determine whether required information is missing
* route to appropriate agents/tools
* coordinate approval
* produce final response

The Supervisor must not directly perform business-critical database mutations.

---

## 8.2 Customer Agent

Responsibilities:

* retrieve customer
* retrieve customer contract
* retrieve credit information
* retrieve shipping information
* verify customer status

Example tools:

```text
get_customer
get_customer_contract
check_credit
get_shipping_address
```

---

## 8.3 Inventory Agent

Responsibilities:

* search products
* retrieve product details
* check inventory
* reserve inventory
* release inventory

Example tools:

```text
search_products
get_product
check_inventory
reserve_inventory
release_inventory
```

Inventory operations must be transaction-safe.

Use locking where necessary.

---

## 8.4 Pricing Agent

Responsibilities:

* retrieve applicable pricing
* retrieve contract pricing
* retrieve discounts
* request policy information
* calculate price using deterministic services
* identify whether approval is required

The LLM must not independently calculate authoritative prices.

---

## 8.5 Policy/RAG Agent

Responsibilities:

* search policies
* retrieve relevant passages
* provide citations
* provide document metadata
* distinguish retrieved facts from generated explanation

Supported policy documents:

```text
pricing_policy.pdf
discount_policy.pdf
shipping_policy.pdf
inventory_policy.pdf
credit_policy.pdf
order_approval_policy.pdf
return_policy.pdf
escalation_policy.pdf
```

---

# 9. MCP Tool Layer

The system must implement MCP-compatible tools.

Minimum tool set:

```text
get_customer
get_customer_contract
check_credit
search_products
get_product
check_inventory
reserve_inventory
release_inventory
get_price
calculate_discount
create_order
get_order
cancel_order
get_shipping_options
create_shipment
track_shipment
search_policy
```

Each tool must have:

* explicit input schema
* explicit output schema
* validation
* authorization requirements
* error behavior
* logging
* trace/request ID support

Tools must not silently accept arbitrary unvalidated data.

---

# 10. Database

PostgreSQL must be the primary persistent datastore.

pgvector must be used for document embeddings.

Minimum business entities:

```text
Customer
CustomerContract
Product
Inventory
PricingCondition
Order
OrderItem
Approval
AuditLog
PolicyDocument
PolicyChunk
User
Role
Permission
Conversation
ConversationMessage
WorkflowExecution
```

Use database migrations.

Do not create production tables dynamically during application startup.

---

# 11. Enterprise Data

Seed deterministic demo data.

Example customer:

```text
ACME Corporation
```

Example products:

```text
Laptop Pro 14
Laptop Enterprise 15
Business Monitor 27
Enterprise Dock
```

Include realistic:

* prices
* inventory
* customer contracts
* discount limits
* approval thresholds
* shipping options

The demo dataset must be deterministic so that automated tests and interviewer demonstrations produce predictable results.

---

# 12. RAG Architecture

Pipeline:

```text
Documents
    ↓
Document Loader
    ↓
Text Extraction
    ↓
Cleaning
    ↓
Chunking
    ↓
Metadata
    ↓
Embeddings
    ↓
pgvector
    ↓
Similarity Retrieval
    ↓
Optional Reranking
    ↓
Context Construction
    ↓
Grok
```

Every chunk should contain metadata such as:

```text
document_name
document_version
section
effective_date
department
region
document_type
```

RAG responses should provide citations.

The system must prevent retrieved text from being automatically treated as executable instructions.

---

# 13. Memory

Implement multiple memory layers.

## Short-term memory

LangGraph state.

Contains:

* current request
* current entities
* active workflow
* tool results
* approval status
* current order state

## Session memory

Redis and/or PostgreSQL.

Contains:

* recent conversation
* conversation summary
* current customer
* current order
* recent tool results

## Long-term business memory

PostgreSQL.

Examples:

* customer preferences
* common products
* preferred shipping method
* prior order patterns

Memory retrieval must be selective.

Do not inject the entire conversation history into every LLM call.

---

# 14. Context Management

Implement a context manager responsible for:

* selecting relevant conversation history
* selecting relevant memory
* retrieving relevant policies
* sanitizing untrusted content
* controlling context size
* summarizing old messages
* prioritizing system/developer/business constraints
* preventing unnecessary token usage

The context manager should expose a structured context object to the graph.

---

# 15. Redis

Redis must support:

* session state
* caching
* distributed locks
* rate limiting
* temporary workflow state

Suggested TTLs:

```text
Product metadata: 1 hour
Policy retrieval/cache: 1 hour
Customer profile: 15 minutes
Order status: 5–10 seconds
Pricing: 5–15 minutes
Inventory: conservative caching or no aggressive cache
```

Do not aggressively cache inventory availability.

---

# 16. Human-in-the-Loop

The system must support approval workflows.

Example:

```text
Policy maximum discount = 15%

Requested discount = 25%

        ↓

Approval required

        ↓

Workflow pauses

        ↓

Human reviews

        ↓

Approve / Reject

        ↓

LangGraph resumes

        ↓

Continue or terminate
```

Approval state must be persisted.

The frontend must expose pending approvals.

Approval actions must be authorized and audited.

---

# 17. MuleSoft-Style Integration

Implement an API architecture compatible with MuleSoft principles.

```text
Experience API
      ↓
Process API
      ↓
System API
```

Example:

```text
POST /experience/orders

        ↓

POST /process/orders

        ↓

GET /system/customer/{id}
GET /system/inventory/{id}
POST /system/order
```

These are initially Python/FastAPI simulated APIs.

The code should keep integration boundaries clear enough that actual MuleSoft APIs could replace them later.

Do not call the simulator "MuleSoft" in a way that falsely implies an actual Anypoint deployment.

Use terminology such as:

**MuleSoft-style API-led integration simulator**

---

# 18. SAP-Style System

Implement mock SAP-compatible business endpoints.

Examples:

```text
GET /sap/customers/{id}
GET /sap/materials/{id}
GET /sap/stock/{id}
POST /sap/orders
GET /sap/orders/{id}
```

Model concepts such as:

* Customer
* Material
* Plant
* Stock
* Sales Order
* Pricing Condition

These are simulated enterprise endpoints.

---

# 19. MLflow

Use MLflow for tracing/evaluation where practical.

Capture:

```text
request_id
session_id
user_id
model
model_version
prompt/version
agent
tool
latency
token usage
retrieved documents
errors
workflow state
approval
final outcome
```

Trace example:

```text
Supervisor
  ├── Customer Agent
  │     └── get_customer
  │
  ├── Inventory Agent
  │     └── check_inventory
  │
  ├── Pricing Agent
  │     ├── search_policy
  │     └── calculate_discount
  │
  ├── Approval
  │
  └── create_order
```

Do not fabricate evaluation metrics.

Metrics must be generated from actual evaluation runs.

---

# 20. Evaluation

Create evaluation datasets covering:

### Order execution

* valid order
* invalid customer
* insufficient inventory
* approval-required discount
* invalid product
* failed order creation

### RAG

* correct policy retrieval
* incorrect policy retrieval
* outdated policy
* irrelevant policy
* citation correctness

### Security

* prompt injection
* unauthorized customer lookup
* unauthorized order cancellation
* tool misuse
* malicious input

### Memory

* multi-turn customer reference
* prior product preference
* conversation summarization

### Agent routing

* correct agent selection
* unnecessary agent invocation
* incorrect tool selection

Track actual results.

---

# 21. Security

Implement:

* JWT authentication
* RBAC
* permission-aware tools
* input validation
* rate limiting
* PII masking where appropriate
* audit logging
* prompt-injection defenses
* tool authorization
* idempotency
* request IDs
* secure environment configuration

Security checks must occur outside the LLM.

Example:

```text
LLM says:
"Cancel order 123"

       ↓

Authorization layer

       ↓

Does user have order cancellation permission?

       ↓

Yes → tool executes
No  → tool rejected
```

---

# 22. Frontend

Create a Next.js frontend.

Required pages:

```text
/dashboard
/chat
/orders
/approvals
/traces
/evaluations
/knowledge
/health
```

The chat interface must show:

* user request
* agent activity
* tool calls
* RAG sources
* approval status
* final result

The user should be able to inspect the workflow rather than seeing only a chatbot response.

---

# 23. Dashboard

Dashboard should display:

* workflow executions
* successful orders
* pending approvals
* failed workflows
* latency
* token usage where available
* recent agent activity
* system health

Do not display fabricated metrics.

If a metric has no data, display an explicit empty state.

---

# 24. Docker

Local Docker Compose must provide:

```text
frontend
api
mcp-server
postgres
redis
mlflow
worker
```

Only required public services should be exposed.

PostgreSQL and Redis should remain internal in production.

Every service should have appropriate health checks.

---

# 25. Coolify

The final application must be deployable through Coolify.

Deployment should support:

* Git-based deployment
* Docker/Compose
* environment variables
* persistent storage
* HTTPS
* health checks
* restart policies
* deployment logs

The application should be accessible through a public HTTPS URL.

---

# 26. CI/CD

GitHub Actions should run:

```text
lint
type check
unit tests
integration tests
security tests
agent tests
RAG tests
evaluation smoke tests
Docker build
```

Deployment must happen only after successful CI.

---

# 27. Databricks

Provide a documented Databricks integration/deployment path.

The system should demonstrate understanding of:

* model/agent deployment
* MLflow
* evaluation
* production AI lifecycle
* enterprise data integration

Do not make Databricks a mandatory dependency for local development.

The application must remain runnable locally without a Databricks account.

---

# 28. Observability

Every request should have a trace/request ID.

Structured logs should include:

```text
timestamp
level
request_id
session_id
user_id
component
agent
tool
duration
status
error
```

Avoid logging secrets.

Avoid logging sensitive PII unnecessarily.

---

# 29. Demo Scenarios

The final application must support these interviewer demonstrations.

## Scenario 1 — Normal order

```text
Create an order for 10 Laptop Pro 14 units for ACME.
```

Expected:

* customer lookup
* inventory check
* pricing
* policy
* order creation

---

## Scenario 2 — RAG

```text
What discount can ACME receive under its current policy?
```

Expected:

* policy retrieval
* cited source
* grounded answer

---

## Scenario 3 — Inventory shortage

```text
Order 500 Laptop Pro 14 units for ACME.
```

Expected:

* inventory check
* shortage detection
* no invalid order creation

---

## Scenario 4 — Human approval

Request a discount exceeding the allowed threshold.

Expected:

* policy retrieval
* deterministic discount calculation
* approval request
* workflow pause
* human approval
* workflow resume

---

## Scenario 5 — Memory

```text
User:
Create an order for ACME.

User:
Use the same shipping address as before.
```

Expected:

* relevant session/business memory retrieval
* no unnecessary repeated question

---

## Scenario 6 — MCP

Show an agent invoking an MCP tool and the tool calling the enterprise service.

---

## Scenario 7 — Prompt injection

User attempts to override system policy.

Expected:

* malicious instruction is treated as untrusted input
* business rules remain authoritative
* no unauthorized tool execution

---

## Scenario 8 — Unauthorized action

User attempts to access or modify data without permission.

Expected:

* authorization layer rejects action
* denial is logged
* LLM cannot bypass authorization

---

# 30. Final Definition of the Product

The final system should demonstrate the following complete chain:

```text
Natural Language
      ↓
FastAPI
      ↓
Authentication / RBAC
      ↓
Context Management
      ↓
LangGraph
      ↓
Grok
      ↓
Specialist Agents
      ↓
RAG / Memory
      ↓
MCP
      ↓
Enterprise APIs
      ↓
MuleSoft-style Integration
      ↓
SAP-style System
      ↓
Deterministic Business Logic
      ↓
Approval if required
      ↓
Database Transaction
      ↓
Audit
      ↓
MLflow Trace
      ↓
Frontend Result
```

The implementation must prioritize correctness, testability, security, observability, and enterprise architecture over unnecessary complexity.
