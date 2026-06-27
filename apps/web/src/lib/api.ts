// Thin typed client over the MaestroAI API.
import type {
  ActionRequestItem,
  Agent,
  MemoryItem,
  AppProject,
  AuditEvent,
  ChatResponse,
  CompanyProfile,
  DocumentCategory,
  DocumentItem,
  Eje,
  Flowchart,
  FlowchartSummary,
  Notebook,
  NotebookAnswer,
  Me,
  Procedure,
  Recipe,
  RecipeRun,
  UsageSummary,
} from "@shared/types";

export type GeneratedImageDto = {
  id: string;
  prompt: string;
  model: string;
  size: string;
  provider: string;
  area: string;
  has_data: boolean;
  source_url: string;
  created_at: string;
};

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
  async login(email: string, password: string, mfaCode?: string) {
    const data = await request<{ access_token: string }>("/auth/login", {
      method: "POST",
      body: JSON.stringify({ email, password, mfa_code: mfaCode }),
    });
    setToken(data.access_token);
    return data;
  },
  me: () => request<Me>("/me"),
  // MFA (TOTP)
  mfaSetup: () => request<{ secret: string; otpauth_uri: string; issuer: string }>("/auth/mfa/setup", { method: "POST" }),
  mfaVerify: (code: string) => request<{ enabled: boolean; backup_codes: string[] }>("/auth/mfa/verify", { method: "POST", body: JSON.stringify({ code }) }),
  mfaDisable: (code: string) => request<{ enabled: boolean }>("/auth/mfa/disable", { method: "POST", body: JSON.stringify({ code }) }),
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
  createUser: (body: { email: string; name: string; role?: string; area?: string; license?: string }) =>
    request<{ id: string; email: string }>("/admin/users", { method: "POST", body: JSON.stringify(body) }),
  updateUser: (id: string, body: { name?: string; role?: string; area?: string; license?: string; status?: string }) =>
    request<{ id: string; role: string; area: string; license: string }>(
      `/admin/users/${id}`, { method: "PATCH", body: JSON.stringify(body) }),
  adminTenants: () =>
    request<{ id: string; name: string; plan: string; subscription_status: string; country: string; seats_licensed: number; users: number; documents: number }[]>(
      "/admin/tenants"),
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
  // Automations
  automationTemplates: () =>
    request<{ id: string; name: string; description: string; trigger: string; schedule: string; event: string; action_type: string }[]>("/automations/templates"),
  automations: () =>
    request<{ id: string; name: string; description: string; trigger: string; schedule: string; event: string; action_type: string; action_ref: string; enabled: boolean; status: string; last_run: string | null }[]>("/automations"),
  createAutomationFromTemplate: (templateId: string) =>
    request<{ id: string; name: string }>("/automations/from-template", { method: "POST", body: JSON.stringify({ template_id: templateId }) }),
  createAutomation: (body: { name: string; trigger: string; schedule?: string; event?: string; action_type: string; action_ref?: string; config?: Record<string, unknown> }) =>
    request<{ id: string; name: string }>("/automations", { method: "POST", body: JSON.stringify(body) }),
  // Integrations: connectors + API keys
  connectors: () =>
    request<{ id: string; kind: string; name: string; base_url: string; auth_header: string; has_token: boolean; enabled: boolean; example: { base_url?: string; auth_header?: string; auth_hint?: string; payload_example?: Record<string, unknown> } }[]>("/integrations/connectors"),
  createConnector: (body: { kind: string; name: string; base_url: string; auth_header?: string; token?: string }) =>
    request<{ id: string; name: string }>("/integrations/connectors", { method: "POST", body: JSON.stringify(body) }),
  testConnector: (id: string) => request<{ status: string; detail: string }>(`/integrations/connectors/${id}/test`, { method: "POST" }),
  revealConnector: (id: string) => request<{ auth_header: string; token: string }>(`/integrations/connectors/${id}/reveal`),
  deleteConnector: (id: string) => request<{ ok: boolean }>(`/integrations/connectors/${id}`, { method: "DELETE" }),
  connectorTemplates: () =>
    request<{ id: string; kind: string; name: string; auth_header: string; base_url: string; auth_hint: string; payload_example: Record<string, unknown> }[]>("/integrations/connector-templates"),
  webhooks: () =>
    request<{ id: string; name: string; default_event: string; enabled: boolean; url: string }[]>("/integrations/webhooks"),
  createWebhook: (body: { name: string; default_event: string }) =>
    request<{ id: string; name: string; url: string; secret: string }>("/integrations/webhooks", { method: "POST", body: JSON.stringify(body) }),
  deleteWebhook: (id: string) => request<{ ok: boolean }>(`/integrations/webhooks/${id}`, { method: "DELETE" }),
  apiKeys: () => request<{ id: string; name: string; prefix: string; status: string }[]>("/admin/api-keys"),
  createApiKey: (name: string) => request<{ id: string; name: string; api_key: string }>("/admin/api-keys", { method: "POST", body: JSON.stringify({ name }) }),
  revokeApiKey: (id: string) => request<{ id: string; status: string }>(`/admin/api-keys/${id}/revoke`, { method: "POST" }),
  toggleAutomation: (id: string) =>
    request<{ id: string; enabled: boolean }>(`/automations/${id}/toggle`, { method: "POST" }),
  runAutomation: (id: string) =>
    request<{ id: string; status: string; detail: string; last_run: string }>(`/automations/${id}/run`, { method: "POST" }),
  deleteAutomation: (id: string) =>
    request<{ ok: boolean }>(`/automations/${id}`, { method: "DELETE" }),
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
  // Mailbox OAuth (Outlook / Gmail)
  oauthProviders: () =>
    request<{
      providers: { provider: string; label: string; kind: string; enabled: boolean; configured: boolean }[];
      connections: { id: string; provider: string; label: string; identifier: string }[];
    }>("/oauth/providers"),
  oauthAuthorize: (provider: string) =>
    request<{ authorize_url: string }>(`/oauth/${provider}/authorize`),
  oauthDisconnect: (provider: string) =>
    request<{ ok: boolean }>(`/oauth/${provider}`, { method: "DELETE" }),
  oauthDisconnectConnection: (connId: string) =>
    request<{ ok: boolean }>(`/oauth/connection/${connId}`, { method: "DELETE" }),
  connectImap: (body: { host: string; port: number; email: string; password: string }) =>
    request<{ ok: boolean; identifier: string }>("/oauth/imap", { method: "POST", body: JSON.stringify(body) }),
  // Company configuration (onboarding workflow)
  companyProfile: () => request<CompanyProfile>("/company/profile"),
  saveCompanyProfile: (body: Partial<CompanyProfile>) =>
    request<CompanyProfile>("/company/profile", { method: "PUT", body: JSON.stringify(body) }),
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
  async downloadRun(runId: string, format: "pdf" | "md" | "docx" | "pptx" | "xlsx" = "pdf") {
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
  documents: (params?: { area?: string; category?: string }) => {
    const qs = new URLSearchParams();
    if (params?.area) qs.set("area", params.area);
    if (params?.category) qs.set("category", params.category);
    const q = qs.toString();
    return request<DocumentItem[]>(`/documents${q ? `?${q}` : ""}`);
  },
  uploadText: (filename: string, text: string, meta?: { area?: string; category?: string; sensitivity?: string }) => {
    const fd = new FormData();
    fd.append("filename", filename);
    fd.append("text", text);
    if (meta?.area) fd.append("area", meta.area);
    if (meta?.category) fd.append("category", meta.category);
    if (meta?.sensitivity) fd.append("sensitivity", meta.sensitivity);
    return request<DocumentItem>("/documents/upload", { method: "POST", body: fd });
  },
  uploadFile: (file: File, meta?: { area?: string; category?: string; sensitivity?: string }) => {
    const fd = new FormData();
    fd.append("file", file);
    if (meta?.area) fd.append("area", meta.area);
    if (meta?.category) fd.append("category", meta.category);
    if (meta?.sensitivity) fd.append("sensitivity", meta.sensitivity);
    return request<DocumentItem>("/documents/upload", { method: "POST", body: fd });
  },
  deleteDocument: (id: string) =>
    request<{ ok: boolean }>(`/documents/${id}`, { method: "DELETE" }),
  updateDocument: (id: string, body: { area?: string; category?: string; sensitivity?: string }) =>
    request<DocumentItem>(`/documents/${id}`, { method: "PATCH", body: JSON.stringify(body) }),
  driveFiles: (query?: string) =>
    request<{ files: { id: string; name: string; mime_type: string; is_folder: boolean; modified: string }[] }>(
      `/drive/files${query ? `?query=${encodeURIComponent(query)}` : ""}`),
  driveImport: (body: { file_id: string; name: string; mime_type: string; area?: string; category?: string }) =>
    request<{ id: string; filename: string }>("/drive/import", { method: "POST", body: JSON.stringify(body) }),
  // Memory + tags
  memory: (params?: { q?: string; tag?: string }) => {
    const qs = new URLSearchParams();
    if (params?.q) qs.set("q", params.q);
    if (params?.tag) qs.set("tag", params.tag);
    const s = qs.toString();
    return request<MemoryItem[]>(`/memory${s ? `?${s}` : ""}`);
  },
  memoryTags: () => request<string[]>("/memory/tags"),
  createMemory: (body: { title: string; content: string; tags?: string[]; source?: string; source_id?: string; area?: string }) =>
    request<MemoryItem>("/memory", { method: "POST", body: JSON.stringify(body) }),
  deleteMemory: (id: string) => request<{ ok: boolean }>(`/memory/${id}`, { method: "DELETE" }),
  // Google/Microsoft action toolkit
  actions: () => request<{ id: string; provider: string; label: string; write: boolean; params: string[]; connected: boolean; granted: boolean }[]>("/actions"),
  runAction: (action: string, params: Record<string, string>) =>
    request<{ status: string; request: ActionRequestItem }>("/actions/run", { method: "POST", body: JSON.stringify({ action, params }) }),
  actionRequests: (status?: string) =>
    request<ActionRequestItem[]>(`/actions/requests${status ? `?status=${status}` : ""}`),
  approveAction: (id: string, always = false) =>
    request<{ request: ActionRequestItem }>(`/actions/requests/${id}/approve${always ? "?always=true" : ""}`, { method: "POST" }),
  rejectAction: (id: string) =>
    request<{ request: ActionRequestItem }>(`/actions/requests/${id}/reject`, { method: "POST" }),
  actionGrants: () => request<{ action: string; label: string }[]>("/actions/grants"),
  revokeGrant: (action: string) => request<{ ok: boolean }>(`/actions/grants/${action}`, { method: "DELETE" }),
  flowcharts: () => request<FlowchartSummary[]>("/flowcharts"),
  flowchart: (id: string) => request<Flowchart>(`/flowcharts/${id}`),
  // Data sources (legacy connectors: read-only DB → RAG)
  dataSources: () =>
    request<{ id: string; name: string; kind: string; query: string; area: string; category: string }[]>("/datasources"),
  createDataSource: (body: { name: string; dsn: string; query: string; area?: string; category?: string }) =>
    request<{ id: string; name: string }>("/datasources", { method: "POST", body: JSON.stringify(body) }),
  testDataSource: (id: string) =>
    request<{ ok: boolean; columns: string[]; total_preview: number }>(`/datasources/${id}/test`, { method: "POST" }),
  importDataSource: (id: string) =>
    request<{ id: string; filename: string; rows: number }>(`/datasources/${id}/import`, { method: "POST" }),
  importCsv: (body: { name: string; csv_text: string; delimiter?: string; area?: string; category?: string }) =>
    request<{ id: string; filename: string; rows: number }>("/datasources/import-csv", { method: "POST", body: JSON.stringify(body) }),
  revealDataSource: (id: string) =>
    request<{ dsn: string }>(`/datasources/${id}/reveal`),
  deleteDataSource: (id: string) =>
    request<{ ok: boolean }>(`/datasources/${id}`, { method: "DELETE" }),
  // Text-to-image generation (NaN / FLUX)
  imageConfig: () =>
    request<{ configured: boolean; aspect_ratios: string[]; default_model: string }>("/images/config"),
  generateImages: (body: { prompt: string; aspect_ratio: string; variants: number }) =>
    request<{ images: GeneratedImageDto[] }>("/images/generate", { method: "POST", body: JSON.stringify(body) }),
  images: () => request<GeneratedImageDto[]>("/images"),
  imageDataUrl: (id: string) => `${api.base}/images/${id}/data`,
  deleteImage: (id: string) => request<{ ok: boolean }>(`/images/${id}`, { method: "DELETE" }),
  // Notebooks (NotebookLM-style over the company RAG)
  notebooks: () => request<Notebook[]>("/notebooks"),
  createNotebook: (body: { name: string; document_ids: string[] }) =>
    request<Notebook>("/notebooks", { method: "POST", body: JSON.stringify(body) }),
  updateNotebook: (id: string, body: { name: string; document_ids: string[] }) =>
    request<Notebook>(`/notebooks/${id}`, { method: "PUT", body: JSON.stringify(body) }),
  deleteNotebook: (id: string) =>
    request<{ ok: boolean }>(`/notebooks/${id}`, { method: "DELETE" }),
  notebookAsk: (id: string, question: string, opts?: { precision?: boolean; approve_external?: boolean }) =>
    request<NotebookAnswer>(`/notebooks/${id}/ask`, { method: "POST", body: JSON.stringify({ question, ...opts }) }),
  notebookGenerate: (id: string, kind: string, opts?: { precision?: boolean; approve_external?: boolean }) => {
    const qs = new URLSearchParams();
    if (opts?.precision) qs.set("precision", "true");
    if (opts?.approve_external) qs.set("approve_external", "true");
    const q = qs.toString();
    return request<NotebookAnswer>(`/notebooks/${id}/generate/${kind}${q ? `?${q}` : ""}`, { method: "POST" });
  },
  // External model providers (admin)
  adminEfficiency: () =>
    request<{ condense_enabled: boolean; condense_threshold_chars: number; max_tokens_per_request: number; rerank_enabled: boolean; tokens_saved_total: number }>("/admin/efficiency"),
  updateEfficiency: (body: { condense_enabled?: boolean; condense_threshold_chars?: number; max_tokens_per_request?: number; rerank_enabled?: boolean }) =>
    request<{ condense_enabled: boolean; condense_threshold_chars: number; max_tokens_per_request: number; rerank_enabled: boolean; tokens_saved_total: number }>(
      "/admin/efficiency", { method: "PUT", body: JSON.stringify(body) }),
  adminProviders: () =>
    request<{ route: string; enabled: boolean; base_url: string; model: string; has_key: boolean }[]>("/admin/providers"),
  updateProvider: (route: string, body: { enabled: boolean; base_url: string; model: string; api_key?: string }) =>
    request<{ route: string; enabled: boolean; has_key: boolean }>(`/admin/providers/${route}`, { method: "PUT", body: JSON.stringify(body) }),
  testProvider: (route: string) =>
    request<{ ok: boolean; mode: string; model?: string; provider?: string; latency_ms?: number; sample?: string; detail?: string }>(`/admin/providers/${route}/test`, { method: "POST" }),
  documentCategories: () => request<DocumentCategory[]>("/documents/categories"),
  createDocumentCategory: (body: { label: string; description?: string }) =>
    request<DocumentCategory>("/documents/categories", { method: "POST", body: JSON.stringify(body) }),
  chat: (body: {
    agent_id: string;
    prompt: string;
    conversation_id?: string;
    document_ids?: string[];
    use_rag?: boolean;
    use_memory?: boolean;
    precision?: boolean;
    approve_external?: boolean;
  }) => request<ChatResponse>("/chat", { method: "POST", body: JSON.stringify(body) }),
  previewRoute: (body: { agent_id: string; prompt: string; document_ids?: string[]; use_rag?: boolean }) =>
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
  audit: (params?: { event_type?: string; risk_level?: string; classification?: string; route?: string; user_id?: string; q?: string; limit?: number; offset?: number }) => {
    const clean = Object.fromEntries(Object.entries(params || {}).filter(([, v]) => v !== "" && v != null).map(([k, v]) => [k, String(v)]));
    const q = new URLSearchParams(clean).toString();
    return request<AuditEvent[]>(`/audit${q ? `?${q}` : ""}`);
  },
  auditStats: () => request<{
    total: number; high_risk: number; blocked: number; total_cost: number; total_tokens: number;
    by_event: Record<string, number>; by_risk: Record<string, number>; by_route: Record<string, number>;
    by_classification: Record<string, number>; event_types: string[]; users: string[];
  }>("/audit/stats"),
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
    request<{ id: string; email: string; name: string; role: string; area: string; license: string; mfa_enabled: boolean; status: string }[]>(
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
