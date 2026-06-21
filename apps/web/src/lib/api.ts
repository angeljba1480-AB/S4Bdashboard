// Thin typed client over the Private AI Platform API.
import type {
  Agent,
  AppProject,
  AuditEvent,
  ChatResponse,
  DocumentItem,
  Eje,
  Me,
  Procedure,
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
  // Billing / seats
  getBilling: () =>
    request<{
      plan: string;
      subscription_status: string;
      renews_at: string | null;
      setup_fee_paid: boolean;
      annual_fee_mxn: number;
      seats_licensed: number;
      seats_used: number;
      seats_available: number;
      prod_deploy_price_mxn: number;
    }>("/admin/billing"),
  updateBilling: (body: Partial<{ seats_licensed: number; annual_fee_mxn: number; subscription_status: string; subscription_renews_at: string; setup_fee_paid: boolean; plan: string }>) =>
    request<{ ok: boolean }>("/admin/billing", { method: "PUT", body: JSON.stringify(body) }),
  createUser: (body: { email: string; name: string; role?: string }) =>
    request<{ id: string; email: string }>("/admin/users", { method: "POST", body: JSON.stringify(body) }),
  // Regional catalog
  regionalEjes: () => request<Eje[]>("/regional/ejes"),
  regionalCountries: () =>
    request<{ code: string; name: string; division_label: string }[]>("/regional/countries"),
  regionalDivisions: (country?: string) =>
    request<{ country: string; division_label: string; divisions: string[] }>(
      `/regional/divisions${country ? `?country=${country}` : ""}`,
    ),
  regionalProcedures: (p?: { estado?: string; eje?: string; q?: string; country?: string }) => {
    const qs = new URLSearchParams();
    if (p?.estado) qs.set("estado", p.estado);
    if (p?.eje) qs.set("eje", p.eje);
    if (p?.q) qs.set("q", p.q);
    if (p?.country) qs.set("country", p.country);
    const s = qs.toString() ? `?${qs}` : "";
    return request<Procedure[]>(`/regional/procedures${s}`);
  },
  procedureToProposal: (id: string) =>
    request<{ id: string; title: string; status: string }>(`/regional/procedures/${id}/propose`, {
      method: "POST",
    }),
  // Trámites (curated KB / company MCP layer)
  tramites: (p?: { q?: string; region?: string; municipio?: string; country?: string }) => {
    const qs = new URLSearchParams();
    Object.entries(p || {}).forEach(([k, v]) => v && qs.set(k, v));
    const s = qs.toString() ? `?${qs}` : "";
    return request<{ id: string; title: string; authority: string; source: string; scope: string; region: string }[]>(`/tramites${s}`);
  },
  addCompanyTramite: (body: { title: string; authority?: string; region?: string; municipio?: string; requisitos?: string[]; pasos?: string[]; costo_aprox?: string; fuente?: string; keywords?: string[] }) =>
    request<{ id: string; title: string }>("/tramites", { method: "POST", body: JSON.stringify(body) }),
  importTramite: (documentId: string) =>
    request<{ id: string; title: string }>("/tramites/import", { method: "POST", body: JSON.stringify({ document_id: documentId }) }),
  // Dashboard builder
  dashboards: () =>
    request<{ id: string; name: string; description: string; spec: unknown[]; workflow_id: string | null }[]>("/dashboards"),
  suggestDashboard: (description: string) =>
    request<{ spec: { id: string; type: string; title: string; source: string; key: string }[] }>("/dashboards/suggest", {
      method: "POST",
      body: JSON.stringify({ description }),
    }),
  createDashboard: (body: { name: string; description: string; spec?: unknown[]; workflow_id?: string }) =>
    request<{ id: string; name: string }>("/dashboards", { method: "POST", body: JSON.stringify(body) }),
  dashboardData: (id: string) =>
    request<{ id: string; name: string; workflow_id: string | null; widgets: { id: string; type: string; title: string; source?: string; key?: string; value?: number; series?: { name: string; value: number }[]; rows?: Record<string, unknown>[] }[] }>(`/dashboards/${id}/data`),
  dashboardCatalog: () =>
    request<{ key: string; type: string; title: string }[]>("/dashboards/catalog"),
  updateDashboard: (id: string, body: { name: string; description: string; spec?: unknown[]; workflow_id?: string }) =>
    request<{ id: string; name: string }>(`/dashboards/${id}`, { method: "PUT", body: JSON.stringify(body) }),
  deleteDashboard: (id: string) => request<{ ok: boolean }>(`/dashboards/${id}`, { method: "DELETE" }),
  // App Studio
  apps: () => request<AppProject[]>("/apps"),
  createApp: (body: { name: string; description: string }) =>
    request<AppProject>("/apps", { method: "POST", body: JSON.stringify(body) }),
  confirmCheckout: (id: string) =>
    request<{ id: string; paid: boolean }>(`/apps/${id}/checkout`, { method: "POST" }),
  async deployApp(id: string): Promise<{ payment_required: boolean; checkout?: { amount: number; currency: string }; app?: AppProject }> {
    const res = await fetch(`${API_BASE}/apps/${id}/deploy`, {
      method: "POST",
      headers: { Authorization: `Bearer ${getToken()}` },
    });
    const data = await res.json().catch(() => ({}));
    if (res.status === 402) return { payment_required: true, checkout: data.detail?.checkout };
    if (!res.ok) throw new Error(typeof data.detail === "string" ? data.detail : "No se pudo publicar");
    return { payment_required: false, app: data };
  },
  getBranding: () =>
    request<{ brand_name: string; brand_logo_url: string; brand_color: string; brand_tagline: string; tenant_name: string; country: string }>(
      "/admin/branding",
    ),
  setBranding: (body: { brand_name: string; brand_logo_url: string; brand_color: string; brand_tagline: string; country?: string }) =>
    request<{ brand_name: string; brand_color: string }>("/admin/branding", {
      method: "PUT",
      body: JSON.stringify(body),
    }),
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
  operations: () =>
    request<{
      cases: { total: number; completed: number; in_progress: number; by_status: Record<string, number>; by_recipe: Record<string, number> };
      searches: number;
      tokens: { total: number; by_source: Record<string, number> };
      cost: { total: number };
      apps: { built: number; deployed: number };
      recent_cases: { id: string; recipe: string; status: string; tokens: number; cost: number; created_at: string }[];
    }>("/usage/operations"),
  account: () =>
    request<{
      user: { id: string; email: string; name: string; role: string };
      license: { type: string; status: string; seat_assigned: boolean };
      company: { name: string; plan: string; subscription_status: string; renews_at: string | null; seats_licensed: number; seats_used: number; seats_available: number };
      licensed_users: { name: string; email: string; role: string; status: string }[];
    }>("/account"),
  plans: () =>
    request<{ currency: string; plans: { id: string; name: string; audience: string; setup_fee: number | null; annual_per_seat: number | null; seats_range: string; prod_deploy_price: number | null; includes: string[]; recommended_for: string[] }[] }>("/admin/plans"),
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
