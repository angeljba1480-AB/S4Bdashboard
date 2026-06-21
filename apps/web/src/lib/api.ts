// Thin typed client over the Private AI Platform API.
import type {
  Agent,
  AuditEvent,
  ChatResponse,
  DocumentItem,
  Me,
  UsageSummary,
} from "@shared/types";

const API_BASE =
  process.env.NEXT_PUBLIC_API_BASE_URL?.replace(/\/$/, "") || "http://localhost:8000";

const TOKEN_KEY = "pai_token";

export function getToken(): string | null {
  if (typeof window === "undefined") return null;
  return window.localStorage.getItem(TOKEN_KEY);
}
export function setToken(token: string) {
  window.localStorage.setItem(TOKEN_KEY, token);
}
export function clearToken() {
  window.localStorage.removeItem(TOKEN_KEY);
}

async function request<T>(path: string, options: RequestInit = {}): Promise<T> {
  const token = getToken();
  const headers: Record<string, string> = {
    ...(options.headers as Record<string, string>),
  };
  if (!(options.body instanceof FormData)) headers["Content-Type"] = "application/json";
  if (token) headers["Authorization"] = `Bearer ${token}`;

  const res = await fetch(`${API_BASE}${path}`, { ...options, headers });
  if (res.status === 401 && typeof window !== "undefined") {
    clearToken();
    if (!window.location.pathname.includes("/login")) window.location.href = "/login";
  }
  if (!res.ok) {
    let detail = res.statusText;
    try {
      detail = (await res.json()).detail || detail;
    } catch {
      /* ignore */
    }
    throw new Error(detail);
  }
  if (res.status === 204) return undefined as T;
  return res.json() as Promise<T>;
}

export const api = {
  base: API_BASE,
  async login(email: string, password: string) {
    const data = await request<{ access_token: string }>("/auth/login", {
      method: "POST",
      body: JSON.stringify({ email, password }),
    });
    setToken(data.access_token);
    return data;
  },
  me: () => request<Me>("/me"),
  agents: () => request<Agent[]>("/agents"),
  agent: (id: string) => request<Agent>(`/agents/${id}`),
  createAgent: (body: Partial<Agent>) =>
    request<Agent>("/agents", { method: "POST", body: JSON.stringify(body) }),
  documents: () => request<DocumentItem[]>("/documents"),
  uploadText: (filename: string, text: string) => {
    const fd = new FormData();
    fd.append("filename", filename);
    fd.append("text", text);
    return request<DocumentItem>("/documents/upload", { method: "POST", body: fd });
  },
  uploadFile: (file: File) => {
    const fd = new FormData();
    fd.append("file", file);
    return request<DocumentItem>("/documents/upload", { method: "POST", body: fd });
  },
  chat: (body: {
    agent_id: string;
    prompt: string;
    conversation_id?: string;
    document_ids?: string[];
  }) => request<ChatResponse>("/chat", { method: "POST", body: JSON.stringify(body) }),
  audit: (params?: { event_type?: string; risk_level?: string }) => {
    const q = new URLSearchParams(params as Record<string, string>).toString();
    return request<AuditEvent[]>(`/audit${q ? `?${q}` : ""}`);
  },
  usage: () => request<UsageSummary>("/usage"),
  workflows: () => request<{ id: string; name: string; steps: string }[]>("/workflows"),
  runWorkflow: (id: string) =>
    request<{ run_id: string; status: string; steps: string }>(`/workflows/${id}/run`, {
      method: "POST",
    }),
  routes: () =>
    request<{ route: string; enabled: boolean; model: string; mode: string }[]>("/admin/routes"),
  users: () =>
    request<{ id: string; email: string; name: string; role: string; mfa_enabled: boolean }[]>(
      "/admin/users",
    ),
};
