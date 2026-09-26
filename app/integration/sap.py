"""SAP-style field mapping + simulator helpers.

# ponytail: mock SAP shapes only — not real RFC/OData.
"""

from __future__ import annotations

from decimal import Decimal
from typing import Any

from sqlalchemy.orm import Session

from app.services import (
    CustomerService,
    InventoryService,
    OrderService,
    ProductService,
    ServiceError,
)


class SapError(Exception):
    def __init__(self, code: str, message: str, http_status: int = 400):
        self.code = code
        self.message = message
        self.http_status = http_status
        super().__init__(message)


def customer_to_sap(c) -> dict[str, Any]:
    return {
        "KUNNR": c.code,
        "NAME1": c.name,
        "LAND1": c.country,
        "LOEVM": "" if c.status == "active" else "X",
        "KLIMK": f"{Decimal(c.credit_limit):.2f}",
        "SKFOR": f"{Decimal(c.credit_used):.2f}",
        "customer_id": c.id,
    }


def material_to_sap(p) -> dict[str, Any]:
    return {
        "MATNR": p.sku,
        "MAKTX": p.name,
        "MTART": p.category,
        "STPRS": f"{Decimal(p.unit_price):.2f}",
        "WAERS": p.currency,
        "product_id": p.id,
    }


def stock_to_sap(v) -> dict[str, Any]:
    return {
        "MATNR": v.sku,
        "WERKS": v.warehouse,
        "LABST": v.on_hand,
        "INSME": v.reserved,
        "VERME": v.available,
    }


def order_to_sap(o, customer_code: str | None = None) -> dict[str, Any]:
    items = []
    for it in o.items or []:
        items.append(
            {
                "POSNR": str(len(items) + 1).zfill(6),
                "MATNR": it.sku,
                "KWMENG": it.quantity,
                "NETPR": f"{Decimal(it.unit_price):.2f}",
                "NETWR": f"{Decimal(it.line_total):.2f}",
            }
        )
    kunnr = customer_code
    if not kunnr and getattr(o, "customer", None) is not None:
        kunnr = o.customer.code
    return {
        "VBELN": o.order_number,
        "KUNNR": kunnr,
        "AUART": "OR",
        "GBSTK": (o.status or "A")[:10].upper(),
        "NETWR": f"{Decimal(o.total):.2f}",
        "WAERK": o.currency,
        "ITEMS": items,
        "order_id": o.id,
    }


class SapSimulator:
    """System-of-record face using enterprise services underneath."""

    def __init__(self, session: Session):
        self.s = session
        self.customers = CustomerService(session)
        self.products = ProductService(session)
        self.inventory = InventoryService(session)
        self.orders = OrderService(session)

    def get_customer(self, kunnr: str) -> dict[str, Any]:
        try:
            return customer_to_sap(self.customers.get_by_code(kunnr))
        except ServiceError as e:
            raise SapError("SAP_CUSTOMER_NOT_FOUND", e.message, 404) from e

    def list_customers(self) -> list[dict[str, Any]]:
        # seed has ACME — expose via get
        try:
            return [self.get_customer("ACME")]
        except SapError:
            return []

    def get_material(self, matnr: str) -> dict[str, Any]:
        try:
            return material_to_sap(self.products.get_by_sku(matnr))
        except ServiceError as e:
            raise SapError("SAP_MATERIAL_NOT_FOUND", e.message, 404) from e

    def get_stock(self, matnr: str) -> dict[str, Any]:
        try:
            return stock_to_sap(self.inventory.view(matnr))
        except ServiceError as e:
            raise SapError("SAP_STOCK_NOT_FOUND", e.message, 404) from e

    def create_order(
        self,
        *,
        kunnr: str,
        matnr: str,
        kwmeng: int,
        vbeln: str | None = None,
        reserve: bool = True,
    ) -> dict[str, Any]:
        import uuid

        onum = vbeln or f"SAP{uuid.uuid4().hex[:10].upper()}"
        try:
            o = self.orders.create_draft(
                kunnr,
                matnr,
                kwmeng,
                order_number=onum,
                reserve=reserve,
                actor="sap",
            )
            return order_to_sap(o, customer_code=kunnr)
        except ServiceError as e:
            raise SapError("SAP_ORDER_FAILED", e.message, 409) from e

    def get_order(self, vbeln: str) -> dict[str, Any]:
        try:
            o = self.orders.get_order(order_number=vbeln)
            # resolve customer code
            code = None
            if o.customer_id:
                from app import models as m

                cust = self.s.get(m.Customer, o.customer_id)
                code = cust.code if cust else None
            return order_to_sap(o, customer_code=code)
        except ServiceError as e:
            raise SapError("SAP_ORDER_NOT_FOUND", e.message, 404) from e
