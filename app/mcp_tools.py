"""MCP tool layer — agents call typed tools; tools call services."""

from __future__ import annotations

import logging
import threading
import uuid
from collections.abc import Callable
from dataclasses import dataclass
from decimal import Decimal
from typing import Any

from pydantic import BaseModel, Field, ValidationError

from app.db import session_scope
from app.services import (
    CustomerService,
    InventoryService,
    OrderService,
    PricingService,
    ProductService,
    ServiceError,
)

logger = logging.getLogger(__name__)

# ponytail: Redis-backed idempotency with in-process fallback
_IDEMPOTENCY: dict[str, dict[str, Any]] = {}
_IDEM_LOCK = threading.Lock()

# Role → permissions (seeded codes)
ROLE_PERMS: dict[str, set[str]] = {
    "admin": {
        "customer:read",
        "product:read",
        "inventory:read",
        "inventory:reserve",
        "pricing:read",
        "order:create",
        "order:read",
        "order:cancel",
        "shipping:read",
        "shipping:write",
        "policy:read",
    },
    "sales": {
        "customer:read",
        "product:read",
        "inventory:read",
        "inventory:reserve",
        "pricing:read",
        "order:create",
        "order:read",
        "order:cancel",
        "shipping:read",
        "policy:read",
    },
    "viewer": {
        "customer:read",
        "product:read",
        "inventory:read",
        "pricing:read",
        "order:read",
        "shipping:read",
        "policy:read",
    },
}

SHIPPING_OPTIONS = [
    {"code": "GROUND", "name": "Ground", "days": 5, "cost": "25.00"},
    {"code": "EXPRESS", "name": "Express", "days": 2, "cost": "75.00"},
    {"code": "OVERNIGHT", "name": "Overnight", "days": 1, "cost": "150.00"},
]

# ponytail: static policy pack; DB CMS when content team needs edits
POLICIES = [
    {
        "id": "pol_credit",
        "title": "Credit limit policy",
        "body": "Orders exceeding available credit require manager approval.",
        "tags": ["credit", "approval"],
    },
    {
        "id": "pol_discount",
        "title": "Discount authority",
        "body": "Discounts above contract terms require pricing approval.",
        "tags": ["discount", "pricing"],
    },
    {
        "id": "pol_inventory",
        "title": "Inventory reservation",
        "body": "Reserved stock is held 24h; release on cancel.",
        "tags": ["inventory", "reservation"],
    },
]

# in-memory shipments
_SHIPMENTS: dict[str, dict[str, Any]] = {}


class ToolError(Exception):
    def __init__(self, code: str, message: str, http_status: int = 400):
        super().__init__(message)
        self.code = code
        self.message = message
        self.http_status = http_status


@dataclass
class ToolSpec:
    name: str
    description: str
    permission: str
    side_effects: bool
    idempotent: bool
    input_model: type[BaseModel]
    handler: Callable[[BaseModel, str, str | None], dict[str, Any]]


# ---- input schemas ----


class CustomerCodeIn(BaseModel):
    customer_code: str | None = None
    customer_id: str | None = None

    def code(self) -> str:
        v = (self.customer_code or self.customer_id or "").strip()
        if not v:
            raise ValueError("customer_code or customer_id required")
        return v.upper()


class CreditIn(BaseModel):
    customer_code: str
    amount: Decimal = Field(gt=0)


class SearchIn(BaseModel):
    query: str = Field(min_length=1)


class SkuIn(BaseModel):
    sku: str = Field(min_length=1)


class QtySkuIn(BaseModel):
    sku: str
    quantity: int = Field(gt=0)
    idempotency_key: str | None = None


class PriceIn(BaseModel):
    sku: str
    quantity: int = Field(default=1, gt=0)
    customer_code: str | None = "ACME"


class CreateOrderIn(BaseModel):
    customer_code: str
    sku: str
    quantity: int = Field(gt=0)
    order_number: str | None = None
    reserve: bool = True
    idempotency_key: str | None = None


class OrderRefIn(BaseModel):
    order_number: str | None = None
    order_id: str | None = None


class CancelOrderIn(BaseModel):
    order_number: str
    idempotency_key: str | None = None


class ShippingOptsIn(BaseModel):
    order_number: str | None = None
    weight_kg: float | None = None


