"use client";

import { FormEvent, useState } from "react";
import { Shell } from "@/components/Shell";
import { api } from "@/lib/api";

export default function KnowledgePage() {
  const [q, setQ] = useState("return policy restocking fee");
  const [hits, setHits] = useState<Array<Record<string, unknown>>>([]);
  const [msg, setMsg] = useState<string | null>(null);
  const [busy, setBusy] = useState(false);

  async function search(e?: FormEvent) {
    e?.preventDefault();
    setBusy(true);
    setMsg(null);
    try {
      const { data } = await api<{
        citations?: Array<Record<string, unknown>>;
        results?: Array<Record<string, unknown>>;
        message?: string;
        count?: number;
      }>("/rag/search", {
        method: "POST",
        body: JSON.stringify({ query: q, top_k: 5 }),
      });
      const list = data.citations || data.results || [];
      setHits(list);
      setMsg(data.message || (list.length ? `${list.length} hits` : "no relevant policy found"));
    } finally {
      setBusy(false);
    }
  }

  return (
    <Shell title="Knowledge Base">
      <form className="card mb row" onSubmit={search}>
        <input className="input" value={q} onChange={(e) => setQ(e.target.value)} />
        <button className="btn primary" type="submit" disabled={busy}>
          Search
        </button>
      </form>
      {msg && <div className="sub mb" style={{ color: "var(--muted)" }}>{msg}</div>}
      {hits.length === 0 ? (
        <div className="empty">No citations. Try a policy query.</div>
      ) : (
        hits.map((h, i) => (
          <div className="cite" key={i}>
            <div className="src">
              {String(h.source || "doc")} · score {String(h.score ?? "—")}
            </div>
            <div style={{ marginTop: 8 }}>{String(h.text || h.content || h.chunk || "")}</div>
          </div>
        ))
      )}
    </Shell>
  );
}
