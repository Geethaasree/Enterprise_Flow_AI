"use client";

import { FormEvent, useState } from "react";
import { useRouter } from "next/navigation";
import { login } from "@/lib/api";

export default function LoginPage() {
  const router = useRouter();
  const [username, setUsername] = useState("admin");
  const [password, setPassword] = useState("admin");
  const [err, setErr] = useState<string | null>(null);
  const [busy, setBusy] = useState(false);

  async function onSubmit(e: FormEvent) {
    e.preventDefault();
    setBusy(true);
    setErr(null);
    try {
      await login(username, password);
      router.replace("/dashboard");
    } catch (ex) {
      setErr(ex instanceof Error ? ex.message : String(ex));
    } finally {
      setBusy(false);
    }
  }

  return (
    <div className="login-wrap">
      <form className="card login-card" onSubmit={onSubmit}>
        <h2 style={{ marginTop: 0, fontFamily: "var(--head)" }}>EnterpriseFlow</h2>
        <p className="sub" style={{ color: "var(--muted)", marginTop: 0 }}>
          Sign in with demo JWT (admin / admin or demo / demo)
        </p>
        {err && <div className="errbox">{err}</div>}
        <label className="mb" style={{ display: "block" }}>
          <div style={{ fontSize: "0.8rem", color: "var(--muted)", marginBottom: 4 }}>Username</div>
          <input className="input" value={username} onChange={(e) => setUsername(e.target.value)} />
        </label>
        <label className="mb" style={{ display: "block" }}>
          <div style={{ fontSize: "0.8rem", color: "var(--muted)", marginBottom: 4 }}>Password</div>
          <input
            className="input"
            type="password"
            value={password}
            onChange={(e) => setPassword(e.target.value)}
          />
        </label>
        <button className="btn primary" type="submit" disabled={busy} style={{ width: "100%" }}>
          {busy ? "Signing in…" : "Sign in"}
        </button>
      </form>
    </div>
  );
}
