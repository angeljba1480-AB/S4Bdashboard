// Thin typed client over the Private AI Platform API.
import type {
  Agent,
  AuditEvent,
  ChatResponse,
  DocumentItem,
  Me,
  Recipe,
  RecipeRun,
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
  recipes: (params?: { category?: string; q?: string }) => {
    const qs = new URLSearchParams();
    if (params?.category) qs.set("category", params.category);
    if (params?.q) qs.set("q", params.q);
    const suffix = qs.toString() ? `?${qs}` : "";
    return request<Recipe[]>(`/recipes${suffix}`);
  },
  recipeCategories: () =>
    request<{ id: string; label: string; count: number }[]>("/recipes/categories"),
  proposeRecipe: (body: { title: string; description?: string; category?: string }) =>
    request<{ id: string; title: string; status: string }>("/recipes/propose", {
      method: "POST",
      body: JSON.stringify(body),
    }),
  recipeProposals: () =>
    request<{ id: string; title: string; description: string; category: string; status: string }[]>(
      "/recipes/proposals",
    ),
  curateProposal: (
    id: string,
    body: { name?: string; category?: string; inputs?: unknown[]; prompt?: string; produces?: string },
  ) =>
    request<{ id: string; slug: string; name: string; status: string }>(
      `/recipes/proposals/${id}/curate`,
      { method: "POST", body: JSON.stringify(body) },
    ),
  rejectProposal: (id: string) =>
    request<{ id: string; status: string }>(`/recipes/proposals/${id}/reject`, { method: "POST" }),
  startRecipe: (id: string, inputs: Record<string, unknown>) =>
    request<RecipeRun>(`/recipes/${id}/start`, { method: "POST", body: JSON.stringify({ inputs }) }),
  recipeRun: (runId: string) => request<RecipeRun>(`/recipes/runs/${runId}`),
  approveRun: (runId: string) =>
    request<RecipeRun>(`/recipes/runs/${runId}/approve`, { method: "POST" }),
  async downloadRun(runId: string, format: "pdf" | "md" = "pdf") {
    const res = await fetch(`${API_BASE}/recipes/runs/${runId}/export?format=${format}`, {
      headers: { Authorization: `Bearer ${getToken()}` },
    });
    if (!res.ok) throw new Error("No se pudo exportar el resultado");
    const blob = await res.blob();
    const url = URL.createObjectURL(blob);
    const a = document.createElement("a");
    a.href = url;
    a.download = `caso-${runId}.${format}`;
    document.body.appendChild(a);
    a.click();
    a.remove();
    URL.revokeObjectURL(url);
  },
  approveConnection: (connId: string) =>
    request<{ id: string; status: string }>(`/recipes/connections/${connId}/approve`, {
      method: "POST",
      body: JSON.stringify({ prefs: {} }),
    }),
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
  previewRoute: (body: { agent_id: string; prompt: string; document_ids?: string[] }) =>
    request<{
      classification: string;
      route: string;
      pii_types: string[];
      pii_score: number;
      reason: string;
      level: "info" | "warn" | "block";
      message: string;
      requires_approval: boolean;
      sources_found: number;
    }>("/chat/preview", { method: "POST", body: JSON.stringify(body) }),
  audit: (params?: { event_type?: string; risk_level?: string }) => {
    const q = new URLSearchParams(params as Record<string, string>).toString();
    return request<AuditEvent[]>(`/audit${q ? `?${q}` : ""}`);
  },
  usage: () => request<UsageSummary>("/usage"),
  workflows: () => request<{ id: string; name: string; steps: string }[]>("/workflows"),
  runWorkflow: (id: string) =>
    request<{ run_id: string; status: string; engine: string; detail: string; steps: string }>(
      `/workflows/${id}/run`,
      { method: "POST" },
    ),
  routes: () =>
    request<{ route: string; provider: string; enabled: boolean; model: string; mode: string }[]>(
      "/admin/routes",
    ),
  users: () =>
    request<{ id: string; email: string; name: string; role: string; mfa_enabled: boolean }[]>(
      "/admin/users",
    ),
  security: () =>
    request<{
      encryption_at_rest: { enabled: boolean; algo: string; kms_key_version: number };
      vector_store: string;
      sso: { enabled: boolean; issuer: string | null };
      fallback_order: string[];
      workflows: { engine: string; base_url: string | null };
    }>("/admin/security"),
  ssoConfig: () => request<{ enabled: boolean; authorize_url?: string }>("/auth/sso/config"),
  getN8n: () =>
    request<{
      tenant_override: boolean;
      webhook_base_url: string | null;
      auth_header: string;
      has_api_key: boolean;
      effective_source: string;
      managed_available: boolean;
      auto_provision: boolean;
      provisioned: boolean;
    }>("/admin/n8n"),
  setN8n: (body: { webhook_base_url: string; api_key?: string; auth_header?: string }) =>
    request<{ engine: string; source: string; base_url: string | null }>("/admin/n8n", {
      method: "PUT",
      body: JSON.stringify(body),
    }),
  provisionN8n: () =>
    request<{ provisioned: boolean; created?: string[]; reason?: string }>("/admin/n8n/provision", {
      method: "POST",
    }),
  // Downloads (return URLs with auth handled by the browser fetch + blob).
  async download(path: string, filename: string) {
    const res = await fetch(`${API_BASE}${path}`, {
      headers: getToken() ? { Authorization: `Bearer ${getToken()}` } : {},
    });
    if (!res.ok) throw new Error("Export falló");
    const blob = await res.blob();
    const url = URL.createObjectURL(blob);
    const a = document.createElement("a");
    a.href = url;
    a.download = filename;
    a.click();
    URL.revokeObjectURL(url);
  },
  exportConversation: (id: string, format: "pdf" | "md") =>
    api.download(`/export/conversation/${id}?format=${format}`, `conversacion.${format}`),
  exportAudit: () => api.download("/audit/export", "audit.jsonl"),
};
