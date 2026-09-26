"""API-led connectivity: Experience → Process → System → SAP (simulators)."""

from __future__ import annotations

import logging
import uuid
from typing import Any

from fastapi import APIRouter, Header, Query
from fastapi.responses import JSONResponse
from pydantic import BaseModel, Field

from app.db import session_scope
from app.integration.sap import SapError, SapSimulator

logger = logging.getLogger(__name__)

# --- SAP System Simulator ---
sap_router = APIRouter(prefix="/sap", tags=["sap-simulator"])


def _sap_fail(x_sap_fail: str | None, fail: bool) -> JSONResponse | None:
    if fail or (x_sap_fail and x_sap_fail.lower() in {"1", "true", "yes"}):
        return JSONResponse(
            {"status": "error", "code": "SAP_UNAVAILABLE", "message": "Simulated SAP outage"},
            status_code=503,
        )
    return None


@sap_router.get("/customers")
def sap_customers(
    x_sap_fail: str | None = Header(default=None, alias="X-SAP-Fail"),
    fail: bool = Query(default=False),
):
    if err := _sap_fail(x_sap_fail, fail):
        return err
    with session_scope() as s:
        return {"status": "ok", "results": SapSimulator(s).list_customers()}


@sap_router.get("/customers/{kunnr}")
def sap_customer(
    kunnr: str,
    x_sap_fail: str | None = Header(default=None, alias="X-SAP-Fail"),
    fail: bool = Query(default=False),
):
    if err := _sap_fail(x_sap_fail, fail):
        return err
    try:
        with session_scope() as s:
            return {"status": "ok", "customer": SapSimulator(s).get_customer(kunnr)}
    except SapError as e:
        return JSONResponse(
            {"status": "error", "code": e.code, "message": e.message}, status_code=e.http_status
        )


@sap_router.get("/materials/{matnr}")
def sap_material(matnr: str, fail: bool = Query(default=False), x_sap_fail: str | None = Header(default=None, alias="X-SAP-Fail")):
    if err := _sap_fail(x_sap_fail, fail):
        return err
    try:
        with session_scope() as s:
            return {"status": "ok", "material": SapSimulator(s).get_material(matnr)}
    except SapError as e:
        return JSONResponse(
            {"status": "error", "code": e.code, "message": e.message}, status_code=e.http_status
        )


@sap_router.get("/stock/{matnr}")
def sap_stock(matnr: str, fail: bool = Query(default=False), x_sap_fail: str | None = Header(default=None, alias="X-SAP-Fail")):
    if err := _sap_fail(x_sap_fail, fail):
        return err
    try:
        with session_scope() as s:
            return {"status": "ok", "stock": SapSimulator(s).get_stock(matnr)}
    except SapError as e:
        return JSONResponse(
            {"status": "error", "code": e.code, "message": e.message}, status_code=e.http_status
        )


class SapOrderIn(BaseModel):
    KUNNR: str = "ACME"
    MATNR: str = "LAPTOP-PRO-14"
    KWMENG: int = Field(default=1, gt=0)
    VBELN: str | None = None
    RESERVE: bool = True


@sap_router.post("/orders")
def sap_create_order(
    body: SapOrderIn,
    fail: bool = Query(default=False),
    x_sap_fail: str | None = Header(default=None, alias="X-SAP-Fail"),
):
    if err := _sap_fail(x_sap_fail, fail):
        return err
    try:
        with session_scope() as s:
            order = SapSimulator(s).create_order(
                kunnr=body.KUNNR,
                matnr=body.MATNR,
                kwmeng=body.KWMENG,
                vbeln=body.VBELN,
                reserve=body.RESERVE,
            )
            return {"status": "ok", "order": order}
    except SapError as e:
        return JSONResponse(
            {"status": "error", "code": e.code, "message": e.message}, status_code=e.http_status
        )


@sap_router.get("/orders/{vbeln}")
def sap_get_order(vbeln: str, fail: bool = Query(default=False), x_sap_fail: str | None = Header(default=None, alias="X-SAP-Fail")):
    if err := _sap_fail(x_sap_fail, fail):
        return err
    try:
        with session_scope() as s:
            return {"status": "ok", "order": SapSimulator(s).get_order(vbeln)}
    except SapError as e:
        return JSONResponse(
            {"status": "error", "code": e.code, "message": e.message}, status_code=e.http_status
        )


# --- System API (canonical enterprise DTOs over SAP) ---
system_router = APIRouter(prefix="/system", tags=["system-api"])


