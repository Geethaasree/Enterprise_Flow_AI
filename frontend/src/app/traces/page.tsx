"use client";

import { useEffect, useState } from "react";
import { Shell, StatusChip } from "@/components/Shell";
import { api } from "@/lib/api";

export default function TracesPage() {
  const [runs, setRuns] = useState<Array<Record<string, unknown>>>([]);
  const [wfId, setWfId] = useState("");
  const [state, setState] = useState<Record<string, unknown> | null>(null);
  const [err, setErr] = useState<string | null>(null);

  useEffect(() => {
    (async () => {
      const { data } = await api<{ runs?: Array<Record<string, unknown>> }>("/evaluations/runs?limit=20");
      setRuns(data.runs || []);
    })();
  }, []);

  async function loadWf() {
    if (!wfId.trim()) return;
    setErr(null);
    const { ok, data } = await api<{ state?: Record<string, unknown>; detail?: string; status?: string }>(
      `/workflows/${wfId.trim()}`,
    );
    if (!ok) {
      setErr(data.detail || data.status || "not found");
      setState(null);
      return;
    }
    setState(data.state || data);
  }

  return (
    <Shell title="Agent Traces">
      {err && <div className="errbox mb">{err}</div>}
      <div className="card mb">
        <h3>Lookup workflow checkpoint</h3>
        <div className="row mt">
          <input
            className="input"
            style={{ maxWidth: 360 }}
            placeholder="wf_…"
            value={wfId}
            onChange={(e) => setWfId(e.target.value)}
          />
          <button className="btn primary" type="button" onClick={loadWf}>
            Load
          </button>
        </div>
        {state && (
          <div className="mt">
            <StatusChip status={String(state.status || state.intent || "ok")} />
            <pre className="toolcard mt">{JSON.stringify(state, null, 2)}</pre>
          </div>
        )}
      </div>
      <div className="card">
        <h3>Recent MLflow runs (file store)</h3>
        {runs.length === 0 ? (
          <div className="empty">No trace runs yet.</div>
        ) : (
          <table className="table">
            <thead>
              <tr>
                <th>Run</th>
                <th>Info</th>
              </tr>
            </thead>
            <tbody>
              {runs.map((r, i) => (
                <tr key={i}>
                  <td className="mono">{String(r.run_id || i).slice(0, 18)}</td>
                  <td className="mono" style={{ fontSize: "0.75rem" }}>
                    {JSON.stringify(r).slice(0, 200)}
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
