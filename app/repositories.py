"""Repository helpers — thin SQLAlchemy access."""

from __future__ import annotations

from sqlalchemy import select
from sqlalchemy.orm import Session, joinedload

from app import models as m


class CustomerRepo:
    def __init__(self, session: Session):
        self.s = session

    def get_by_code(self, code: str) -> m.Customer | None:
        return self.s.scalar(select(m.Customer).where(m.Customer.code == code.upper()))

    def get(self, customer_id: str) -> m.Customer | None:
        return self.s.get(m.Customer, customer_id)

    def list(self, limit: int = 50) -> list[m.Customer]:
        return list(self.s.scalars(select(m.Customer).limit(limit)))

    def active_contract(self, customer_id: str) -> m.CustomerContract | None:
        return self.s.scalar(
            select(m.CustomerContract)
            .where(m.CustomerContract.customer_id == customer_id, m.CustomerContract.active.is_(True))
            .limit(1)
        )


class ProductRepo:
    def __init__(self, session: Session):
        self.s = session

    def get_by_sku(self, sku: str) -> m.Product | None:
        return self.s.scalar(select(m.Product).where(m.Product.sku == sku.upper()))

    def search(self, q: str, limit: int = 20) -> list[m.Product]:
        like = f"%{q}%"
        return list(
            self.s.scalars(
                select(m.Product)
                .where(m.Product.active.is_(True))
                .where(m.Product.name.ilike(like) | m.Product.sku.ilike(like))
                .limit(limit)
            )
        )

    def get(self, product_id: str) -> m.Product | None:
        return self.s.get(m.Product, product_id)


class InventoryRepo:
    def __init__(self, session: Session):
        self.s = session

    def get_for_product(self, product_id: str) -> m.Inventory | None:
        return self.s.scalar(select(m.Inventory).where(m.Inventory.product_id == product_id))

    def get_for_sku(self, sku: str) -> m.Inventory | None:
        return self.s.scalar(
            select(m.Inventory)
            .join(m.Product)
            .options(joinedload(m.Inventory.product))
            .where(m.Product.sku == sku.upper())
        )


class OrderRepo:
    def __init__(self, session: Session):
        self.s = session

    def get_by_number(self, order_number: str) -> m.Order | None:
        return self.s.scalar(
            select(m.Order)
            .options(joinedload(m.Order.items))
            .where(m.Order.order_number == order_number)
        )

    def add(self, order: m.Order) -> m.Order:
        self.s.add(order)
        self.s.flush()
        return order


class AuditRepo:
    def __init__(self, session: Session):
        self.s = session

    def write(
        self,
        action: str,
        *,
        actor: str | None = None,
        entity_type: str | None = None,
        entity_id: str | None = None,
        request_id: str | None = None,
        workflow_id: str | None = None,
        detail: str | None = None,
    ) -> m.AuditLog:
        row = m.AuditLog(
            action=action,
            actor=actor,
            entity_type=entity_type,
            entity_id=entity_id,
            request_id=request_id,
            workflow_id=workflow_id,
            detail=detail,
        )
        self.s.add(row)
        self.s.flush()
        return row
