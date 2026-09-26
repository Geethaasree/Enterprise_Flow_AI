"use client";

import { useState } from "react";
import { Shell } from "@/components/Shell";
import { api } from "@/lib/api";

export default function EvaluationsPage() {
  const [summary, setSummary] = useState<Record<string, unknown> | null>(null);
  const [busy, setBusy] = useState(false);
  const [err, setErr] = useState<string | null>(null);

  async function run() {
    setBusy(true);
    setErr(null);
    try {
      const { ok, data } = await api<{ summary?: Record<string, unknown>; detail?: string }>(
        "/evaluations/run",
        { method: "POST", body: "{}" },
      );
      if (!ok) setErr(data.detail || "eval failed");
      else setSummary(data.summary || data);
    } finally {
      setBusy(false);
    }
  }

  return (
    <Shell title="Evaluations">
      <div className="row mb">
        <button className="btn primary" type="button" disabled={busy} onClick={run}>
          {busy ? "Running…" : "Run evaluation suites"}
        </button>
      </div>
      {err && <div className="errbox">{err}</div>}
      <div className="card">
        {!summary ? (
          <div className="empty">No results yet. Metrics come only from live suite runs.</div>
        ) : (
          <pre className="toolcard">{JSON.stringify(summary, null, 2)}</pre>
        )}
      </div>
    </Shell>
  );
}
