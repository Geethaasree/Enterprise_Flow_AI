"""Enterprise data HTTP API (Phase 4)."""

from __future__ import annotations

import logging

from fastapi import APIRouter
from fastapi.responses import JSONResponse
from pydantic import BaseModel, Field

from app.db import session_scope
from app.seed import seed_enterprise
from app.services import (
    CustomerService,
    InventoryService,
    OrderService,
    PricingService,
    ProductService,
    ServiceError,
)

logger = logging.getLogger(__name__)
router = APIRouter(prefix="/enterprise", tags=["enterprise"])


class ReserveBody(BaseModel):
    sku: str
    quantity: int = Field(gt=0)


class OrderBody(BaseModel):
    customer_code: str = "ACME"
    sku: str = "LAPTOP-PRO-14"
    quantity: int = Field(default=1, gt=0)
    order_number: str
    reserve: bool = False


@router.post("/seed")
def post_seed(reset: bool = False):
    with session_scope() as s:
        result = seed_enterprise(s, reset=reset)
    return {"status": "ok", **result}


@router.get("/customers/{code}")
def get_customer(code: str):
    try:
        with session_scope() as s:
            c = CustomerService(s).get_by_code(code)
            contract = CustomerService(s).repo.active_contract(c.id)
            return {
                "code": c.code,
                "name": c.name,
                "status": c.status,
                "credit_limit": str(c.credit_limit),
                "credit_used": str(c.credit_used),
                "contract": None
                if not contract
                else {
                    "number": contract.contract_number,
                    "discount_pct": str(contract.discount_pct),
                    "payment_terms": contract.payment_terms,
                },
            }
    except ServiceError as e:
        return JSONResponse({"status": "error", "code": e.code, "message": e.message}, status_code=404)


@router.get("/products/{sku}")
def get_product(sku: str):
    try:
        with session_scope() as s:
            p = ProductService(s).get_by_sku(sku)
            return {
                "sku": p.sku,
                "name": p.name,
                "unit_price": str(p.unit_price),
                "currency": p.currency,
                "category": p.category,
            }
    except ServiceError as e:
        return JSONResponse({"status": "error", "code": e.code, "message": e.message}, status_code=404)


@router.get("/inventory/{sku}")
def get_inventory(sku: str):
    try:
        with session_scope() as s:
            v = InventoryService(s).view(sku)
            return {
                "sku": v.sku,
                "product_name": v.product_name,
                "on_hand": v.on_hand,
                "reserved": v.reserved,
                "available": v.available,
                "warehouse": v.warehouse,
            }
    except ServiceError as e:
        return JSONResponse({"status": "error", "code": e.code, "message": e.message}, status_code=404)


@router.post("/inventory/reserve")
def post_reserve(body: ReserveBody):
    try:
        with session_scope() as s:
            v = InventoryService(s).reserve(body.sku, body.quantity, actor="api")
            return {
                "sku": v.sku,
                "on_hand": v.on_hand,
                "reserved": v.reserved,
                "available": v.available,
            }
    except ServiceError as e:
        code = 409 if e.code == "INSUFFICIENT_STOCK" else 400
        return JSONResponse({"status": "error", "code": e.code, "message": e.message}, status_code=code)


@router.post("/inventory/release")
def post_release(body: ReserveBody):
    try:
        with session_scope() as s:
            v = InventoryService(s).release(body.sku, body.quantity, actor="api")
            return {
                "sku": v.sku,
                "on_hand": v.on_hand,
                "reserved": v.reserved,
                "available": v.available,
            }
    except ServiceError as e:
        return JSONResponse({"status": "error", "code": e.code, "message": e.message}, status_code=400)


@router.get("/pricing/quote")
def quote(sku: str, quantity: int = 1, customer_code: str | None = "ACME"):
    try:
        with session_scope() as s:
            q = PricingService(s).quote(sku, quantity, customer_code)
            return {
                "sku": q.sku,
                "quantity": q.quantity,
                "unit_price": str(q.unit_price),
                "discount_pct": str(q.discount_pct),
                "line_total": str(q.line_total),
            }
    except ServiceError as e:
        return JSONResponse({"status": "error", "code": e.code, "message": e.message}, status_code=400)


@router.post("/orders")
def create_order(body: OrderBody):
    try:
        with session_scope() as s:
            order = OrderService(s).create_draft(
                body.customer_code,
                body.sku,
                body.quantity,
                order_number=body.order_number,
                reserve=body.reserve,
                actor="api",
            )
            return {
                "order_number": order.order_number,
                "status": order.status,
                "total": str(order.total),
                "discount_total": str(order.discount_total),
                "items": [
                    {
                        "sku": i.sku,
                        "quantity": i.quantity,
                        "line_total": str(i.line_total),
                        "discount_pct": str(i.discount_pct),
                    }
                    for i in order.items
                ],
            }
    except ServiceError as e:
        code = 409 if e.code == "INSUFFICIENT_STOCK" else 400
        return JSONResponse({"status": "error", "code": e.code, "message": e.message}, status_code=code)
