# EnterpriseFlow AI — Agent & Service Contracts

This document defines the boundaries between agents, tools, services, APIs, and infrastructure.

The implementation may change internal code structure, but these logical contracts must remain intact.

---

# 1. Contract Philosophy

Each component should have one clear responsibility.

The preferred direction of communication is:

```text
User
 ↓
API
 ↓
Supervisor
 ↓
Specialist Agent
 ↓
MCP Tool
 ↓
Business Service
 ↓
Repository
 ↓
Database
```

Do not allow components to bypass layers without a documented reason.

---

# 2. Common Request Context

All major operations should support a common execution context.

Conceptual structure:

```python
ExecutionContext(
    request_id: str,
    session_id: str,
    user_id: str,
    tenant_id: str | None,
    permissions: list[str],
    workflow_id: str,
    model: str | None,
)
```

Additional fields may be added.

Do not place secrets inside the execution context.

---

# 3. Standard Tool Result

Tools should return structured results.

Conceptual structure:

```python
ToolResult(
    success: bool,
    data: object | None,
    error_code: str | None,
    error_message: str | None,
    metadata: dict,
)
```

Actual implementation may use typed Pydantic models.

---

# 4. Supervisor Contract

## Input

The Supervisor receives:

```text
user request
execution context
relevant memory
relevant conversation
available capabilities
```

Example:

```text
"Create an order for 100 laptops for ACME."
```

## Responsibilities

The Supervisor must:

1. understand intent
2. identify required entities
3. determine workflow
4. delegate to specialist agents
5. coordinate results
6. request missing information when necessary
7. handle approval
8. formulate final response

## Output

Conceptual:

```python
SupervisorResult(
    intent: str,
    action_required: bool,
    customer_id: str | None,
    workflow: str,
    required_agents: list[str],
    approval_required: bool,
    final_response: str | None,
)
```

The Supervisor must not directly perform unrestricted database operations.

---

# 5. Customer Agent Contract

## Input

```text
customer identifier
```

or:

```text
customer name
```

## Responsibilities

* identify customer
* retrieve customer profile
* retrieve contract
* retrieve credit status
* retrieve shipping information

## Tools

```text
get_customer
get_customer_contract
check_credit
get_shipping_address
```

## Output

Conceptual:

```python
CustomerResult(
    customer_id: str,
    customer_name: str,
    status: str,
    contract_id: str | None,
    credit_status: str | None,
    shipping_address: object | None,
)
```

---

# 6. Inventory Agent Contract

## Input

```text
product
quantity
location/plant if relevant
```

## Responsibilities

* product lookup
* inventory check
* inventory reservation
* inventory release

## Tools

```text
search_products
get_product
check_inventory
reserve_inventory
release_inventory
```

## Output

Conceptual:

```python
InventoryResult(
    product_id: str,
    requested_quantity: int,
    available_quantity: int,
    available: bool,
    reservation_id: str | None,
)
```

Inventory reservations must be concurrency-safe.

---

# 7. Pricing Agent Contract

## Input

```text
customer_id
product_id
quantity
contract_id
requested_discount
```

## Responsibilities

* retrieve base price
* retrieve customer contract pricing
* retrieve applicable discount
* retrieve policy
* calculate final pricing
* identify approval requirement

## Tools

```text
get_price
calculate_discount
search_policy
```

## Output

Conceptual:

```python
PricingResult(
    base_price: Decimal,
    discount_percent: Decimal,
    discount_amount: Decimal,
    final_unit_price: Decimal,
    total_price: Decimal,
    policy_source: str | None,
    approval_required: bool,
    approval_reason: str | None,
)
```

Authoritative calculations must be performed by deterministic Python code.

---

# 8. Policy/RAG Agent Contract

## Input

```text
natural language policy question
```

Example:

```text
"What discount can this customer receive?"
```

## Responsibilities

