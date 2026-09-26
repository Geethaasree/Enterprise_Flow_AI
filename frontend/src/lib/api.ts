const API_BASE =
  typeof window === "undefined"
    ? process.env.API_INTERNAL_URL || process.env.NEXT_PUBLIC_API_URL || "http://127.0.0.1:8010"
    : process.env.NEXT_PUBLIC_API_URL || "/backend";

export type Json = Record<string, unknown>;

function authHeaders(): HeadersInit {
  if (typeof window === "undefined") return {};
  const token = localStorage.getItem("ef_token");
  const role = localStorage.getItem("ef_role") || "admin";
  const h: Record<string, string> = { "Content-Type": "application/json" };
  if (token) h.Authorization = `Bearer ${token}`;
  else h["X-Role"] = role;
  return h;
}

export async function api<T = Json>(
  path: string,
  init: RequestInit = {},
): Promise<{ ok: boolean; status: number; data: T }> {
  const res = await fetch(`${API_BASE}${path}`, {
    ...init,
    headers: { ...authHeaders(), ...(init.headers || {}) },
    cache: "no-store",
  });
  let data = {} as T;
  try {
    data = (await res.json()) as T;
  } catch {
    /* empty */
  }
  return { ok: res.ok, status: res.status, data };
}

export async function login(username: string, password: string) {
  const { ok, data, status } = await api<{
    access_token?: string;
    role?: string;
    detail?: string;
  }>("/auth/token", {
    method: "POST",
    body: JSON.stringify({ username, password }),
  });
  if (!ok || !data.access_token) {
    throw new Error(data.detail || `login failed (${status})`);
  }
  localStorage.setItem("ef_token", data.access_token);
  localStorage.setItem("ef_role", data.role || "sales");
  localStorage.setItem("ef_user", username);
  return data;
}

export function logout() {
  localStorage.removeItem("ef_token");
  localStorage.removeItem("ef_role");
  localStorage.removeItem("ef_user");
}

export function sessionUser() {
  if (typeof window === "undefined") return { user: null as string | null, role: null as string | null };
  return {
    user: localStorage.getItem("ef_user"),
    role: localStorage.getItem("ef_role"),
  };
}
