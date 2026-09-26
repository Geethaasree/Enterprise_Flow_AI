"use client";

import { useEffect, useState } from "react";
import { Shell, StatusChip } from "@/components/Shell";
import { api } from "@/lib/api";

type Order = {
  order_number: string;
  status: string;
  total: string;
  discount_total?: string;
  currency?: string;
  created_at?: string;
};

export default function OrdersPage() {
  const [orders, setOrders] = useState<Order[]>([]);
  const [err, setErr] = useState<string | null>(null);

  async function load() {
    const { ok, data } = await api<{ orders?: Order[]; detail?: string }>("/enterprise/orders?limit=100");
    if (!ok) setErr(data.detail || "failed to load orders");
    else setOrders(data.orders || []);
  }

  useEffect(() => {
    load();
  }, []);

  return (
    <Shell title="Orders">
      <div className="row mb">
        <button className="btn" type="button" onClick={load}>
          Refresh
        </button>
      </div>
      {err && <div className="errbox">{err}</div>}
      <div className="card">
        {orders.length === 0 ? (
          <div className="empty">No orders yet. Create one via Chat workflow.</div>
        ) : (
          <table className="table">
            <thead>
              <tr>
                <th>Order</th>
                <th>Status</th>
                <th>Total</th>
                <th>Created</th>
              </tr>
            </thead>
            <tbody>
              {orders.map((o) => (
                <tr key={o.order_number}>
                  <td className="mono">{o.order_number}</td>
                  <td>
                    <StatusChip status={o.status} />
                  </td>
                  <td className="mono">
                    {o.total} {o.currency || "USD"}
                  </td>
                  <td className="mono">{o.created_at || "—"}</td>
                </tr>
              ))}
            </tbody>
          </table>
        )}
      </div>
    </Shell>
  );
}
