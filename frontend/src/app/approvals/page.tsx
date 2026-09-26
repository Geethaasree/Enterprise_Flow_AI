"use client";

import { useEffect, useState } from "react";
import { Shell, StatusChip } from "@/components/Shell";
import { api } from "@/lib/api";

type Approval = {
  id: string;
  workflow_id?: string;
  status?: string;
  reason?: string;
  approval_type?: string;
  payload?: unknown;
};

export default function ApprovalsPage() {
  const [rows, setRows] = useState<Approval[]>([]);
  const [err, setErr] = useState<string | null>(null);
  const [busy, setBusy] = useState<string | null>(null);

  async function load() {
    const { data } = await api<{ approvals?: Approval[] }>("/approvals?status=pending");
    setRows(data.approvals || []);
  }

  useEffect(() => {
    load();
  }, []);

  async function decide(id: string, action: "approve" | "reject") {
    setBusy(id);
    setErr(null);
    try {
      const { ok, data } = await api<{ detail?: string }>(`/approvals/${id}/decide`, {
        method: "POST",
        body: JSON.stringify({ action, decided_by: "ui-admin", note: `approvals page ${action}` }),
      });
      if (!ok) setErr(data.detail || "decide failed");
      await load();
    } finally {
      setBusy(null);
    }
  }

  return (
    <Shell title="Approvals">
      {err && <div className="errbox mb">{err}</div>}
      <div className="card">
        {rows.length === 0 ? (
          <div className="empty">No pending approvals.</div>
        ) : (
          <table className="table">
            <thead>
              <tr>
                <th>ID</th>
                <th>Workflow</th>
                <th>Reason</th>
                <th>Status</th>
                <th>Actions</th>
              </tr>
            </thead>
            <tbody>
              {rows.map((r) => (
                <tr key={r.id}>
                  <td className="mono">{r.id.slice(0, 14)}</td>
                  <td className="mono">{r.workflow_id || "—"}</td>
                  <td>{r.reason || r.approval_type || "—"}</td>
                  <td>
                    <StatusChip status={r.status} />
                  </td>
                  <td>
                    <div className="row">
                      <button
                        className="btn ok sm"
                        type="button"
                        disabled={busy === r.id}
                        onClick={() => decide(r.id, "approve")}
                      >
                        Approve
                      </button>
                      <button
                        className="btn danger sm"
                        type="button"
                        disabled={busy === r.id}
                        onClick={() => decide(r.id, "reject")}
                      >
                        Reject
                      </button>
                    </div>
                  </td>
                </tr>
              ))}
            </tbody>
          </table>
        )}
      </div>
    </Shell>
  );
}
