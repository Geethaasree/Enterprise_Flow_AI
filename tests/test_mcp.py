"""MCP tool tests."""

from __future__ import annotations

import os
import uuid

import pytest

from app.db import reset_engine, session_scope
from app.mcp_tools import ToolError, call_tool, list_tools
from app.seed import seed_enterprise

pytestmark = pytest.mark.skipif(
    not os.getenv("DATABASE_URL") and not os.getenv("EF_DB_TESTS"),
    reason="needs Postgres",
)


@pytest.fixture(autouse=True)
def _seed():
    reset_engine()
    with session_scope() as s:
        seed_enterprise(s, reset=True)
    yield
    reset_engine()


def test_list_tools_min_count():
    names = {t["name"] for t in list_tools()}
    required = {
        "get_customer",
        "get_customer_contract",
        "check_credit",
        "search_products",
        "get_product",
        "check_inventory",
        "reserve_inventory",
        "release_inventory",
        "get_price",
        "calculate_discount",
        "create_order",
        "get_order",
        "cancel_order",
        "get_shipping_options",
        "create_shipment",
        "track_shipment",
        "search_policy",
    }
    assert required <= names


def test_get_customer_ok():
    out = call_tool("get_customer", {"customer_code": "ACME"}, role="sales")
    assert out["result"]["name"] == "ACME Corporation"


def test_invalid_input():
    with pytest.raises(ToolError) as e:
        call_tool("check_inventory", {}, role="sales")
    assert e.value.code == "INVALID_INPUT"


def test_unauthorized_tool():
    with pytest.raises(ToolError) as e:
        call_tool(
            "create_shipment",
            {"order_number": "x", "option_code": "GROUND"},
            role="viewer",
        )
    assert e.value.code == "UNAUTHORIZED"


def test_reserve_and_idempotent():
    key = f"idem-{uuid.uuid4().hex}"
    a = call_tool(
        "reserve_inventory",
        {"sku": "LAPTOP-PRO-14", "quantity": 3, "idempotency_key": key},
        role="sales",
    )
    b = call_tool(
        "reserve_inventory",
        {"sku": "LAPTOP-PRO-14", "quantity": 3, "idempotency_key": key},
        role="sales",
    )
    assert a["result"]["reserved"] == b["result"]["reserved"]
    assert b["result"].get("idempotent_replay") is True


def test_create_get_cancel_order():
    onum = f"ORD-MCP-{uuid.uuid4().hex[:8].upper()}"
    created = call_tool(
        "create_order",
        {
            "customer_code": "ACME",
            "sku": "LAPTOP-PRO-14",
            "quantity": 2,
            "order_number": onum,
            "reserve": True,
            "idempotency_key": f"ord-{onum}",
        },
        role="sales",
    )
    assert created["result"]["status"] == "reserved"
    got = call_tool("get_order", {"order_number": onum}, role="sales")
    assert got["result"]["order_number"] == onum
    cancelled = call_tool("cancel_order", {"order_number": onum}, role="sales")
    assert cancelled["result"]["status"] == "cancelled"
    inv = call_tool("check_inventory", {"sku": "LAPTOP-PRO-14"}, role="sales")
    assert inv["result"]["reserved"] == 0


def test_price_and_policy():
    price = call_tool(
        "get_price",
        {"sku": "LAPTOP-PRO-14", "quantity": 100, "customer_code": "ACME"},
        role="sales",
    )
    assert price["result"]["discount_pct"] == "12.00"
    pol = call_tool("search_policy", {"query": "credit"}, role="sales")
    assert pol["result"]["policies"]


def test_mcp_http_api():
    from fastapi.testclient import TestClient

    from app.main import create_app

    client = TestClient(create_app())
    r = client.get("/mcp/tools")
    assert r.status_code == 200
    assert len(r.json()["tools"]) >= 17
    r2 = client.post(
        "/mcp/call",
        json={"name": "get_customer", "arguments": {"customer_code": "ACME"}, "role": "sales"},
    )
    assert r2.status_code == 200
    assert r2.json()["result"]["customer_code"] == "ACME"
    r3 = client.post(
        "/mcp/call",
        json={"name": "create_shipment", "arguments": {"order_number": "x"}, "role": "viewer"},
        headers={"X-Role": "viewer"},
    )
    assert r3.status_code == 403
