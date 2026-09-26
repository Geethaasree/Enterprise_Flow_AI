"""Specialist agents — call MCP tools only (no direct DB)."""

from __future__ import annotations

import logging
import uuid
from typing import Any

from app.agents.parse import parse_customer, parse_quantity, parse_sku
from app.graph.state import GraphState
from app.mcp_tools import ToolError, call_tool

logger = logging.getLogger(__name__)
ROLE = "sales"


def _ctx(state: GraphState) -> dict[str, Any]:
    return dict(state.get("context") or {})


def _steps(state: GraphState, name: str) -> list[str]:
    steps = list(state.get("steps") or [])
    steps.append(name)
    return steps


def _tool(name: str, args: dict, state: GraphState) -> dict[str, Any]:
    rid = state.get("request_id")
    try:
        out = call_tool(name, args, role=ROLE, request_id=rid)
        return {"ok": True, "result": out.get("result") or {}, "raw": out}
    except ToolError as e:
        return {"ok": False, "code": e.code, "message": e.message}


def customer_agent(state: GraphState) -> dict:
    """Identify customer + contract + light credit check."""
    ctx = _ctx(state)
    text = state.get("user_request") or ""
    code = parse_customer(text, state.get("customer_hint"))
    qty = parse_quantity(text)
    sku = parse_sku(text)
    ctx["customer_code"] = code
    ctx["sku"] = sku
    ctx["quantity"] = qty

    cust = _tool("get_customer", {"customer_code": code}, state)
    contract = _tool("get_customer_contract", {"customer_code": code}, state)
    # rough credit probe using list price * qty (pricing agent refines)
    amount = 1500 * qty  # provisional
    credit = _tool("check_credit", {"customer_code": code, "amount": amount}, state)

    ctx["customer"] = cust
    ctx["contract"] = contract
    ctx["credit_probe"] = credit

    notes = list(state.get("notes") or [])
    if not cust["ok"]:
        notes.append(f"customer_agent fail: {cust.get('message')}")
        return {
            "steps": _steps(state, "customer_agent"),
            "notes": notes,
            "context": ctx,
            "error": cust.get("message"),
            "final_response": f"Could not identify customer {code}: {cust.get('message')}",
            "route": "done",
        }
    notes.append(f"customer_ok={code}")
    return {
        "steps": _steps(state, "customer_agent"),
        "notes": notes,
        "context": ctx,
        "customer_hint": code,
    }


def inventory_agent(state: GraphState) -> dict:
    """Product + stock check; reserve when on order path."""
    ctx = _ctx(state)
    text = state.get("user_request") or ""
    sku = ctx.get("sku") or parse_sku(text)
    qty = int(ctx.get("quantity") or parse_quantity(text))
    ctx["sku"] = sku
    ctx["quantity"] = qty

    product = _tool("get_product", {"sku": sku}, state)
    inv = _tool("check_inventory", {"sku": sku}, state)
    ctx["product"] = product
    ctx["inventory"] = inv

    notes = list(state.get("notes") or [])
    if not product["ok"] or not inv["ok"]:
        msg = product.get("message") or inv.get("message") or "inventory error"
        notes.append(f"inventory_agent fail: {msg}")
        return {
            "steps": _steps(state, "inventory_agent"),
            "notes": notes,
            "context": ctx,
            "error": msg,
            "final_response": f"Inventory/product issue for {sku}: {msg}",
            "route": "done",
        }

    available = int(inv["result"].get("available") or 0)
    ctx["available"] = available
    notes.append(f"inventory available={available} need={qty}")

    # reserve only for create_order intent
    if state.get("intent") == "create_order":
        if available < qty:
            msg = f"Insufficient stock for {sku}: need {qty}, available {available}"
            notes.append(msg)
            return {
                "steps": _steps(state, "inventory_agent"),
                "notes": notes,
                "context": ctx,
                "error": msg,
                "final_response": msg,
                "route": "done",
            }
        key = f"res-{state.get('workflow_id')}-{sku}-{qty}"
        res = _tool(
            "reserve_inventory",
            {"sku": sku, "quantity": qty, "idempotency_key": key},
            state,
        )
        ctx["reservation"] = res
        if not res["ok"]:
            return {
                "steps": _steps(state, "inventory_agent"),
                "notes": notes + [res.get("message") or ""],
                "context": ctx,
                "error": res.get("message"),
                "final_response": res.get("message"),
                "route": "done",
            }
        notes.append("reserved")

    # inventory-only path finishes here
    if state.get("intent") == "check_inventory":
        p = product["result"]
        i = inv["result"]
        return {
            "steps": _steps(state, "inventory_agent"),
            "notes": notes,
            "context": ctx,
            "final_response": (
                f"{p.get('name')} ({sku}): on_hand={i.get('on_hand')} "
                f"reserved={i.get('reserved')} available={i.get('available')} @ {i.get('warehouse')}"
            ),
            "route": "done",
        }

    return {"steps": _steps(state, "inventory_agent"), "notes": notes, "context": ctx}