class CreateShipmentIn(BaseModel):
    order_number: str
    option_code: str = "GROUND"
    idempotency_key: str | None = None


class TrackShipmentIn(BaseModel):
    tracking_number: str


class PolicySearchIn(BaseModel):
    query: str = Field(min_length=1)


def _dec(v: Decimal | str | float) -> str:
    return str(v)


def _require(role: str, perm: str) -> None:
    perms = ROLE_PERMS.get(role, set())
    if perm not in perms:
        raise ToolError("UNAUTHORIZED", f"Role {role!r} lacks {perm}", http_status=403)


def _idem_get(key: str | None) -> dict[str, Any] | None:
    if not key:
        return None
    try:
        from app.memory import cache_get

        hit = cache_get("idem", key)
        if isinstance(hit, dict):
            return hit
    except Exception:  # noqa: BLE001
        pass
    with _IDEM_LOCK:
        return _IDEMPOTENCY.get(key)


def _idem_put(key: str | None, value: dict[str, Any]) -> None:
    if not key:
        return
    try:
        from app.memory import cache_set

        cache_set("idem", key, value, ttl=60 * 60 * 24)
    except Exception:  # noqa: BLE001
        pass
    with _IDEM_LOCK:
        _IDEMPOTENCY[key] = value


# ---- handlers ----


def h_get_customer(inp: CustomerCodeIn, role: str, request_id: str | None) -> dict:
    _require(role, "customer:read")
    try:
        code = inp.code()
    except ValueError as e:
        raise ToolError("INVALID_INPUT", str(e), http_status=422) from e
    with session_scope() as s:
        c = CustomerService(s).get_by_code(code)
        return {
            "customer_id": c.id,
            "customer_code": c.code,
            "name": c.name,
            "status": c.status,
            "credit_limit": _dec(c.credit_limit),
            "credit_used": _dec(c.credit_used),
        }


def h_get_contract(inp: CustomerCodeIn, role: str, request_id: str | None) -> dict:
    _require(role, "customer:read")
    try:
        code = inp.code()
    except ValueError as e:
        raise ToolError("INVALID_INPUT", str(e), http_status=422) from e
    with session_scope() as s:
        c = CustomerService(s).get_by_code(code)
        ct = CustomerService(s).get_contract(code)
        return {
            "contract_id": ct.id,
            "customer_id": c.id,
            "customer_code": c.code,
            "contract_number": ct.contract_number,
            "pricing_terms": {"discount_pct": _dec(ct.discount_pct), "payment_terms": ct.payment_terms},
            "active": ct.active,
        }


def h_check_credit(inp: CreditIn, role: str, request_id: str | None) -> dict:
    _require(role, "customer:read")
    with session_scope() as s:
        ok = CustomerService(s).credit_ok(inp.customer_code.upper(), Decimal(inp.amount))
        c = CustomerService(s).get_by_code(inp.customer_code)
        available = Decimal(c.credit_limit) - Decimal(c.credit_used)
        return {
            "customer_code": c.code,
            "amount": _dec(inp.amount),
            "approved": ok,
            "credit_available": _dec(available),
        }


def h_search_products(inp: SearchIn, role: str, request_id: str | None) -> dict:
    _require(role, "product:read")
    with session_scope() as s:
        rows = ProductService(s).search(inp.query)
        return {
            "products": [
                {"sku": p.sku, "name": p.name, "unit_price": _dec(p.unit_price), "currency": p.currency}
                for p in rows
            ]
        }


def h_get_product(inp: SkuIn, role: str, request_id: str | None) -> dict:
    _require(role, "product:read")
    with session_scope() as s:
        p = ProductService(s).get_by_sku(inp.sku)
        return {
            "sku": p.sku,
            "name": p.name,
            "unit_price": _dec(p.unit_price),
            "currency": p.currency,
            "category": p.category,
        }


