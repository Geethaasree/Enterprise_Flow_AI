"""Deterministic enterprise seed data."""

from __future__ import annotations

from decimal import Decimal

from sqlalchemy import func, select
from sqlalchemy.orm import Session

from app import models as m
from app.db import Base

# Stable IDs so tests and demos are deterministic across re-seeds.
SEED = {
    "customer_acme": "cust_acme000000000000000001",
    "contract_acme": "ctr_acme000000000000000001",
    "sku_laptop": "LAPTOP-PRO-14",
    "product_laptop": "prod_laptop000000000000001",
    "inv_laptop": "inv_laptop000000000000001",
    "sku_mouse": "MOUSE-ERGO-01",
    "product_mouse": "prod_mouse000000000000001",
    "inv_mouse": "inv_mouse0000000000000001",
    "role_admin": "role_admin0000000000000001",
    "role_sales": "role_sales0000000000000001",
    "user_demo": "user_demo00000000000000001",
    "perm_order": "perm_order_create000000001",
    "perm_approve": "perm_order_approve00000001",
}


def seed_enterprise(session: Session, *, reset: bool = False) -> dict[str, int]:
    """Idempotent seed. If reset=True, truncate enterprise tables first (dev only)."""
    if reset:
        _wipe(session)

    existing = session.scalar(select(func.count()).select_from(m.Customer))
    if existing and existing > 0 and not reset:
        return {"customers": int(existing), "skipped": 1}

    perms = [
        m.Permission(id=SEED["perm_order"], code="order.create", description="Create orders"),
        m.Permission(id=SEED["perm_approve"], code="order.approve", description="Approve orders"),
    ]
    session.add_all(perms)

    admin = m.Role(id=SEED["role_admin"], code="admin", name="Administrator")
    sales = m.Role(id=SEED["role_sales"], code="sales", name="Sales Representative")
    session.add_all([admin, sales])
    session.flush()
    session.add_all(
        [
            m.RolePermission(role_id=admin.id, permission_id=SEED["perm_order"]),
            m.RolePermission(role_id=admin.id, permission_id=SEED["perm_approve"]),
            m.RolePermission(role_id=sales.id, permission_id=SEED["perm_order"]),
        ]
    )

    session.add(
        m.User(
            id=SEED["user_demo"],
            username="demo",
            email="demo@enterpriseflow.local",
            full_name="Demo User",
            role_id=sales.id,
        )
    )

    acme = m.Customer(
        id=SEED["customer_acme"],
        code="ACME",
        name="ACME Corporation",
        status="active",
        credit_limit=Decimal("500000.00"),
        credit_used=Decimal("12500.00"),
        country="US",
    )
    session.add(acme)
    session.add(
        m.CustomerContract(
            id=SEED["contract_acme"],
            customer_id=acme.id,
            contract_number="CTR-ACME-2026-001",
            discount_pct=Decimal("5.00"),
            payment_terms="NET30",
            active=True,
        )
    )

    laptop = m.Product(
        id=SEED["product_laptop"],
        sku=SEED["sku_laptop"],
        name="Laptop Pro 14",
        category="computers",
        unit_price=Decimal("1499.00"),
        currency="USD",
        active=True,
    )
    mouse = m.Product(
        id=SEED["product_mouse"],
        sku=SEED["sku_mouse"],
        name="Ergo Mouse",
        category="accessories",
        unit_price=Decimal("49.00"),
        currency="USD",
        active=True,
    )
    session.add_all([laptop, mouse])
    session.flush()

    session.add_all(
        [
            m.Inventory(
                id=SEED["inv_laptop"],
                product_id=laptop.id,
                warehouse="MAIN",
                on_hand=120,
                reserved=0,
            ),
            m.Inventory(
                id=SEED["inv_mouse"],
                product_id=mouse.id,
                warehouse="MAIN",
                on_hand=500,
                reserved=0,
            ),
            m.PricingCondition(
                product_id=laptop.id,
                name="Laptop volume 50+",
                discount_pct=Decimal("8.00"),
                min_qty=50,
                active=True,
            ),
            m.PricingCondition(
                product_id=laptop.id,
                name="Laptop volume 100+",
                discount_pct=Decimal("12.00"),
                min_qty=100,
                active=True,
            ),
        ]
    )

    session.flush()
    return {
        "customers": 1,
        "products": 2,
        "inventory": 2,
        "roles": 2,
        "users": 1,
        "skipped": 0,
    }


def _wipe(session: Session) -> None:
    for table in reversed(Base.metadata.sorted_tables):
        session.execute(table.delete())
    session.flush()