def sap_to_customer(sap: dict) -> dict:
    return {
        "customer_code": sap["KUNNR"],
        "name": sap["NAME1"],
        "country": sap.get("LAND1"),
        "active": sap.get("LOEVM") != "X",
        "credit_limit": sap.get("KLIMK"),
        "credit_used": sap.get("SKFOR"),
        "source": "sap",
    }


def sap_to_product(sap: dict) -> dict:
    return {
        "sku": sap["MATNR"],
        "name": sap["MAKTX"],
        "category": sap.get("MTART"),
        "unit_price": sap.get("STPRS"),
        "currency": sap.get("WAERS"),
        "source": "sap",
    }


def sap_to_inventory(sap: dict) -> dict:
    return {
        "sku": sap["MATNR"],
        "warehouse": sap.get("WERKS"),
        "on_hand": sap.get("LABST"),
        "reserved": sap.get("INSME"),
        "available": sap.get("VERME"),
        "source": "sap",
    }


def sap_to_order(sap: dict) -> dict:
    return {
        "order_number": sap["VBELN"],
        "customer_code": sap.get("KUNNR"),
        "status": sap.get("GBSTK"),
        "total": sap.get("NETWR"),
        "currency": sap.get("WAERK"),
        "items": [
            {
                "sku": i["MATNR"],
                "quantity": i["KWMENG"],
                "unit_price": i.get("NETPR"),
                "line_total": i.get("NETWR"),
            }
            for i in sap.get("ITEMS") or []
        ],
        "source": "sap",
    }


@system_router.get("/customers/{code}")
def system_customer(code: str, fail: bool = False):
    if err := _sap_fail(None, fail):
        return err
    try:
        with session_scope() as s:
            raw = SapSimulator(s).get_customer(code)
            return {"status": "ok", "layer": "system", "customer": sap_to_customer(raw)}
    except SapError as e:
        return JSONResponse(
            {"status": "error", "layer": "system", "code": e.code, "message": e.message},
            status_code=e.http_status,
        )


@system_router.get("/products/{sku}")
def system_product(sku: str, fail: bool = False):
    try:
        with session_scope() as s:
            raw = SapSimulator(s).get_material(sku)
            return {"status": "ok", "layer": "system", "product": sap_to_product(raw)}
    except SapError as e:
        return JSONResponse(
            {"status": "error", "layer": "system", "code": e.code, "message": e.message},
            status_code=e.http_status,
        )


@system_router.get("/inventory/{sku}")
def system_inventory(sku: str, fail: bool = False):
    try:
        with session_scope() as s:
            raw = SapSimulator(s).get_stock(sku)
            return {"status": "ok", "layer": "system", "inventory": sap_to_inventory(raw)}
    except SapError as e:
        return JSONResponse(
            {"status": "error", "layer": "system", "code": e.code, "message": e.message},
            status_code=e.http_status,
        )


class SystemOrderIn(BaseModel):
    customer_code: str = "ACME"
    sku: str = "LAPTOP-PRO-14"
    quantity: int = Field(default=1, gt=0)
    order_number: str | None = None
    reserve: bool = True


@system_router.post("/orders")
def system_create_order(body: SystemOrderIn, fail: bool = False):
    if err := _sap_fail(None, fail):
        return err
    try:
        with session_scope() as s:
            sim = SapSimulator(s)
            # validate customer + stock via SAP shapes first
            sim.get_customer(body.customer_code)
            stock = sim.get_stock(body.sku)
            if int(stock.get("VERME") or 0) < body.quantity and body.reserve:
                return JSONResponse(
                    {
                        "status": "error",
                        "layer": "system",
                        "code": "INSUFFICIENT_STOCK",
                        "message": f"Available {stock.get('VERME')} < {body.quantity}",
                    },
                    status_code=409,
                )
            raw = sim.create_order(
                kunnr=body.customer_code,
                matnr=body.sku,
                kwmeng=body.quantity,
                vbeln=body.order_number,
                reserve=body.reserve,
            )
            return {"status": "ok", "layer": "system", "order": sap_to_order(raw)}
    except SapError as e:
        return JSONResponse(
            {"status": "error", "layer": "system", "code": e.code, "message": e.message},
            status_code=e.http_status,
        )


@system_router.get("/orders/{order_number}")
def system_get_order(order_number: str):
    try:
        with session_scope() as s:
            raw = SapSimulator(s).get_order(order_number)
            return {"status": "ok", "layer": "system", "order": sap_to_order(raw)}
    except SapError as e:
        return JSONResponse(
            {"status": "error", "layer": "system", "code": e.code, "message": e.message},
            status_code=e.http_status,
        )


# --- Process API (orchestration) ---
process_router = APIRouter(prefix="/process", tags=["process-api"])


