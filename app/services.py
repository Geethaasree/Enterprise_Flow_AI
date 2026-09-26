"""Deterministic business services (Phase 4). LLM must not own these decisions."""

from __future__ import annotations

from dataclasses import dataclass
from decimal import Decimal

from sqlalchemy.orm import Session

from app import models as m
from app.repositories import AuditRepo, CustomerRepo, InventoryRepo, OrderRepo, ProductRepo


class ServiceError(Exception):
    def __init__(self, code: str, message: str):
        super().__init__(message)
        self.code = code
        self.message = message


@dataclass
class InventoryView:
    sku: str
    product_name: str
    on_hand: int
    reserved: int
    available: int
    warehouse: str


@dataclass
class PriceQuote:
    sku: str
    quantity: int
    unit_price: Decimal
    discount_pct: Decimal
    line_total: Decimal


class CustomerService:
    def __init__(self, session: Session):
        self.repo = CustomerRepo(session)
        self.audit = AuditRepo(session)

    def get_by_code(self, code: str) -> m.Customer:
        row = self.repo.get_by_code(code)
        if not row:
            raise ServiceError("CUSTOMER_NOT_FOUND", f"Customer {code!r} not found")
        return row

    def get_contract(self, customer_code: str) -> m.CustomerContract:
        cust = self.get_by_code(customer_code)
        contract = self.repo.active_contract(cust.id)
        if not contract:
            raise ServiceError("CONTRACT_NOT_FOUND", f"No active contract for {customer_code}")
        return contract

    def credit_ok(self, customer_code: str, amount: Decimal) -> bool:
        cust = self.get_by_code(customer_code)
        return (cust.credit_used + amount) <= cust.credit_limit


class ProductService:
    def __init__(self, session: Session):
        self.repo = ProductRepo(session)

    def get_by_sku(self, sku: str) -> m.Product:
        row = self.repo.get_by_sku(sku)
        if not row or not row.active:
            raise ServiceError("PRODUCT_NOT_FOUND", f"Product {sku!r} not found")
        return row

    def search(self, q: str) -> list[m.Product]:
        return self.repo.search(q)


class InventoryService:
    def __init__(self, session: Session):
        self.repo = InventoryRepo(session)
        self.products = ProductRepo(session)
        self.audit = AuditRepo(session)

    def view(self, sku: str) -> InventoryView:
        inv = self.repo.get_for_sku(sku)
        if not inv or not inv.product:
            raise ServiceError("INVENTORY_NOT_FOUND", f"No inventory for {sku!r}")
        return InventoryView(
            sku=inv.product.sku,
            product_name=inv.product.name,
            on_hand=inv.on_hand,
            reserved=inv.reserved,
            available=inv.available,
            warehouse=inv.warehouse,
        )

    def reserve(self, sku: str, qty: int, *, actor: str | None = None, request_id: str | None = None) -> InventoryView:
        if qty <= 0:
            raise ServiceError("INVALID_QTY", "Quantity must be positive")
        inv = self.repo.get_for_sku(sku)
        if not inv or not inv.product:
            raise ServiceError("INVENTORY_NOT_FOUND", f"No inventory for {sku!r}")
        if inv.available < qty:
            raise ServiceError(
                "INSUFFICIENT_STOCK",
                f"Need {qty}, available {inv.available} for {sku}",
            )
        inv.reserved += qty
        self.audit.write(
            "inventory.reserve",
            actor=actor,
            entity_type="inventory",
            entity_id=inv.id,
            request_id=request_id,
            detail=f"sku={sku} qty={qty}",
        )
        return self.view(sku)

    def release(self, sku: str, qty: int, *, actor: str | None = None, request_id: str | None = None) -> InventoryView:
        if qty <= 0:
            raise ServiceError("INVALID_QTY", "Quantity must be positive")
        inv = self.repo.get_for_sku(sku)
        if not inv or not inv.product:
            raise ServiceError("INVENTORY_NOT_FOUND", f"No inventory for {sku!r}")
        if inv.reserved < qty:
            raise ServiceError("RESERVE_UNDERFLOW", f"Cannot release {qty}; reserved={inv.reserved}")
        inv.reserved -= qty
        self.audit.write(
            "inventory.release",
            actor=actor,
            entity_type="inventory",
            entity_id=inv.id,
            request_id=request_id,
            detail=f"sku={sku} qty={qty}",
        )
        return self.view(sku)