* identify policy query
* retrieve relevant documents
* provide grounded context
* provide citations
* expose metadata

## Output

Conceptual:

```python
PolicyResult(
    answer_context: str,
    citations: list[PolicyCitation],
)
```

Citation:

```python
PolicyCitation(
    document_name: str,
    version: str,
    section: str,
    chunk_id: str,
    relevance_score: float | None,
)
```

The final answer must not claim unsupported facts.

---

# 9. MCP Tool Contract

Every MCP tool must define:

```text
name
description
input schema
output schema
required permissions
side effects
idempotency behavior
error behavior
```

Example:

```text
Tool:
create_order

Permission:
orders:create

Side effect:
Creates persistent order

Idempotency:
Required

Authorization:
Required

Output:
order_id, order_number, status
```

---

# 10. Customer Tools

## get_customer

Input:

```json
{
  "customer_id": "string"
}
```

Output:

```json
{
  "customer_id": "string",
  "name": "string",
  "status": "string"
}
```

---

## get_customer_contract

Input:

```json
{
  "customer_id": "string"
}
```

Output:

```json
{
  "contract_id": "string",
  "customer_id": "string",
  "pricing_terms": {},
  "discount_limit": 0
}
```

---

## check_credit

Input:

```json
{
  "customer_id": "string"
}
```

Output:

```json
{
  "customer_id": "string",
  "status": "string",
  "available_credit": 0
}
```

---

## get_shipping_address

Input:

```json
{
  "customer_id": "string"
}
```

Output:

```json
{
  "address": {}
}
```

---

# 11. Product and Inventory Tools

## search_products

Input:

```json
{
  "query": "string"
}
```

Output:

```json
{
  "products": []
}
```

---

## get_product

Input:

```json
{
  "product_id": "string"
}
```

Output:

```json
{
  "product_id": "string",
  "name": "string",
  "sku": "string",
  "category": "string"
}
```

---

## check_inventory

Input:

```json
{
  "product_id": "string",
  "quantity": 1
}
```

Output:

```json
{
  "product_id": "string",
  "requested_quantity": 1,
  "available_quantity": 1,
  "available": true
}
```

---

## reserve_inventory

Input:

```json
{
  "product_id": "string",
  "quantity": 1,
  "order_reference": "string"
}
```

Output:

```json
{
  "reservation_id": "string",
  "status": "reserved",
  "quantity": 1
}
```

Must be idempotent where appropriate.

---

## release_inventory

Input:

```json
{
  "reservation_id": "string"
}
```

Output:

```json
{
  "reservation_id": "string",
  "status": "released"
}
```

---

# 12. Pricing Tools

## get_price

Input:

```json
{
  "customer_id": "string",
  "product_id": "string",
  "quantity": 1
}
```

Output:

```json
{
  "base_unit_price": 0,
  "currency": "USD"
}
```

---

## calculate_discount

Input:

```json
{
  "customer_id": "string",
  "product_id": "string",
  "quantity": 1,
  "requested_discount_percent": 0
}
```

Output:

```json
{
  "approved_discount_percent": 0,
  "discount_amount": 0,
  "final_total": 0,
  "approval_required": false,
  "reason": "string"
}
```

The calculation must be deterministic.

---

# 13. Order Tools

## create_order

Input:

```json
{
  "customer_id": "string",
  "items": [],
  "shipping_address": {},
  "pricing": {},
  "idempotency_key": "string"
}
```

Output:

```json
{
  "order_id": "string",
  "order_number": "string",
  "status": "created",
  "total": 0
}
```

Authorization required.

Idempotency required.

---

## get_order

Input:

```json
{
  "order_id": "string"
}
```

Output:

```json
{
  "order_id": "string",
  "order_number": "string",
  "status": "string",
  "items": [],
  "total": 0
}
```

---

## cancel_order

Input:

```json
{
  "order_id": "string",
  "reason": "string",
  "idempotency_key": "string"
}
```

