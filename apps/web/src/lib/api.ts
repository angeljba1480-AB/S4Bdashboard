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
    request<{ id: string; name: string; description: string; trigger: string; schedule: string; event: string; action_type: string; action_ref: string; config: Record<string, unknown>; enabled: boolean; status: string; last_run: string | null }[]>("/automations"),
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
  validateAutomation: (id: string) =>
    request<{ name: string; ready: boolean; steps: { label: string; status: "ok" | "missing"; detail: string; link: string | null; optional?: boolean }[] }>(`/automations/${id}/validate`),
  scheduleAutomation: (id: string, frequency: string) =>
    request<{ id: string; trigger: string; schedule: string; enabled: boolean }>(`/automations/${id}/schedule`, { method: "POST", body: JSON.stringify({ frequency }) }),
  setAutomationDelivery: (id: string, channels: string[], emailTo = "") =>
    request<{ id: string; config: Record<string, unknown> }>(`/automations/${id}/delivery`, { method: "POST", body: JSON.stringify({ channels, email_to: emailTo }) }),
  setAutomationSource: (id: string, body: { kind: string; ref?: string; label?: string }) =>
    request<{ id: string; config: Record<string, unknown> }>(`/automations/${id}/source`, { method: "POST", body: JSON.stringify(body) }),
  automationSteps: (id: string) =>
    request<{ id: string; steps: Record<string, unknown>[] }>(`/automations/${id}/steps`),
  setAutomationSteps: (id: string, steps: Record<string, unknown>[]) =>
    request<{ id: string; config: Record<string, unknown> }>(`/automations/${id}/steps`, { method: "PUT", body: JSON.stringify({ steps }) }),
  // KEDB (base de errores conocidos, gateada por perfil cyber)
  kedbStatus: () => request<{ enabled: boolean }>("/kedb/status"),
  kedb: (params?: { q?: string; severity?: string; product?: string }) => {
    const qs = new URLSearchParams();
    if (params?.q) qs.set("q", params.q);
    if (params?.severity) qs.set("severity", params.severity);
    if (params?.product) qs.set("product", params.product);
    const s = qs.toString();
    return request<{ id: string; scope: string; title: string; symptom: string; cause: string; resolution: string; product: string; severity: string; tags: string[]; status: string; source: string; created_at: string }[]>(`/kedb${s ? `?${s}` : ""}`);
  },
  createKnownError: (body: { title: string; symptom?: string; cause?: string; resolution?: string; product?: string; severity?: string; tags?: string[]; scope?: string }) =>
    request<{ id: string; title: string }>("/kedb", { method: "POST", body: JSON.stringify(body) }),
  deleteKnownError: (id: string) => request<{ ok: boolean }>(`/kedb/${id}`, { method: "DELETE" }),
  analyzeKedb: (symptom: string, product = "") =>
    request<{ matches: { id: string; title: string; symptom: string; cause: string; resolution: string; product: string; severity: string }[]; is_known: boolean; suggestion: string }>("/kedb/analyze", { method: "POST", body: JSON.stringify({ symptom, product }) }),
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
    request<{ brand_name: string; brand_logo_url: string; brand_color: string; brand_tagline: string; custom_domain: string; tenant_name: string; country: string }>(
      "/admin/branding",
    ),
  setBranding: (body: { brand_name: string; brand_logo_url: string; brand_color: string; brand_tagline: string; custom_domain?: string; country?: string }) =>
    request<{ brand_name: string; brand_color: string; custom_domain?: string }>("/admin/branding", {
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
  supportSender: () =>
    request<{ account_id: string; from_addr: string; from_name: string; connections: { id: string; provider: string; email: string }[] }>("/company/support-sender"),
  setSupportSender: (body: { account_id: string; from_addr: string; from_name: string }) =>
    request<{ account_id: string; from_addr: string; from_name: string }>("/company/support-sender", { method: "PUT", body: JSON.stringify(body) }),
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
  uploadFile: (file: File, meta?: { area?: string; category?: string; sensitivity?: string; name?: string }) => {
    const fd = new FormData();
    fd.append("file", file);
    if (meta?.name) fd.append("filename", meta.name);   // nombre editado por el usuario (gana sobre el del archivo)
    if (meta?.area) fd.append("area", meta.area);
    if (meta?.category) fd.append("category", meta.category);
    if (meta?.sensitivity) fd.append("sensitivity", meta.sensitivity);
    return request<DocumentItem>("/documents/upload", { method: "POST", body: fd });
  },
  deleteDocument: (id: string) =>
    request<{ ok: boolean }>(`/documents/${id}`, { method: "DELETE" }),
  updateDocument: (id: string, body: { area?: string; category?: string; sensitivity?: string }) =>
    request<DocumentItem>(`/documents/${id}`, { method: "PATCH", body: JSON.stringify(body) }),
  driveFiles: (query?: string, folder?: string) => {
    const qs = new URLSearchParams();
    if (query) qs.set("query", query);
    if (folder) qs.set("folder", folder);
    const s = qs.toString();
    return request<{ files: { id: string; name: string; mime_type: string; is_folder: boolean; modified: string }[] }>(
      `/drive/files${s ? `?${s}` : ""}`);
  },
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
  readiness: () =>
    request<{ summary: Record<string, number>; checks: { key: string; label: string; status: "ok" | "warn" | "missing"; detail: string; fix: { steps: string[]; help?: string | null; link?: string | null } | null }[] }>("/admin/readiness"),
  agentRun: (instruction: string, autoApprove = false, dryRun = false) =>
    request<{ instruction: string; source: string; note: string; dry_run: boolean; steps: (ActionRequestItem & { step_status: string; reason: string })[] }>(
      "/actions/agent", { method: "POST", body: JSON.stringify({ instruction, auto_approve: autoApprove, dry_run: dryRun }) }),
  playbooks: () =>
    request<{ id: string; name: string; instruction: string; auto_approve: boolean; created_at: string }[]>("/actions/playbooks"),
  createPlaybook: (body: { name: string; instruction: string; auto_approve?: boolean }) =>
    request<{ id: string; name: string }>("/actions/playbooks", { method: "POST", body: JSON.stringify(body) }),
  runPlaybook: (id: string, dryRun = false) =>
    request<{ instruction: string; source: string; note: string; dry_run: boolean; steps: (ActionRequestItem & { step_status: string; reason: string })[] }>(
      `/actions/playbooks/${id}/run${dryRun ? "?dry_run=true" : ""}`, { method: "POST" }),
  deletePlaybook: (id: string) =>
    request<{ ok: boolean }>(`/actions/playbooks/${id}`, { method: "DELETE" }),
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
  // Carga los bytes de la imagen CON token (un <img src> normal no manda el header
  // Authorization) y devuelve un object URL para usar como src.
  imageBlob: async (id: string): Promise<string> => {
    const token = getToken();
    const res = await fetch(`${api.base}/images/${id}/data`, {
      headers: token ? { Authorization: `Bearer ${token}` } : {},
    });
    if (!res.ok) throw new Error(`No se pudo cargar la imagen (${res.status})`);
    return URL.createObjectURL(await res.blob());
  },
  deleteImage: (id: string) => request<{ ok: boolean }>(`/images/${id}`, { method: "DELETE" }),
  editImages: (form: FormData) =>
    request<{ images: GeneratedImageDto[] }>("/images/edit", { method: "POST", body: form }),
  // Runbooks (automatizaciones multi-paso por segmento/sector)
  runbookFacets: () =>
    request<{ segments: { key: string; label: string }[]; sectors: { key: string; label: string; count: number }[]; total: number }>("/runbooks/facets"),
  runbooks: (segment = "", sector = "", q = "") => {
    const p = new URLSearchParams();
    if (segment) p.set("segment", segment);
    if (sector) p.set("sector", sector);
    if (q) p.set("q", q);
    const s = p.toString();
    return request<{ id: string; title: string; description: string; segment: string; sector: string; area: string; benefit: string; icon: string; steps: string[] }[]>(`/runbooks${s ? `?${s}` : ""}`);
  },
  installRunbook: (id: string) =>
    request<{ id: string; name: string; already_installed: boolean }>(`/runbooks/${id}/install`, { method: "POST" }),
  // Espacios (proyectos del cliente)
  spaces: () =>
    request<{ id: string; name: string; client: string; description: string; modules: { key: string; title: string; href: string; icon: string; desc: string }[]; created_at: string }[]>("/spaces"),
  space: (id: string) =>
    request<{ id: string; name: string; client: string; description: string; modules: { key: string; title: string; href: string; icon: string; desc: string }[]; created_at: string }>(`/spaces/${id}`),
  createSpace: (body: { name: string; client: string; description: string }) =>
    request<{ id: string }>("/spaces", { method: "POST", body: JSON.stringify(body) }),
  deleteSpace: (id: string) =>
    request<{ ok: boolean }>(`/spaces/${id}`, { method: "DELETE" }),
  // Tablero Financiero (pilot)
  financeOverview: (entity: string) =>
    request<{ entity: string; company: { name: string; period: string; ceo: string; cfo: string }; kpis: Record<string, number>; summary: Record<string, number | string>; monthly: { mes: string; ingresos: number; ebitda: number }[]; segments: { name: string; revenue: number; margin: number; tipo: string }[]; gob_ip: Record<string, { gob: number; ip: number }>; benchmarks: { metric: string; s4b: number; industry: number; topQ: number; format: string; higherBetter: boolean }[]; alerts: { level: string; area: string; msg: string; impact: number | null }[]; source: string; is_demo: boolean }>(`/finance/overview?entity=${entity}`),
  financeClients: (entity: string) =>
    request<{ name: string; sector: string; entity: string; revenue: number; margin: number; status: string }[]>(`/finance/clients?entity=${entity}`),
  financeAsk: (question: string, entity: string) =>
    request<{ answer: string; entity: string; route: string }>("/finance/ask", { method: "POST", body: JSON.stringify({ question, entity }) }),
  financeProjects: () =>
    request<{
      source: string;
      totals: { venta: number; costos: number; margen: number; ebitda: number; ebitda_bc: number; pct_margen: number; pct_ebitda: number; desviacion: number; proyectos: number };
      trend: Record<string, { venta: number; gob: number; ip: number; ebitda: number; ebitda_bc: number; margen: number; proyectos: number; desviacion: number }>;
      cost_mix: { nomina: number; hw_sw: number; costo_corp: number; repr_viaticos: number; otros: number };
      clients: { name: string; sector: string; revenue: number; margin: number; status: string }[];
      detail: { cliente: string; nombre: string; tipo: string; venta: number; costos: number; margen: number; pct_margen: number; ebitda: number; ebitda_bc: number; desviacion: number }[];
    }>("/finance/projects"),
  financeDatasetStatus: () =>
    request<{ loaded: boolean; source?: string; filename?: string; updated_at?: string; origin: string }>("/finance/dataset/status"),
  financeUploadDataset: (files: File[]) => {
    const fd = new FormData();
    files.forEach((f) => fd.append("files", f));
    return request<{ ok: boolean; source: string; filename: string; partial_entities: boolean; proyectos: number }>("/finance/dataset", { method: "POST", body: fd });
  },
  financeDeleteDataset: () =>
    request<{ ok: boolean }>("/finance/dataset", { method: "DELETE" }),
  financeOperations: () =>
    request<{
      utilization: { year: string; horas_reales: number; horas_capacidad: number; utilizacion: number; empleados: number; capacidad_emp: number; by_project: { nombre: string; horas: number }[] };
      cost_per_hour: { year: string; by_role: { rol: string; costo_hora: number; registros: number }[] };
      client_scoring: { criteria: [string, number][]; clients: { name: string; sector: string; score: number; tier: string; facturacion: string; rentabilidad: string }[] };
      cost_comparison: { note: string; available: string[]; pending: string[]; by_month: { anio: string; mes: string; costo_bc: number | null; costo_cmi: number | null; costo_timesheet: number | null }[] };
      is_demo: boolean;
    }>("/finance/operations"),
  // Resumen de correo automatizado
  mailDigestConfig: () =>
    request<{ id: string; enabled: boolean; account_id: string; schedule: string; channels: string[]; email_to: string; language: string; notes: string; discard_propaganda: boolean; pending_enabled: boolean; pending_days: number; last_run_at: string }>("/mail-digest/config"),
  setMailDigestConfig: (body: { enabled: boolean; account_id: string; schedule: string; channels: string[]; email_to: string; language: string; notes: string; discard_propaganda: boolean; pending_enabled: boolean; pending_days: number }) =>
    request<{ id: string }>("/mail-digest/config", { method: "PUT", body: JSON.stringify(body) }),
  mailDigestPreview: () =>
    request<{ ok: boolean; text: string; account: string; message: string; counts: { messages?: number } }>("/mail-digest/preview", { method: "POST" }),
  mailDigestRunNow: () =>
    request<{ ok: boolean; sent: Record<string, boolean>; account: string }>("/mail-digest/run-now", { method: "POST" }),
  // WhatsApp (CallMeBot)
  whatsappConfig: () => request<{ phone: string; configured: boolean }>("/whatsapp/config"),
  setWhatsappConfig: (phone: string, apikey: string) =>
    request<{ phone: string; configured: boolean }>("/whatsapp/config", { method: "POST", body: JSON.stringify({ phone, apikey }) }),
  sendWhatsapp: (text: string) =>
    request<{ ok: boolean; detail: string }>("/whatsapp/send", { method: "POST", body: JSON.stringify({ text }) }),
  testWhatsapp: () => request<{ ok: boolean; detail: string }>("/whatsapp/test", { method: "POST" }),
  // Voz (NaN: kokoro TTS / whisper STT)
  voiceConfig: () =>
    request<{ configured: boolean; voices: { id: string; label: string }[] }>("/voice/config"),
  tts: async (text: string, voice = "", format = "mp3"): Promise<Blob> => {
    const res = await fetch(`${API_BASE}/voice/tts`, {
      method: "POST",
      headers: { "Content-Type": "application/json", ...(getToken() ? { Authorization: `Bearer ${getToken()}` } : {}) },
      body: JSON.stringify({ text, voice, format }),
    });
    if (!res.ok) throw new Error((await res.json().catch(() => ({}))).detail || "No se pudo narrar");
    return res.blob();
  },
  transcribe: (form: FormData) =>
    request<{ text: string; language: string }>("/voice/transcribe", { method: "POST", body: form }),
  // Alertas configurables + notificaciones (pop-ups)
  alertEventTypes: () =>
    request<{ key: string; label: string }[]>("/alerts/event-types"),
  alertRules: () =>
    request<{ id: string; name: string; event_type: string; channels: string[]; webhook_url: string; telegram_chat_id: string; has_telegram_token: boolean; schedule: string; last_digest_at: string; enabled: boolean }[]>("/alerts/rules"),
  createAlertRule: (body: { name: string; event_type: string; channels: string[]; webhook_url?: string; telegram_token?: string; telegram_chat_id?: string; schedule?: string; enabled?: boolean }) =>
    request<{ id: string }>("/alerts/rules", { method: "POST", body: JSON.stringify(body) }),
  deleteAlertRule: (id: string) =>
    request<{ ok: boolean }>(`/alerts/rules/${id}`, { method: "DELETE" }),
  testAlert: () => request<{ fired: number }>("/alerts/test", { method: "POST" }),
  runDigests: (frequency: string) =>
    request<{ frequency: string; sent: number }>(`/alerts/run-digests?frequency=${frequency}`, { method: "POST" }),
  getAlertThreshold: () => request<{ spend_threshold_usd: number }>("/alerts/threshold"),
  setAlertThreshold: (spend_threshold_usd: number) =>
    request<{ spend_threshold_usd: number }>("/alerts/threshold", { method: "POST", body: JSON.stringify({ spend_threshold_usd }) }),
  // Búsqueda global
  search: (q: string) =>
    request<{ query: string; total: number; results: { type: string; id: string; title: string; snippet: string; href: string; area?: string }[] }>(`/search?q=${encodeURIComponent(q)}`),
  notifications: (unread = false) =>
    request<{ id: string; title: string; body: string; level: string; event_type: string; read: boolean; created_at: string }[]>(`/notifications${unread ? "?unread=true" : ""}`),
  unreadCount: () => request<{ count: number }>("/notifications/unread-count"),
  markNotificationRead: (id: string) => request<{ ok: boolean }>(`/notifications/${id}/read`, { method: "POST" }),
  markAllNotificationsRead: () => request<{ ok: boolean; marked: number }>("/notifications/read-all", { method: "POST" }),
  // RAG: re-indexar tras cambiar el proveedor de embeddings
  reindexDocuments: () =>
    request<{ documents: number; chunks: number; orphans_purged?: number }>("/documents/reindex", { method: "POST" }),
  // Recetas n8n a la medida (DB / SOAP / apps propias)
  n8nRecipes: () =>
    request<{ id: string; provider: string; name: string; description: string; category: string; webhook_path: string; webhook_url: string; params: string[]; enabled: boolean; created_at: string }[]>("/workflows/recipes"),
  createN8nRecipe: (body: { name: string; provider?: string; description?: string; category?: string; webhook_path?: string; webhook_url?: string; params?: string[]; enabled?: boolean }) =>
    request<{ id: string; name: string }>("/workflows/recipes", { method: "POST", body: JSON.stringify(body) }),
  updateN8nRecipe: (id: string, body: { name: string; provider?: string; description?: string; category?: string; webhook_path?: string; webhook_url?: string; params?: string[]; enabled?: boolean }) =>
    request<{ id: string }>(`/workflows/recipes/${id}`, { method: "PATCH", body: JSON.stringify(body) }),
  deleteN8nRecipe: (id: string) =>
    request<{ ok: boolean }>(`/workflows/recipes/${id}`, { method: "DELETE" }),
  runN8nRecipe: (id: string, payload: Record<string, unknown> = {}) =>
    request<{ status: string; engine: string; detail: string }>(`/workflows/recipes/${id}/run`, { method: "POST", body: JSON.stringify({ payload }) }),
  // Conector SFTP (solo lectura) → import al RAG
  sftpSources: () =>
    request<{ id: string; name: string; host: string; port: number; username: string; auth_type: string; remote_path: string; area: string; category: string; created_at: string }[]>("/datasources/sftp"),
  createSftp: (body: { name: string; host: string; port?: number; username: string; auth_type: string; secret: string; remote_path: string; area?: string; category?: string }) =>
    request<{ id: string }>("/datasources/sftp", { method: "POST", body: JSON.stringify(body) }),
  testSftp: (id: string) =>
    request<{ ok: boolean; files: { name: string; size: number }[]; count: number }>(`/datasources/sftp/${id}/test`, { method: "POST" }),
  importSftp: (id: string) =>
    request<{ imported: number; documents: { id: string; filename: string }[] }>(`/datasources/sftp/${id}/import`, { method: "POST" }),
  deleteSftp: (id: string) =>
    request<{ ok: boolean }>(`/datasources/sftp/${id}`, { method: "DELETE" }),
  // Conector OData (SAP S/4HANA, solo lectura) → import al RAG
  odataSources: () =>
    request<{ id: string; name: string; base_url: string; auth_type: string; username: string; odata_filter: string; select: string; top: number; area: string; category: string }[]>("/datasources/odata"),
  createOdata: (body: { name: string; base_url: string; auth_type?: string; username?: string; secret?: string; odata_filter?: string; select?: string; top?: number; area?: string; category?: string }) =>
    request<{ id: string; name: string }>("/datasources/odata", { method: "POST", body: JSON.stringify(body) }),
  testOdata: (id: string) =>
    request<{ ok: boolean; columns: string[]; total_preview: number }>(`/datasources/odata/${id}/test`, { method: "POST" }),
  importOdata: (id: string) =>
    request<{ id: string; filename: string; rows: number }>(`/datasources/odata/${id}/import`, { method: "POST" }),
  deleteOdata: (id: string) =>
    request<{ ok: boolean }>(`/datasources/odata/${id}`, { method: "DELETE" }),
  // Fine-tuning ligero (LoRA)
  ftBaseModels: () =>
    request<{ name: string; mlx_model: string; family: string }[]>("/finetune/base-models"),
  ftDatasets: () =>
    request<{ id: string; name: string; area: string; base_model: string; status: string; version: number; examples: number; created_at: string }[]>("/finetune/datasets"),
  ftCreateDataset: (body: { name: string; area?: string; base_model?: string }) =>
    request<{ id: string; name: string; examples: number }>("/finetune/datasets", { method: "POST", body: JSON.stringify(body) }),
  ftAddExample: (id: string, body: { prompt: string; completion: string }) =>
    request<{ id: string; examples: number }>(`/finetune/datasets/${id}/examples`, { method: "POST", body: JSON.stringify(body) }),
  ftFromMemory: (id: string, body: { tag?: string; limit?: number }) =>
    request<{ added: number; examples: number }>(`/finetune/datasets/${id}/from-memory`, { method: "POST", body: JSON.stringify(body) }),
  ftCheck: (id: string) =>
    request<{ status: string; ok: boolean; issues: string[]; n: number; pii_leaks: number; injection_flags: number }>(`/finetune/datasets/${id}/check`, { method: "POST" }),
  ftExportUrl: (id: string) => `${api.base}/finetune/datasets/${id}/export`,
  ftJobs: () =>
    request<{ id: string; dataset_id: string; base_model: string; status: string; adapter_uri: string; serve_base_url: string; metrics: Record<string, unknown>; reason: string; created_at: string }[]>("/finetune/jobs"),
  ftCreateJob: (body: { dataset_id: string; base_model?: string }) =>
    request<{ id: string; status: string; base_model: string; reason: string }>("/finetune/jobs", { method: "POST", body: JSON.stringify(body) }),
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
    request<{ route: string; onprem?: boolean; enabled: boolean; base_url: string; model: string; has_key: boolean }[]>("/admin/providers"),
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
    request<{ run_id: string; status: string; engine: string; source: string; detail: string; steps: string; response: Record<string, unknown> | null }>(
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
  conversations: () =>
    request<{ id: string; title: string; agent_id: string; agent_name: string; messages: number; created_at: string }[]>("/chat/conversations"),
  conversation: (id: string) =>
    request<{ id: string; title: string; agent_id: string; messages: { role: string; content: string; route: string }[] }>(`/chat/conversations/${id}`),
  deleteConversation: (id: string) =>
    request<{ ok: boolean }>(`/chat/conversations/${id}`, { method: "DELETE" }),
  exportAudit: () => api.download("/audit/export", "audit.jsonl"),
};
