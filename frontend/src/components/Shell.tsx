"use client";

import Link from "next/link";
import { usePathname, useRouter } from "next/navigation";
import { ReactNode, useEffect, useState } from "react";
import { api, logout, sessionUser } from "@/lib/api";

const NAV = [
  { href: "/dashboard", label: "Dashboard" },
  { href: "/chat", label: "Chat" },
  { href: "/orders", label: "Orders" },
  { href: "/approvals", label: "Approvals" },
  { href: "/traces", label: "Traces" },
  { href: "/evaluations", label: "Evaluations" },
  { href: "/knowledge", label: "Knowledge" },
  { href: "/health", label: "Health" },
];

export function Shell({ title, children }: { title: string; children: ReactNode }) {
  const path = usePathname();
  const router = useRouter();
  const [user, setUser] = useState<string | null>(null);
  const [role, setRole] = useState<string | null>(null);
  const [health, setHealth] = useState<{ api: boolean; db: boolean; redis: boolean }>({
    api: false,
    db: false,
    redis: false,
  });

  useEffect(() => {
    const s = sessionUser();
    setUser(s.user);
    setRole(s.role);
    if (!s.user && path !== "/login") router.replace("/login");
    (async () => {
      const [a, d, r] = await Promise.all([
        api("/health"),
        api("/health/db"),
        api("/health/redis"),
      ]);
      setHealth({ api: a.ok, db: d.ok, redis: r.ok });
    })();
  }, [path, router]);

  return (
    <div className="shell">
      <aside className="sidebar">
        <div className="brand">
          <h1>EnterpriseFlow</h1>
          <p>AI Ops Console · Stitch DS</p>
        </div>
        <nav className="nav">
          {NAV.map((n) => (
            <Link key={n.href} href={n.href} className={path.startsWith(n.href) ? "active" : ""}>
              {n.label}
            </Link>
          ))}
        </nav>
        <div className="userchip">
          <span>
            <span className={`dot ${user ? "ok" : "warn"}`} />
            {user || "guest"} · {role || "—"}
          </span>
          <button
            className="btn sm"
            type="button"
            onClick={() => {
              logout();
              router.push("/login");
            }}
          >
            Out
          </button>
        </div>
      </aside>
      <div className="main">
        <header className="topbar">
          <h2>{title}</h2>
          <div className="health-row">
            <span>
              <span className={`dot ${health.api ? "ok" : "err"}`} />
              API
            </span>
            <span>
              <span className={`dot ${health.db ? "ok" : "err"}`} />
              DB
            </span>
            <span>
              <span className={`dot ${health.redis ? "ok" : "err"}`} />
              Redis
            </span>
          </div>
        </header>
        <div className="content">{children}</div>
      </div>
    </div>
  );
}

export function StatusChip({ status }: { status?: string | null }) {
  const s = (status || "unknown").toLowerCase();
  let cls = "neutral";
  if (s.includes("ok") || s.includes("complete") || s.includes("approved") || s === "reserved") cls = "ok";
  else if (s.includes("await") || s.includes("pending")) cls = "await";
  else if (s.includes("fail") || s.includes("error") || s.includes("reject")) cls = "err";
  else if (s.includes("warn")) cls = "warn";
  return <span className={`chip ${cls}`}>{status || "—"}</span>;
}