Authorization required.

---

# 14. Shipping Tools

## get_shipping_options

Input:

```json
{
  "customer_id": "string",
  "destination": {},
  "items": []
}
```

Output:

```json
{
  "options": []
}
```

---

## create_shipment

Input:

```json
{
  "order_id": "string",
  "shipping_option": "string",
  "idempotency_key": "string"
}
```

Output:

```json
{
  "shipment_id": "string",
  "status": "created"
}
```

---

## track_shipment

Input:

```json
{
  "shipment_id": "string"
}
```

Output:

```json
{
  "shipment_id": "string",
  "status": "string",
  "events": []
}
```

---

# 15. Policy Tool

## search_policy

Input:

```json
{
  "query": "string",
  "department": "string | null",
  "region": "string | null"
}
```

Output:

```json
{
  "results": [
    {
      "document_name": "string",
      "version": "string",
      "section": "string",
      "content": "string",
      "score": 0
    }
  ]
}
```

---

# 16. Approval Contract

When approval is required:

```python
ApprovalRequest(
    approval_id: str,
    workflow_id: str,
    requested_by: str,
    approval_type: str,
    reason: str,
    requested_value: object,
    policy_limit: object,
    status: str,
)
```

Statuses:

```text
pending
approved
rejected
expired
cancelled
```

Approval action:

```python
ApprovalDecision(
    approval_id: str,
    decision: str,
    decided_by: str,
    comment: str | None,
)
```

Every decision must be audited.

---

# 17. Audit Contract

Every important mutation must create an audit event.

Conceptual:

```python
AuditEvent(
    event_id: str,
    request_id: str,
    user_id: str,
    action: str,
    resource_type: str,
    resource_id: str | None,
    status: str,
    timestamp: datetime,
    metadata: dict,
)
```

Examples:

```text
ORDER_CREATED
ORDER_CANCELLED
INVENTORY_RESERVED
APPROVAL_REQUESTED
APPROVAL_APPROVED
APPROVAL_REJECTED
UNAUTHORIZED_TOOL_ATTEMPT
```

---

# 18. Error Contract

All layers should use structured error categories.

```text
VALIDATION_ERROR
AUTHENTICATION_ERROR
AUTHORIZATION_ERROR
NOT_FOUND
CONFLICT
INSUFFICIENT_INVENTORY
APPROVAL_REQUIRED
EXTERNAL_SERVICE_ERROR
LLM_ERROR
TOOL_ERROR
DATABASE_ERROR
RATE_LIMITED
```

Errors returned to the frontend must be safe and understandable.

---

# 19. Agent-to-Agent Rules

Agents may exchange structured information.

Do not pass uncontrolled natural-language dumps when a typed object can be used.

Preferred:

```text
Customer Agent
     ↓
CustomerResult
     ↓
Supervisor
```

rather than:

```text
Customer Agent
     ↓
"Here is a huge paragraph..."
```

---

# 20. Agent-to-MCP Rules

Agents request capabilities through typed tools.

The MCP layer must enforce:

```text
authentication
authorization
input validation
logging
business rules
```

The agent does not bypass MCP for protected operations.

---

# 21. MCP-to-Service Rules

MCP tools call business services.

Business services own:

* validation
* business logic
* transactions
* database operations

---

# 22. Service-to-Repository Rules

Repositories handle persistence.

Repositories should not contain LLM logic.

Business decisions belong in services.

---

# 23. Final Response Contract

The final API response should provide, where appropriate:

```json
{
  "request_id": "string",
  "status": "success",
  "message": "string",
  "data": {},
  "workflow": {},
  "citations": [],
  "approval": null
}
```

Internal implementation details should not leak sensitive information.

---

# 24. Contract Evolution

If a contract changes:

1. Update this document.
2. Update affected code.
3. Update tests.
4. Update documentation.
5. Explain the reason in the phase report.

Do not silently break contracts.
