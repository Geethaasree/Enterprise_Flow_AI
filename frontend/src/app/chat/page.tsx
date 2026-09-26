"use client";

import { FormEvent, useMemo, useState } from "react";
import { Shell, StatusChip } from "@/components/Shell";
import { api } from "@/lib/api";

type Msg = { role: "user" | "assistant"; text: string };
type Wf = {
  status?: string;
  workflow_id?: string;
  session_id?: string;
  request_id?: string;
  intent?: string;
  steps?: string[];
  final_response?: string;
  approval?: Record<string, unknown>;
  error?: string;
  context_used?: boolean;
};

export default function ChatPage() {
  const [input, setInput] = useState("Create an order for 1 Laptop Pro 14 units for ACME.");
  const [msgs, setMsgs] = useState<Msg[]>([]);
  const [wf, setWf] = useState<Wf | null>(null);
  const [sessionId, setSessionId] = useState<string | null>(null);
  const [tab, setTab] = useState<"steps" | "tools" | "rag" | "approval" | "result">("steps");
  const [busy, setBusy] = useState(false);
  const [err, setErr] = useState<string | null>(null);
  const [rag, setRag] = useState<Array<Record<string, unknown>>>([]);
  const [tools, setTools] = useState<Array<Record<string, unknown>>>([]);

  const steps = useMemo(() => wf?.steps || [], [wf]);

  async function run(e?: FormEvent) {
    e?.preventDefault();
    if (!input.trim() || busy) return;
    setBusy(true);
    setErr(null);
    const userText = input.trim();
    setMsgs((m) => [...m, { role: "user", text: userText }]);
    setInput("");
    try {
      const { ok, data, status } = await api<Wf & { detail?: string; code?: string; reason?: string }>(
        "/workflows/run",
        {
          method: "POST",
          headers: sessionId ? { "X-Session-Id": sessionId } : {},
          body: JSON.stringify({ message: userText, session_id: sessionId }),
        },
      );
      if (!ok) {
        setErr(`${data.code || status}: ${data.detail || data.reason || "workflow failed"}`);
        setMsgs((m) => [
          ...m,
          { role: "assistant", text: `Error: ${data.detail || data.code || status}` },
        ]);
        return;
      }
      setWf(data);
      if (data.session_id) setSessionId(data.session_id);
      setMsgs((m) => [
        ...m,
        {
          role: "assistant",
          text: data.final_response || `(status=${data.status})`,
        },
      ]);
      // opportunistic RAG + tool probe for inspector (real APIs)
      const [search, toolList] = await Promise.all([
        api<{ citations?: Array<Record<string, unknown>>; results?: Array<Record<string, unknown>> }>(
          "/rag/search",
          {
            method: "POST",
            body: JSON.stringify({ query: userText, top_k: 3 }),
          },
        ),
        api<{ tools?: Array<Record<string, unknown>> }>("/mcp/tools"),
      ]);
      setRag(search.data.citations || search.data.results || []);
      setTools((toolList.data.tools || []).slice(0, 8));
      if (data.status === "awaiting_approval") setTab("approval");
      else if ((data.steps || []).length) setTab("steps");
      else setTab("result");
    } catch (ex) {
      setErr(ex instanceof Error ? ex.message : String(ex));
    } finally {
      setBusy(false);
    }
  }

  async function decide(action: "approve" | "reject") {
    const id = String(wf?.approval?.approval_id || wf?.approval?.id || "");
    if (!id) {
      setErr("No approval_id on workflow");
      return;
    }
    setBusy(true);
    try {
      const { ok, data } = await api<Wf & { detail?: string }>(`/approvals/${id}/decide`, {
        method: "POST",
        body: JSON.stringify({ action, decided_by: "ui-admin", note: `ui ${action}` }),
      });
      if (!ok) {
        setErr(data.detail || "decide failed");
        return;
      }
      setWf(data);
      setMsgs((m) => [
        ...m,
        { role: "assistant", text: data.final_response || `Decision ${action}: ${data.status}` },
      ]);
      setTab("result");
    } finally {
      setBusy(false);
    }
  }

  return (
    <Shell title="Chat / Workflow">
      {err && <div className="errbox mb">{err}</div>}
      <div className="split-chat">
        <div className="chat-pane">
          <div className="chat-log">
            {msgs.length === 0 && (
              <div className="empty">
                Run a real workflow. Example: create ACME Laptop order, or ask about return policy.
              </div>
            )}
            {msgs.map((m, i) => (
              <div key={i} className={`bubble ${m.role}`}>
                {m.text}
              </div>
            ))}
          </div>
          <form className="chat-input" onSubmit={run}>
            <textarea
              className="textarea"
              value={input}
              onChange={(e) => setInput(e.target.value)}
              placeholder="Create an order for 1 Laptop Pro 14 for ACME"
              onKeyDown={(e) => {
                if (e.key === "Enter" && (e.metaKey || e.ctrlKey)) run();
              }}
            />
            <button className="btn primary" type="submit" disabled={busy}>
              {busy ? "…" : "Send"}
            </button>
          </form>
        </div>

        <div className="inspect-pane">
          <div className="tabs">
            {(["steps", "tools", "rag", "approval", "result"] as const).map((t) => (
              <button
                key={t}
                type="button"
                className={`tab ${tab === t ? "active" : ""}`}
                onClick={() => setTab(t)}
              >
                {t}
                {t === "steps" && steps.length ? ` (${steps.length})` : ""}
              </button>
            ))}
          </div>
          <div className="inspect-body">
            <div className="row mb" style={{ gap: "0.75rem" }}>
              <StatusChip status={wf?.status} />
              {wf?.workflow_id && <span className="mono">{wf.workflow_id}</span>}
              {wf?.intent && <span className="chip neutral">{wf.intent}</span>}
            </div>

            {tab === "steps" &&
              (steps.length ? (
                steps.map((s, i) => (
                  <div className="step" key={`${s}-${i}`}>
                    <span className="n">{i + 1}</span>
                    <span className="mono">{s}</span>
                  </div>
                ))
              ) : (
                <div className="empty">No agent steps yet.</div>
              ))}

            {tab === "tools" &&
              (tools.length ? (
                tools.map((t, i) => (
                  <div className="toolcard" key={i}>
                    {JSON.stringify(t, null, 2)}
                  </div>
                ))
              ) : (
                <div className="empty">Tool catalog loads after a run (GET /mcp/tools).</div>
              ))}

            {tab === "rag" &&
              (rag.length ? (
                rag.map((c, i) => (
                  <div className="cite" key={i}>
                    <div className="src">
                      {String(c.source || c.document || "policy")} · score{" "}
                      {String(c.score ?? c.similarity ?? "—")}
                    </div>
                    <div style={{ marginTop: 6, fontSize: "0.85rem" }}>
                      {String(c.text || c.content || c.chunk || "").slice(0, 400)}
                    </div>
                  </div>
                ))
              ) : (
                <div className="empty">No RAG hits for last query.</div>
              ))}

            {tab === "approval" &&
              (wf?.approval ? (
                <div>
                  <div className="mb">
                    <StatusChip status={String(wf.status)} />
                  </div>
                  <pre className="toolcard">{JSON.stringify(wf.approval, null, 2)}</pre>
                  {wf.status === "awaiting_approval" && (
                    <div className="row mt">
                      <button className="btn ok" type="button" disabled={busy} onClick={() => decide("approve")}>
                        Approve
                      </button>
                      <button
                        className="btn danger"
                        type="button"
                        disabled={busy}
                        onClick={() => decide("reject")}
                      >
                        Reject
                      </button>
                    </div>
                  )}
                </div>
              ) : (
                <div className="empty">No approval required on current workflow.</div>
              ))}

            {tab === "result" &&
              (wf ? (
                <div>
                  <div className="okbox mb mono" style={{ whiteSpace: "pre-wrap" }}>
                    {wf.final_response || "(no final_response)"}
                  </div>
                  <pre className="toolcard">
                    {JSON.stringify(
                      {
                        status: wf.status,
                        workflow_id: wf.workflow_id,
                        request_id: wf.request_id,
                        session_id: wf.session_id,
                        intent: wf.intent,
                        error: wf.error,
                      },
                      null,
                      2,
                    )}
                  </pre>
                </div>
              ) : (
                <div className="empty">Run a workflow to see the result.</div>
              ))}
          </div>
        </div>
      </div>
    </Shell>
  );
}