class PricingService:
    """Deterministic pricing — never leave final math to the LLM."""

    def __init__(self, session: Session):
        self.session = session
        self.products = ProductService(session)
        self.customers = CustomerService(session)

    def quote(self, sku: str, quantity: int, customer_code: str | None = None) -> PriceQuote:
        if quantity <= 0:
            raise ServiceError("INVALID_QTY", "Quantity must be positive")
        product = self.products.get_by_sku(sku)
        discount = Decimal(0)
        if customer_code:
            try:
                contract = self.customers.get_contract(customer_code)
                discount = max(discount, Decimal(contract.discount_pct))
            except ServiceError:
                pass
        # volume tiers from pricing_conditions
        from sqlalchemy import select

        conds = list(
            self.session.scalars(
                select(m.PricingCondition).where(
                    m.PricingCondition.active.is_(True),
                    m.PricingCondition.product_id == product.id,
                    m.PricingCondition.min_qty <= quantity,
                )
            )
        )
        for c in conds:
            discount = max(discount, Decimal(c.discount_pct))
        unit = Decimal(product.unit_price)
        line = (unit * quantity * (Decimal(100) - discount) / Decimal(100)).quantize(Decimal("0.01"))
        return PriceQuote(
            sku=product.sku,
            quantity=quantity,
            unit_price=unit,
            discount_pct=discount,
            line_total=line,
        )


class OrderService:
    def __init__(self, session: Session):
        self.session = session
        self.orders = OrderRepo(session)
        self.customers = CustomerService(session)
        self.pricing = PricingService(session)
        self.inventory = InventoryService(session)
        self.audit = AuditRepo(session)

    def create_draft(
        self,
        customer_code: str,
        sku: str,
        quantity: int,
        *,
        order_number: str,
        reserve: bool = False,
        actor: str | None = None,
        workflow_id: str | None = None,
        request_id: str | None = None,
    ) -> m.Order:
        existing = self.orders.get_by_number(order_number)
        if existing:
            return existing  # idempotent on order_number

        customer = self.customers.get_by_code(customer_code)
        quote = self.pricing.quote(sku, quantity, customer_code)
        product = ProductService(self.session).get_by_sku(sku)

        if reserve:
            self.inventory.reserve(sku, quantity, actor=actor, request_id=request_id)

        order = m.Order(
            order_number=order_number,
            customer_id=customer.id,
            status="reserved" if reserve else "draft",
            currency=product.currency,
            subtotal=(quote.unit_price * quantity).quantize(Decimal("0.01")),
            discount_total=(quote.unit_price * quantity - quote.line_total).quantize(Decimal("0.01")),
            total=quote.line_total,
            created_by=actor,
            workflow_id=workflow_id,
        )
        order.items.append(
            m.OrderItem(
                product_id=product.id,
                sku=product.sku,
                quantity=quantity,
                unit_price=quote.unit_price,
                discount_pct=quote.discount_pct,
                line_total=quote.line_total,
            )
        )
        self.orders.add(order)
        self.audit.write(
            "order.create",
            actor=actor,
            entity_type="order",
            entity_id=order.id,
            request_id=request_id,
            workflow_id=workflow_id,
            detail=f"{order_number} {sku} x{quantity}",
        )
        return order

    def get_order(self, *, order_number: str | None = None, order_id: str | None = None) -> m.Order:
        row = None
        if order_number:
            row = self.orders.get_by_number(order_number)
        elif order_id:
            row = self.orders.get(order_id)
        if not row:
            raise ServiceError("ORDER_NOT_FOUND", "Order not found")
        return row

    def cancel_order(
        self,
        *,
        order_number: str,
        actor: str | None = None,
        request_id: str | None = None,
    ) -> m.Order:
        order = self.get_order(order_number=order_number)
        if order.status == "cancelled":
            return order  # idempotent
        if order.status not in ("draft", "reserved", "pending_approval"):
            raise ServiceError("ORDER_NOT_CANCELLABLE", f"Cannot cancel status={order.status}")
        if order.status == "reserved":
            for item in order.items:
                self.inventory.release(item.sku, item.quantity, actor=actor, request_id=request_id)
        order.status = "cancelled"
        self.audit.write(
            "order.cancel",
            actor=actor,
            entity_type="order",
            entity_id=order.id,
            request_id=request_id,
            detail=order_number,
        )
        return order