class ProcessOrderIn(BaseModel):
    customer_code: str = "ACME"
    sku: str = "LAPTOP-PRO-14"
    quantity: int = Field(default=1, gt=0)
    order_number: str | None = None


def _process_create_order(body: ProcessOrderIn) -> dict[str, Any]:
    """Orchestrate: customer check → stock → create (via system/SAP mapping)."""
    steps: list[str] = []
    with session_scope() as s:
        sim = SapSimulator(s)
        cust = sap_to_customer(sim.get_customer(body.customer_code))
        steps.append("system.customer")
        prod = sap_to_product(sim.get_material(body.sku))
        steps.append("system.product")
        inv = sap_to_inventory(sim.get_stock(body.sku))
        steps.append("system.inventory")
        if int(inv.get("available") or 0) < body.quantity:
            raise SapError(
                "PROCESS_STOCK",
                f"Insufficient stock available={inv.get('available')} need={body.quantity}",
                409,
            )
        onum = body.order_number or f"PROC-{uuid.uuid4().hex[:10].upper()}"
        order = sap_to_order(
            sim.create_order(
                kunnr=body.customer_code,
                matnr=body.sku,
                kwmeng=body.quantity,
                vbeln=onum,
                reserve=True,
            )
        )
        steps.append("system.order_create")
        return {
            "status": "ok",
            "layer": "process",
            "steps": steps,
            "customer": cust,
            "product": prod,
            "inventory_before_create": inv,
            "order": order,
        }


@process_router.post("/orders")
def process_create_order(body: ProcessOrderIn, fail: bool = False):
    if err := _sap_fail(None, fail):
        return err
    try:
        return _process_create_order(body)
    except SapError as e:
        return JSONResponse(
            {"status": "error", "layer": "process", "code": e.code, "message": e.message, "steps": []},
            status_code=e.http_status,
        )


@process_router.get("/orders/{order_number}")
def process_get_order(order_number: str):
    try:
        with session_scope() as s:
            order = sap_to_order(SapSimulator(s).get_order(order_number))
            return {"status": "ok", "layer": "process", "order": order}
    except SapError as e:
        return JSONResponse(
            {"status": "error", "layer": "process", "code": e.code, "message": e.message},
            status_code=e.http_status,
        )


# --- Experience API (channel-facing) ---
experience_router = APIRouter(prefix="/experience", tags=["experience-api"])


class ExperienceOrderIn(BaseModel):
    customer: str = Field(default="ACME", description="Customer code")
    product: str = Field(default="LAPTOP-PRO-14", description="SKU")
    qty: int = Field(default=1, gt=0, le=10000)


@experience_router.post("/orders")
def experience_create_order(body: ExperienceOrderIn):
    """Channel DTO → Process API orchestration."""
    try:
        result = _process_create_order(
            ProcessOrderIn(
                customer_code=body.customer.upper(),
                sku=body.product.upper(),
                quantity=body.qty,
            )
        )
        order = result["order"]
        return {
            "status": "ok",
            "layer": "experience",
            "message": f"Order {order['order_number']} placed for {body.customer}",
            "order_id": order["order_number"],
            "total": order.get("total"),
            "currency": order.get("currency") or "USD",
            "process_steps": result.get("steps"),
            "trace": {
                "experience": True,
                "process": True,
                "system": True,
                "sap": True,
            },
        }
    except SapError as e:
        return JSONResponse(
            {
                "status": "error",
                "layer": "experience",
                "code": e.code,
                "message": e.message,
            },
            status_code=e.http_status,
        )


@experience_router.get("/orders/{order_id}")
def experience_get_order(order_id: str):
    try:
        with session_scope() as s:
            order = sap_to_order(SapSimulator(s).get_order(order_id))
            return {
                "status": "ok",
                "layer": "experience",
                "order_id": order["order_number"],
                "customer": order.get("customer_code"),
                "total": order.get("total"),
                "items": order.get("items"),
            }
    except SapError as e:
        return JSONResponse(
            {"status": "error", "layer": "experience", "code": e.code, "message": e.message},
            status_code=e.http_status,
        )


@experience_router.get("/catalog/{sku}")
def experience_catalog(sku: str):
    try:
        with session_scope() as s:
            sim = SapSimulator(s)
            p = sap_to_product(sim.get_material(sku))
            inv = sap_to_inventory(sim.get_stock(sku))
            return {
                "status": "ok",
                "layer": "experience",
                "sku": p["sku"],
                "name": p["name"],
                "price": p["unit_price"],
                "in_stock": int(inv.get("available") or 0) > 0,
                "available": inv.get("available"),
            }
    except SapError as e:
        return JSONResponse(
            {"status": "error", "layer": "experience", "code": e.code, "message": e.message},
            status_code=e.http_status,
        )
