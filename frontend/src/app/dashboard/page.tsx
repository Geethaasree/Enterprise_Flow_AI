"use client";

import { useEffect, useState } from "react";
import Link from "next/link";
import { Shell, StatusChip } from "@/components/Shell";
import { api } from "@/lib/api";

type Approval = {
  id: string;
  workflow_id?: string;
  status?: string;
  reason?: string;
  approval_type?: string;
};

export default function DashboardPage() {
  const [pending, setPending] = useState<Approval[]>([]);
  const [evalSummary, setEvalSummary] = useState<{
    pass_rate?: number;
    n?: number;
    latency_ms_p50?: number;
  } | null>(null);
  const [orders, setOrders] = useState<number | null>(null);
  const [runs, setRuns] = useState<Array<Record<string, unknown>>>([]);
  const [err, setErr] = useState<string | null>(null);

  useEffect(() => {
    (async () => {
      try {
        const [a, o, e, r] = await Promise.all([
          api<{ approvals?: Approval[] }>("/approvals?status=pending"),
          api<{ count?: number }>("/enterprise/orders?limit=50"),
          api<{ summary?: { pass_rate?: number; n?: number; latency_ms_p50?: number } }>(
            "/evaluations/run",
            { method: "POST", body: "{}" },
          ),
          api<{ runs?: Array<Record<string, unknown>> }>("/evaluations/runs?limit=8"),
        ]);
        setPending(a.data.approvals || []);
        setOrders(o.data.count ?? null);
        setEvalSummary(e.data.summary || null);
        setRuns(r.data.runs || []);
      } catch (ex) {
        setErr(ex instanceof Error ? ex.message : String(ex));
      }
    })();
  }, []);

  return (
    <Shell title="Dashboard">
      {err && <div className="errbox">{err}</div>}
      <div className="grid4 mb">
        <div className="card">
          <h3>Pending Approvals</h3>
          <div className="value">{pending.length}</div>
          <div className="sub">
            <Link href="/approvals">View queue →</Link>
          </div>
        </div>
        <div className="card">
          <h3>Eval Pass Rate</h3>
          <div className="value">
            {evalSummary?.pass_rate != null ? `${(evalSummary.pass_rate * 100).toFixed(0)}%` : "—"}
          </div>
          <div className="sub">
            {evalSummary?.n != null ? `${evalSummary.n} cases (live run)` : "No eval data yet"}
          </div>
        </div>
        <div className="card">
          <h3>Orders (listed)</h3>
          <div className="value">{orders ?? "—"}</div>
          <div className="sub">{orders === 0 ? "Empty state · no orders yet" : "From /enterprise/orders"}</div>
        </div>
        <div className="card">
          <h3>Latency p50</h3>
          <div className="value">
            {evalSummary?.latency_ms_p50 != null ? `${Math.round(evalSummary.latency_ms_p50)}ms` : "—"}
          </div>
          <div className="sub">From last evaluation suite</div>
        </div>
      </div>

      <div className="grid2">
        <div className="card">
          <h3>Recent MLflow / eval runs</h3>
          {runs.length === 0 ? (
            <div className="empty">No runs yet — open Evaluations to execute.</div>
          ) : (
            <table className="table">
              <thead>
                <tr>
                  <th>Run</th>
                  <th>Metrics</th>
                </tr>
              </thead>
              <tbody>
                {runs.map((run, i) => (
                  <tr key={String(run.run_id || i)}>
                    <td className="mono">{String(run.run_id || run.name || i).slice(0, 16)}</td>
                    <td className="mono" style={{ fontSize: "0.75rem" }}>
                      {JSON.stringify(run.metrics || run).slice(0, 120)}
                    </td>
                  </tr>
                ))}
              </tbody>
            </table>
          )}
        </div>
        <div className="card">
          <h3>Human-in-the-loop queue</h3>
          {pending.length === 0 ? (
            <div className="empty">No pending approvals.</div>
          ) : (
            <table className="table">
              <thead>
                <tr>
                  <th>ID</th>
                  <th>Reason</th>
                  <th>Status</th>
                </tr>
              </thead>
              <tbody>
                {pending.map((p) => (
                  <tr key={p.id}>
                    <td className="mono">{p.id.slice(0, 12)}</td>
                    <td>{p.reason || p.approval_type || "—"}</td>
                    <td>
                      <StatusChip status={p.status} />
                    </td>
                  </tr>
                ))}
              </tbody>
            </table>
          )}
        </div>
      </div>
    </Shell>
  );
}