def h_check_inventory(inp: SkuIn, role: str, request_id: str | None) -> dict:
    _require(role, "inventory:read")
    try:
        from app.memory import cache_get, cache_set

        hit = cache_get("inv", inp.sku.upper())
        if isinstance(hit, dict):
            return {**hit, "cached": True}
    except Exception:  # noqa: BLE001
        hit = None
    with session_scope() as s:
        v = InventoryService(s).view(inp.sku)
        out = {
            "sku": v.sku,
            "on_hand": v.on_hand,
            "reserved": v.reserved,
            "available": v.available,
            "warehouse": v.warehouse,
        }
    try:
        from app.memory import cache_set

        cache_set("inv", inp.sku.upper(), out, ttl=15)
    except Exception:  # noqa: BLE001
        pass
    return out


def h_reserve_inventory(inp: QtySkuIn, role: str, request_id: str | None) -> dict:
    _require(role, "inventory:reserve")
    cached = _idem_get(inp.idempotency_key)
    if cached:
        return {**cached, "idempotent_replay": True}
    from app.memory import cache_delete, distributed_lock

    with distributed_lock(f"inv:{inp.sku.upper()}", ttl_seconds=15, wait_seconds=8) as ok:
        if not ok:
            raise ToolError("LOCK_TIMEOUT", f"Could not lock inventory for {inp.sku}", http_status=409)
        with session_scope() as s:
            v = InventoryService(s).reserve(inp.sku, inp.quantity, actor=role, request_id=request_id)
            out = {
                "sku": v.sku,
                "quantity": inp.quantity,
                "on_hand": v.on_hand,
                "reserved": v.reserved,
                "available": v.available,
            }
            _idem_put(inp.idempotency_key, out)
    try:
        cache_delete("inv", inp.sku.upper())
    except Exception:  # noqa: BLE001
        pass
    return out


def h_release_inventory(inp: QtySkuIn, role: str, request_id: str | None) -> dict:
    _require(role, "inventory:reserve")
    cached = _idem_get(inp.idempotency_key)
    if cached:
        return {**cached, "idempotent_replay": True}
    from app.memory import cache_delete, distributed_lock

    with distributed_lock(f"inv:{inp.sku.upper()}", ttl_seconds=15, wait_seconds=8) as ok:
        if not ok:
            raise ToolError("LOCK_TIMEOUT", f"Could not lock inventory for {inp.sku}", http_status=409)
        with session_scope() as s:
            v = InventoryService(s).release(inp.sku, inp.quantity, actor=role, request_id=request_id)
            out = {
                "sku": v.sku,
                "quantity": inp.quantity,
                "on_hand": v.on_hand,
                "reserved": v.reserved,
                "available": v.available,
            }
            _idem_put(inp.idempotency_key, out)
    try:
        cache_delete("inv", inp.sku.upper())
    except Exception:  # noqa: BLE001
        pass
    return out


def h_get_price(inp: PriceIn, role: str, request_id: str | None) -> dict:
    _require(role, "pricing:read")
    ck = f"{inp.sku.upper()}:{inp.quantity}:{inp.customer_code.upper()}"
    try:
        from app.memory import cache_get, cache_set

        hit = cache_get("price", ck)
        if isinstance(hit, dict):
            return {**hit, "cached": True}
    except Exception:  # noqa: BLE001
        pass
    with session_scope() as s:
        q = PricingService(s).quote(inp.sku, inp.quantity, inp.customer_code)
        out = {
            "sku": q.sku,
            "quantity": q.quantity,
            "unit_price": _dec(q.unit_price),
            "discount_pct": _dec(q.discount_pct),
            "line_total": _dec(q.line_total),
        }
    try:
        from app.memory import cache_set

        cache_set("price", ck, out, ttl=60)
    except Exception:  # noqa: BLE001
        pass
    return out


def h_calculate_discount(inp: PriceIn, role: str, request_id: str | None) -> dict:
    # same engine as get_price — discount breakdown
    out = h_get_price(inp, role, request_id)
    unit = Decimal(out["unit_price"])
    qty = int(out["quantity"])
    gross = unit * qty
    net = Decimal(out["line_total"])
    out["gross"] = _dec(gross)
    out["discount_amount"] = _dec(gross - net)
    return out


