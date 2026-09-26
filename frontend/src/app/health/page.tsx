"use client";

import { useEffect, useState } from "react";
import { Shell, StatusChip } from "@/components/Shell";
import { api } from "@/lib/api";

export default function HealthPage() {
  const [rows, setRows] = useState<Array<{ name: string; ok: boolean; body: unknown }>>([]);

  useEffect(() => {
    (async () => {
      const paths = [
        ["/health", "API"],
        ["/health/db", "Postgres"],
        ["/health/redis", "Redis"],
        ["/llm/status", "LLM"],
      ] as const;
      const out = [];
      for (const [p, name] of paths) {
        const r = await api(p);
        out.push({ name, ok: r.ok, body: r.data });
      }
      setRows(out);
    })();
  }, []);

  return (
    <Shell title="System Health">
      <div className="grid2">
        {rows.map((r) => (
          <div className="card" key={r.name}>
            <div className="row mb">
              <h3 style={{ margin: 0 }}>{r.name}</h3>
              <StatusChip status={r.ok ? "ok" : "error"} />
            </div>
            <pre className="toolcard">{JSON.stringify(r.body, null, 2)}</pre>
          </div>
        ))}
        {rows.length === 0 && <div className="empty">Checking…</div>}
      </div>
    </Shell>
  );
}
