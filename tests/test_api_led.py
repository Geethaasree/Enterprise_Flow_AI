"""API-led + SAP simulator tests."""

from __future__ import annotations

import os
import uuid

import pytest
from fastapi.testclient import TestClient
from sqlalchemy import text

from app import models  # noqa: F401
from app.db import Base, reset_engine, session_scope
from app.main import create_app
from app.seed import seed_enterprise

pytestmark = pytest.mark.skipif(
    not os.getenv("DATABASE_URL") and not os.getenv("EF_DB_TESTS"),
    reason="needs Postgres",
)


@pytest.fixture
def client():
    reset_engine()
    with session_scope() as s:
        s.execute(text("CREATE EXTENSION IF NOT EXISTS vector"))
        Base.metadata.create_all(s.get_bind())
        seed_enterprise(s, reset=True)
    yield TestClient(create_app())
    reset_engine()


def test_sap_customer_and_material(client):
    r = client.get("/sap/customers/ACME")
    assert r.status_code == 200
    c = r.json()["customer"]
    assert c["KUNNR"] == "ACME"
    assert "NAME1" in c

    m = client.get("/sap/materials/LAPTOP-PRO-14")
    assert m.status_code == 200
    assert m.json()["material"]["MATNR"] == "LAPTOP-PRO-14"

    st = client.get("/sap/stock/LAPTOP-PRO-14")
    assert st.status_code == 200
    assert "LABST" in st.json()["stock"]


def test_sap_failure_simulation(client):
    r = client.get("/sap/customers/ACME", headers={"X-SAP-Fail": "1"})
    assert r.status_code == 503
    assert r.json()["code"] == "SAP_UNAVAILABLE"


def test_system_maps_sap_fields(client):
    r = client.get("/system/customers/ACME")
    assert r.status_code == 200
    body = r.json()
    assert body["layer"] == "system"
    assert body["customer"]["customer_code"] == "ACME"
    assert body["customer"]["source"] == "sap"


def test_process_and_experience_order(client):
    onum = f"PROC-{uuid.uuid4().hex[:8].upper()}"
    p = client.post(
        "/process/orders",
        json={"customer_code": "ACME", "sku": "LAPTOP-PRO-14", "quantity": 1, "order_number": onum},
    )
    assert p.status_code == 200
    pb = p.json()
    assert pb["layer"] == "process"
    assert "system.customer" in pb["steps"]
    assert pb["order"]["order_number"] == onum

    e = client.post(
        "/experience/orders",
        json={"customer": "ACME", "product": "LAPTOP-PRO-14", "qty": 1},
    )
    assert e.status_code == 200
    eb = e.json()
    assert eb["layer"] == "experience"
    assert eb["trace"]["sap"] is True
    assert eb["order_id"].startswith("PROC-") or eb["order_id"]

    g = client.get(f"/experience/orders/{eb['order_id']}")
    assert g.status_code == 200
    assert g.json()["order_id"] == eb["order_id"]


def test_experience_stock_guard(client):
    r = client.post(
        "/experience/orders",
        json={"customer": "ACME", "product": "LAPTOP-PRO-14", "qty": 500},
    )
    assert r.status_code == 409