def h_create_order(inp: CreateOrderIn, role: str, request_id: str | None) -> dict:
    _require(role, "order:create")
    cached = _idem_get(inp.idempotency_key)
    if cached:
        return {**cached, "idempotent_replay": True}
    order_number = inp.order_number or f"ORD-{uuid.uuid4().hex[:10].upper()}"
    with session_scope() as s:
        order = OrderService(s).create_draft(
            inp.customer_code.upper(),
            inp.sku,
            inp.quantity,
            order_number=order_number,
            reserve=inp.reserve,
            actor=role,
            request_id=request_id,
        )
        out = {
            "order_id": order.id,
            "order_number": order.order_number,
            "status": order.status,
            "total": _dec(order.total),
            "currency": order.currency,
        }
        _idem_put(inp.idempotency_key, out)
        return out


def h_get_order(inp: OrderRefIn, role: str, request_id: str | None) -> dict:
    _require(role, "order:read")
    with session_scope() as s:
        order = OrderService(s).get_order(order_number=inp.order_number, order_id=inp.order_id)
        return {
            "order_id": order.id,
            "order_number": order.order_number,
            "status": order.status,
            "total": _dec(order.total),
            "items": [
                {
                    "sku": i.sku,
                    "quantity": i.quantity,
                    "line_total": _dec(i.line_total),
                    "discount_pct": _dec(i.discount_pct),
                }
                for i in order.items
            ],
        }


def h_cancel_order(inp: CancelOrderIn, role: str, request_id: str | None) -> dict:
    _require(role, "order:cancel")
    cached = _idem_get(inp.idempotency_key)
    if cached:
        return {**cached, "idempotent_replay": True}
    with session_scope() as s:
        order = OrderService(s).cancel_order(
            order_number=inp.order_number, actor=role, request_id=request_id
        )
        out = {"order_id": order.id, "order_number": order.order_number, "status": order.status}
        _idem_put(inp.idempotency_key, out)
        return out


def h_shipping_options(inp: ShippingOptsIn, role: str, request_id: str | None) -> dict:
    _require(role, "shipping:read")
    return {"options": SHIPPING_OPTIONS, "order_number": inp.order_number}


def h_create_shipment(inp: CreateShipmentIn, role: str, request_id: str | None) -> dict:
    _require(role, "shipping:write")
    cached = _idem_get(inp.idempotency_key)
    if cached:
        return {**cached, "idempotent_replay": True}
    # sales lacks shipping:write — admin only; sales gets unauthorized (by design)
    opt = next((o for o in SHIPPING_OPTIONS if o["code"] == inp.option_code.upper()), None)
    if not opt:
        raise ToolError("INVALID_SHIPPING_OPTION", f"Unknown option {inp.option_code}")
    with session_scope() as s:
        order = OrderService(s).get_order(order_number=inp.order_number)
    tracking = f"TRK{uuid.uuid4().hex[:12].upper()}"
    shipment = {
        "tracking_number": tracking,
        "order_number": order.order_number,
        "option": opt,
        "status": "created",
    }
    _SHIPMENTS[tracking] = shipment
    _idem_put(inp.idempotency_key, shipment)
    return shipment


def h_track_shipment(inp: TrackShipmentIn, role: str, request_id: str | None) -> dict:
    _require(role, "shipping:read")
    row = _SHIPMENTS.get(inp.tracking_number)
    if not row:
        raise ToolError("SHIPMENT_NOT_FOUND", "Unknown tracking number", http_status=404)
    return row


def h_search_policy(inp: PolicySearchIn, role: str, request_id: str | None) -> dict:
    _require(role, "policy:read")
    # Prefer RAG retrieval; fall back to static pack
    try:
        from app.rag.service import retrieve_dict

        with session_scope() as s:
            out = retrieve_dict(s, inp.query, top_k=4, min_score=0.10)
        if out["count"]:
            return {
                "policies": [
                    {
                        "id": c["document_id"],
                        "title": c["title"],
                        "body": c["text"],
                        "source": c["source"],
                        "score": c["score"],
                        "chunk_index": c["chunk_index"],
                    }
                    for c in out["citations"]
                ],
                "retrieval": "rag",
            }
    except Exception as e:  # pragma: no cover  # noqa: BLE001
        logger.warning("rag_fallback error=%s", e)
    q = inp.query.lower()
    hits = [
        p
        for p in POLICIES
        if q in p["title"].lower() or q in p["body"].lower() or any(q in t for t in p["tags"])
    ]
    return {"policies": hits, "retrieval": "static"}