def pricing_agent(state: GraphState) -> dict:
    """Deterministic quote via MCP pricing tools."""
    ctx = _ctx(state)
    sku = ctx.get("sku") or "LAPTOP-PRO-14"
    qty = int(ctx.get("quantity") or 1)
    code = ctx.get("customer_code") or "ACME"

    price = _tool(
        "get_price",
        {"sku": sku, "quantity": qty, "customer_code": code},
        state,
    )
    disc = _tool(
        "calculate_discount",
        {"sku": sku, "quantity": qty, "customer_code": code},
        state,
    )
    ctx["price"] = price
    ctx["discount"] = disc
    notes = list(state.get("notes") or [])

    if not price["ok"]:
        return {
            "steps": _steps(state, "pricing_agent"),
            "notes": notes + [price.get("message") or ""],
            "context": ctx,
            "error": price.get("message"),
            "final_response": price.get("message"),
            "route": "done",
        }

    # credit check with real line total
    total = price["result"].get("line_total")
    credit = _tool("check_credit", {"customer_code": code, "amount": total}, state)
    ctx["credit"] = credit
    notes.append(f"price total={total} discount={price['result'].get('discount_pct')}%")

    if credit["ok"] and not credit["result"].get("approved"):
        notes.append("credit_exceeded")
        ctx["needs_approval"] = True

    return {"steps": _steps(state, "pricing_agent"), "notes": notes, "context": ctx}


def order_agent(state: GraphState) -> dict:
    """Create order via MCP after prior agents succeeded."""
    ctx = _ctx(state)
    if state.get("error"):
        return {"steps": _steps(state, "order_agent"), "context": ctx}

    sku = ctx.get("sku")
    qty = int(ctx.get("quantity") or 1)
    code = ctx.get("customer_code") or "ACME"
    onum = f"ORD-{uuid.uuid4().hex[:10].upper()}"
    # inventory already reserved — create without double-reserve
    created = _tool(
        "create_order",
        {
            "customer_code": code,
            "sku": sku,
            "quantity": qty,
            "order_number": onum,
            "reserve": False,
            "idempotency_key": f"ord-{state.get('workflow_id')}",
        },
        state,
    )
    ctx["order"] = created
    notes = list(state.get("notes") or [])
    if not created["ok"]:
        # best-effort release
        _tool(
            "release_inventory",
            {
                "sku": sku,
                "quantity": qty,
                "idempotency_key": f"rel-{state.get('workflow_id')}",
            },
            state,
        )
        return {
            "steps": _steps(state, "order_agent"),
            "notes": notes + [created.get("message") or ""],
            "context": ctx,
            "error": created.get("message"),
            "final_response": created.get("message"),
            "route": "done",
        }
    notes.append(f"order={created['result'].get('order_number')}")
    return {"steps": _steps(state, "order_agent"), "notes": notes, "context": ctx}


def policy_agent(state: GraphState) -> dict:
    """RAG policy retrieval for grounding / policy questions."""
    ctx = _ctx(state)
    text = state.get("user_request") or ""
    # on order path, pull relevant policies
    query = text
    if state.get("intent") == "create_order":
        query = "order approval credit inventory reservation discount"
        if ctx.get("needs_approval"):
            query = "credit limit approval policy"
    pol = _tool("search_policy", {"query": query}, state)
    ctx["policy"] = pol
    notes = list(state.get("notes") or [])
    notes.append("policy_retrieved" if pol.get("ok") else "policy_miss")

    if state.get("intent") == "policy":
        if pol.get("ok") and pol["result"].get("policies"):
            tops = pol["result"]["policies"][:2]
            lines = [f"- {p.get('title')}: {p.get('body', '')[:200]}" for p in tops]
            cites = [p.get("source") or p.get("id") for p in tops]
            return {
                "steps": _steps(state, "policy_agent"),
                "notes": notes,
                "context": ctx,
                "final_response": "Policy findings:\n" + "\n".join(lines) + f"\nSources: {', '.join(map(str, cites))}",
                "route": "done",
            }
        return {
            "steps": _steps(state, "policy_agent"),
            "notes": notes,
            "context": ctx,
            "final_response": "No relevant policy found for that question.",
            "route": "done",
        }

    return {"steps": _steps(state, "policy_agent"), "notes": notes, "context": ctx}


def compose_order_response(state: GraphState) -> str:
    ctx = state.get("context") or {}
    if state.get("error"):
        return state.get("final_response") or state["error"]
    cust = (ctx.get("customer") or {}).get("result") or {}
    order = (ctx.get("order") or {}).get("result") or {}
    price = (ctx.get("price") or {}).get("result") or {}
    inv = (ctx.get("inventory") or {}).get("result") or {}
    approval = "pending_approval" if ctx.get("needs_approval") else "ok"
    return (
        f"Order {order.get('order_number')} created for {cust.get('name') or ctx.get('customer_code')} "
        f"({ctx.get('sku')} x{ctx.get('quantity')}). "
        f"Total {price.get('line_total')} {order.get('currency') or 'USD'} "
        f"(discount {price.get('discount_pct')}%). "
        f"Stock remaining available≈{inv.get('available')}. "
        f"Credit/approval: {approval}."
    )


def general_agent(state: GraphState) -> dict:
    return {
        "steps": _steps(state, "general_agent"),
        "final_response": (
            "I can run order, inventory, and policy workflows. "
            f"Try: 'Create an order for 10 Laptop Pro 14 units for ACME.' "
            f"Received: {state.get('user_request', '')!r}"
        ),
        "route": "done",
    }


def finalize_agent(state: GraphState) -> dict:
    steps = _steps(state, "finalize")
    resp = state.get("final_response")
    if (
        state.get("intent") == "create_order"
        and not state.get("error")
        and (not resp or "Specialist" in resp)
    ):
        return {"steps": steps, "final_response": compose_order_response(state), "route": "done"}
    return {"steps": steps, "final_response": resp or "Workflow completed.", "route": "done"}
