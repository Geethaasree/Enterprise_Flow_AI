"""Phase 4 DB / seed / service tests (requires Postgres)."""

from __future__ import annotations

import os
import uuid
from decimal import Decimal

import pytest
from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker

from app import models  # noqa: F401
from app.db import Base, reset_engine
from app.seed import seed_enterprise
from app.services import (
    CustomerService,
    InventoryService,
    OrderService,
    PricingService,
    ServiceError,
)

pytestmark = pytest.mark.skipif(
    not os.getenv("DATABASE_URL") and not os.getenv("EF_DB_TESTS"),
    reason="Set DATABASE_URL or EF_DB_TESTS=1 with local Postgres",
)

DB_URL = os.getenv(
    "DATABASE_URL",
    "postgresql+psycopg://enterpriseflow:enterpriseflow@localhost:5432/enterpriseflow",
)


@pytest.fixture()
def session():
    reset_engine()
    engine = create_engine(DB_URL, pool_pre_ping=True)
    # ensure schema
    Base.metadata.create_all(engine)
    Session = sessionmaker(bind=engine, autoflush=False, expire_on_commit=False)
    s = Session()
    try:
        seed_enterprise(s, reset=True)
        s.commit()
        yield s
        s.commit()
    except Exception:
        s.rollback()
        raise
    finally:
        s.close()
        engine.dispose()
        reset_engine()


def test_seed_acme(session):
    cust = CustomerService(session).get_by_code("ACME")
    assert cust.name == "ACME Corporation"
    contract = CustomerService(session).get_contract("ACME")
    assert contract.discount_pct == Decimal("5.00")


def test_inventory_reserve_release(session):
    inv = InventoryService(session)
    before = inv.view("LAPTOP-PRO-14")
    assert before.available == 120
    after = inv.reserve("LAPTOP-PRO-14", 10)
    assert after.reserved == 10
    assert after.available == 110
    back = inv.release("LAPTOP-PRO-14", 10)
    assert back.reserved == 0
    assert back.available == 120


def test_inventory_insufficient(session):
    inv = InventoryService(session)
    with pytest.raises(ServiceError) as ei:
        inv.reserve("LAPTOP-PRO-14", 9999)
    assert ei.value.code == "INSUFFICIENT_STOCK"


def test_pricing_contract_and_volume(session):
    p = PricingService(session)
    q1 = p.quote("LAPTOP-PRO-14", 1, "ACME")
    assert q1.discount_pct == Decimal("5.00")  # contract
    q100 = p.quote("LAPTOP-PRO-14", 100, "ACME")
    assert q100.discount_pct == Decimal("12.00")  # volume beats contract
    assert q100.line_total == (Decimal("1499.00") * 100 * Decimal("0.88")).quantize(Decimal("0.01"))


def test_order_create_with_reserve(session):
    onum = f"ORD-{uuid.uuid4().hex[:8].upper()}"
    order = OrderService(session).create_draft(
        "ACME",
        "LAPTOP-PRO-14",
        10,
        order_number=onum,
        reserve=True,
        actor="test",
    )
    assert order.status == "reserved"
    assert order.total > 0
    inv = InventoryService(session).view("LAPTOP-PRO-14")
    assert inv.reserved == 10


def test_transaction_rollback_on_error(session):
    inv = InventoryService(session)
    inv.reserve("LAPTOP-PRO-14", 5)
    session.commit()
    try:
        inv.reserve("LAPTOP-PRO-14", 9999)
        session.commit()
    except ServiceError:
        session.rollback()
    # after rollback of failed op, reserved still 5 from prior commit
    session.expire_all()
    assert inv.view("LAPTOP-PRO-14").reserved == 5


def test_alembic_heads_exist():
    from pathlib import Path

    versions = list(Path("alembic/versions").glob("*.py"))
    assert versions, "expected alembic migration file"