TOOLS: dict[str, ToolSpec] = {}


def _reg(spec: ToolSpec) -> None:
    TOOLS[spec.name] = spec


def _bootstrap() -> None:
    if TOOLS:
        return
    pairs = [
        ("get_customer", "Fetch customer profile", "customer:read", False, True, CustomerCodeIn, h_get_customer),
        (
            "get_customer_contract",
            "Fetch active customer contract",
            "customer:read",
            False,
            True,
            CustomerCodeIn,
            h_get_contract,
        ),
        ("check_credit", "Check credit for amount", "customer:read", False, True, CreditIn, h_check_credit),
        ("search_products", "Search products by text", "product:read", False, True, SearchIn, h_search_products),
        ("get_product", "Get product by SKU", "product:read", False, True, SkuIn, h_get_product),
        ("check_inventory", "Check stock levels", "inventory:read", False, True, SkuIn, h_check_inventory),
        (
            "reserve_inventory",
            "Reserve stock",
            "inventory:reserve",
            True,
            True,
            QtySkuIn,
            h_reserve_inventory,
        ),
        (
            "release_inventory",
            "Release reserved stock",
            "inventory:reserve",
            True,
            True,
            QtySkuIn,
            h_release_inventory,
        ),
        ("get_price", "Get deterministic price quote", "pricing:read", False, True, PriceIn, h_get_price),
        (
            "calculate_discount",
            "Calculate discount breakdown",
            "pricing:read",
            False,
            True,
            PriceIn,
            h_calculate_discount,
        ),
        ("create_order", "Create order (idempotent)", "order:create", True, True, CreateOrderIn, h_create_order),
        ("get_order", "Get order by number/id", "order:read", False, True, OrderRefIn, h_get_order),
        ("cancel_order", "Cancel order and release stock", "order:cancel", True, True, CancelOrderIn, h_cancel_order),
        (
            "get_shipping_options",
            "List shipping options",
            "shipping:read",
            False,
            True,
            ShippingOptsIn,
            h_shipping_options,
        ),
        (
            "create_shipment",
            "Create shipment for order",
            "shipping:write",
            True,
            True,
            CreateShipmentIn,
            h_create_shipment,
        ),
        ("track_shipment", "Track shipment", "shipping:read", False, True, TrackShipmentIn, h_track_shipment),
        ("search_policy", "Search enterprise policies", "policy:read", False, True, PolicySearchIn, h_search_policy),
    ]
    for name, desc, perm, side, idem, model, handler in pairs:
        _reg(
            ToolSpec(
                name=name,
                description=desc,
                permission=perm,
                side_effects=side,
                idempotent=idem,
                input_model=model,
                handler=handler,  # type: ignore[arg-type]
            )
        )


_bootstrap()


def list_tools() -> list[dict[str, Any]]:
    return [
        {
            "name": t.name,
            "description": t.description,
            "permission": t.permission,
            "side_effects": t.side_effects,
            "idempotent": t.idempotent,
            "input_schema": t.input_model.model_json_schema(),
        }
        for t in TOOLS.values()
    ]


def call_tool(
    name: str,
    arguments: dict[str, Any],
    *,
    role: str = "sales",
    request_id: str | None = None,
) -> dict[str, Any]:
    """Execute a named MCP tool. Returns structured result or raises ToolError."""
    _bootstrap()
    spec = TOOLS.get(name)
    if not spec:
        raise ToolError("UNKNOWN_TOOL", f"Unknown tool {name!r}", http_status=404)
    try:
        inp = spec.input_model.model_validate(arguments or {})
    except ValidationError as e:
        raise ToolError("INVALID_INPUT", e.errors().__repr__(), http_status=422) from e
    try:
        result = spec.handler(inp, role, request_id)
    except ServiceError as e:
        status = 404 if "NOT_FOUND" in e.code else 409 if e.code == "INSUFFICIENT_STOCK" else 400
        raise ToolError(e.code, e.message, http_status=status) from e
    logger.info(
        "mcp_tool name=%s role=%s request_id=%s side_effects=%s",
        name,
        role,
        request_id,
        spec.side_effects,
    )
    return {
        "tool": name,
        "status": "ok",
        "request_id": request_id,
        "result": result,
    }
