"use client";

import { PageHeader, Shell } from "@/components/Shell";
import { ReadinessPanel } from "@/components/ReadinessPanel";
import { api } from "@/lib/api";
import { useEffect, useState } from "react";

type Security = Awaited<ReturnType<typeof api.security>>;
type N8n = Awaited<ReturnType<typeof api.getN8n>>;

export default function AdminPage() {
  const [routes, setRoutes] = useState<{ route: string; provider: string; enabled: boolean; model: string; mode: string }[]>([]);
  const [users, setUsers] = useState<{ id: string; email: string; name: string; role: string; area: string; license: string; mfa_enabled: boolean; status: string }[]>([]);
  const [tenants, setTenants] = useState<Awaited<ReturnType<typeof api.adminTenants>>>([]);
  const [providers, setProviders] = useState<Awaited<ReturnType<typeof api.adminProviders>>>([]);
  const [eff, setEff] = useState<Awaited<ReturnType<typeof api.adminEfficiency>> | null>(null);
  const [provDraft, setProvDraft] = useState<Record<string, { enabled: boolean; base_url: string; model: string; api_key: string }>>({});
  const [provTest, setProvTest] = useState<Record<string, string>>({});
  const PROVIDER_LABELS: Record<string, string> = {
    local: "Local on-prem (Ollama)",
    vpc: "VPC privada (vLLM / TGI)",
    premium: "Premium (GPT / Claude / Gemini)",
    open: "Abierto (NaN / Llama / OpenRouter)",
  };
  const [security, setSecurity] = useState<Security | null>(null);
  const [n8n, setN8n] = useState<N8n | null>(null);
  const [n8nUrl, setN8nUrl] = useState("");
  const [n8nKey, setN8nKey] = useState("");
  const [n8nMsg, setN8nMsg] = useState("");
  const [proposals, setProposals] = useState<
    { id: string; title: string; description: string; category: string; status: string }[]
  >([]);
  const [error, setError] = useState("");

  const [brand, setBrand] = useState({ brand_name: "", brand_logo_url: "", brand_color: "", brand_tagline: "", country: "MX" });
  const [countries, setCountries] = useState<{ code: string; name: string }[]>([]);
  const [brandMsg, setBrandMsg] = useState("");
  const [billing, setBilling] = useState<Awaited<ReturnType<typeof api.getBilling>> | null>(null);
  const [plans, setPlans] = useState<Awaited<ReturnType<typeof api.plans>> | null>(null);
  const [newUser, setNewUser] = useState({ email: "", name: "", role: "user", area: "", license: "basic" });
  const ROLE_LABELS: Record<string, string> = { super_admin: "Super Admin", admin: "Admin", user: "Usuario", security: "Security", devops: "DevOps" };
  const [billingMsg, setBillingMsg] = useState("");
  const [tramites, setTramites] = useState<{ id: string; title: string; authority: string; source: string; region: string }[]>([]);
  const [newTramite, setNewTramite] = useState({ title: "", authority: "", region: "", keywords: "", requisitos: "", pasos: "" });
  const [tramiteMsg, setTramiteMsg] = useState("");
  const [docs, setDocs] = useState<{ id: string; filename: string }[]>([]);
  const [importDoc, setImportDoc] = useState("");

  function loadTramites() {
    api.tramites().then(setTramites).catch(() => {});
  }
  async function doImport() {
    if (!importDoc) return;
    setTramiteMsg("Importando…");
    try {
      await api.importTramite(importDoc);
      setImportDoc("");
      setTramiteMsg("✓ Documento convertido a trámite del MCP");
      loadTramites();
    } catch (err) {
      setTramiteMsg(err instanceof Error ? err.message : "Error");
    }
  }
  async function addTramite(e: React.FormEvent) {
    e.preventDefault();
    setTramiteMsg("");
    try {
      await api.addCompanyTramite({
        title: newTramite.title,
        authority: newTramite.authority,
        region: newTramite.region,
        keywords: newTramite.keywords.split(",").map((k) => k.trim()).filter(Boolean),
        requisitos: newTramite.requisitos.split("\n").map((k) => k.trim()).filter(Boolean),
        pasos: newTramite.pasos.split("\n").map((k) => k.trim()).filter(Boolean),
      });
      setNewTramite({ title: "", authority: "", region: "", keywords: "", requisitos: "", pasos: "" });
      setTramiteMsg("✓ Agregado al MCP de tu empresa");
      loadTramites();
    } catch (err) {
      setTramiteMsg(err instanceof Error ? err.message : "Error");
    }
  }

  function loadBilling() {
    api.getBilling().then(setBilling).catch(() => {});
  }
  async function addSeat() {
    if (!billing) return;
    await api.updateBilling({ seats_licensed: billing.seats_licensed + 1 });
    loadBilling();
  }
  async function addUser(e: React.FormEvent) {
    e.preventDefault();
    setBillingMsg("");
    try {
      await api.createUser(newUser);
      setNewUser({ email: "", name: "", role: "user", area: "", license: "basic" });
      setBillingMsg("✓ Usuario agregado");
      api.users().then(setUsers).catch(() => {});
      loadBilling();
    } catch (err) {
      setBillingMsg(err instanceof Error ? err.message : "Error (¿asientos agotados?)");
    }
  }

  async function saveProvider(route: string) {
    const d = provDraft[route];
    if (!d) return;
    await api.updateProvider(route, d);
    api.adminProviders().then((p) => {
      setProviders(p);
      setProvDraft(Object.fromEntries(p.map((x) => [x.route, { enabled: x.enabled, base_url: x.base_url, model: x.model, api_key: "" }])));
    }).catch(() => {});
  }
  async function testProvider(route: string) {
    setProvTest((s) => ({ ...s, [route]: "Probando…" }));
    try {
      const r = await api.testProvider(route);
      setProvTest((s) => ({
        ...s,
        [route]: r.ok
          ? `✅ OK · ${r.model} · ${r.latency_ms} ms`
          : `⚠️ ${r.mode === "mock" ? "Sin proveedor real (MOCK)" : "Error"}: ${r.detail ?? ""}`,
      }));
    } catch (e) {
      setProvTest((s) => ({ ...s, [route]: `⚠️ ${e instanceof Error ? e.message : "Error"}` }));
    }
  }

  function loadProposals() {
    api.recipeProposals().then(setProposals).catch(() => {});
  }
  function loadBranding() {
    api.getBranding()
      .then((b) => setBrand({ brand_name: b.brand_name, brand_logo_url: b.brand_logo_url, brand_color: b.brand_color, brand_tagline: b.brand_tagline, country: b.country || "MX" }))
      .catch(() => {});
  }
  async function saveBranding(e: React.FormEvent) {
    e.preventDefault();
    setBrandMsg("Guardando…");
    try {
      await api.setBranding(brand);
      setBrandMsg("✓ Marca actualizada. Recarga para verla en todo el portal.");
    } catch (err) {
      setBrandMsg(err instanceof Error ? err.message : "Error");
    }
  }

  function loadN8n() {
    api.getN8n().then((c) => {
      setN8n(c);
      setN8nUrl(c.webhook_base_url ?? "");
    }).catch(() => {});
  }

  useEffect(() => {
    api.routes().then(setRoutes).catch((e) => setError(e.message));
    api.users().then(setUsers).catch(() => {});
    api.adminTenants().then(setTenants).catch(() => setTenants([]));
    api.adminProviders().then((p) => {
      setProviders(p);
      setProvDraft(Object.fromEntries(p.map((x) => [x.route, { enabled: x.enabled, base_url: x.base_url, model: x.model, api_key: "" }])));
    }).catch(() => {});
    api.adminEfficiency().then(setEff).catch(() => {});
    api.security().then(setSecurity).catch(() => {});
    loadN8n();
    loadProposals();
    loadBranding();
    loadBilling();
    api.plans().then(setPlans).catch(() => {});
    api.regionalCountries().then(setCountries).catch(() => {});
    loadTramites();
    api.documents().then((d) => setDocs(d.map((x) => ({ id: x.id, filename: x.filename })))).catch(() => {});
  }, []);

  async function curate(id: string) {
    await api.curateProposal(id, {});
    loadProposals();
  }
  async function reject(id: string) {
    await api.rejectProposal(id);
    loadProposals();
  }

  async function saveN8n(e: React.FormEvent) {
    e.preventDefault();
    setN8nMsg("Guardando…");
    try {
      const res = await api.setN8n({ webhook_base_url: n8nUrl, api_key: n8nKey || undefined });
      setN8nKey("");
      setN8nMsg(`✓ Motor: ${res.engine} (${res.source})`);
      loadN8n();
      api.security().then(setSecurity).catch(() => {});
    } catch (err) {
      setN8nMsg(err instanceof Error ? err.message : "Error");
    }
  }

  return (
    <Shell>
      <PageHeader title="Administración" subtitle="Usuarios, roles, modelos habilitados y rutas de privacidad." help={["modelos", "onprem"]} />
      <div className="space-y-6 p-8">
        {error && <div className="rounded-lg bg-red-50 px-4 py-2 text-sm text-red-600">{error}</div>}

        <ReadinessPanel />

        {billing && (
          <div className="rounded-2xl border border-slate-200 bg-white p-5">
            <div className="mb-1 flex items-center justify-between">
              <h2 className="font-semibold text-slate-800">Suscripción y asientos</h2>
              <span className={`rounded-full px-2 py-0.5 text-xs ${
                billing.subscription_status === "active" ? "bg-emerald-100 text-emerald-700"
                  : billing.subscription_status === "trial" ? "bg-amber-100 text-amber-700"
                    : "bg-red-100 text-red-700"
              }`}>
                {billing.subscription_status}
              </span>
            </div>
            <p className="mb-4 text-sm text-slate-500">
              Plataforma por <b>setup + anual prepagado por asientos</b>. Publicar proyectos de App Studio a
              producción se cobra aparte ({billing.prod_deploy_price_mxn} MXN por deploy).
            </p>
            <div className="mb-4 grid grid-cols-2 gap-3 sm:grid-cols-4">
              <div className="rounded-xl border border-slate-200 p-3">
                <div className="text-xs uppercase tracking-wide text-slate-400">Asientos</div>
                <div className="mt-1 font-semibold text-slate-800">{billing.seats_used} / {billing.seats_licensed}</div>
                <div className="text-xs text-slate-400">{billing.seats_available} disponibles</div>
              </div>
              <div className="rounded-xl border border-slate-200 p-3">
                <div className="text-xs uppercase tracking-wide text-slate-400">Cuota anual</div>
                <div className="mt-1 font-semibold text-slate-800">${billing.annual_fee_mxn.toLocaleString()} MXN</div>
              </div>
              <div className="rounded-xl border border-slate-200 p-3">
                <div className="text-xs uppercase tracking-wide text-slate-400">Setup</div>
                <div className="mt-1 font-semibold text-slate-800">{billing.setup_fee_paid ? "Pagado" : "Pendiente"}</div>
              </div>
              <div className="rounded-xl border border-slate-200 p-3">
                <div className="text-xs uppercase tracking-wide text-slate-400">Renovación</div>
                <div className="mt-1 font-semibold text-slate-800">{billing.renews_at ?? "—"}</div>
              </div>
            </div>
            <div className="flex flex-wrap items-end gap-3">
              <button onClick={addSeat} className="rounded-lg border border-slate-300 px-3 py-2 text-sm font-semibold text-slate-700">
                + Ampliar 1 asiento
              </button>
              <form onSubmit={addUser} className="flex flex-wrap items-center gap-2">
                <input value={newUser.name} onChange={(e) => setNewUser((u) => ({ ...u, name: e.target.value }))}
                  placeholder="Nombre" className="rounded-lg border border-slate-300 px-3 py-2 text-sm" />
                <input value={newUser.email} onChange={(e) => setNewUser((u) => ({ ...u, email: e.target.value }))}
                  placeholder="correo@empresa.mx" className="rounded-lg border border-slate-300 px-3 py-2 text-sm" />
                <select value={newUser.role} onChange={(e) => setNewUser((u) => ({ ...u, role: e.target.value }))}
                  className="rounded-lg border border-slate-300 px-3 py-2 text-sm">
                  <option value="user">Usuario</option>
                  <option value="admin">Admin</option>
                  <option value="security">Security</option>
                  <option value="devops">DevOps</option>
                </select>
                <input value={newUser.area} onChange={(e) => setNewUser((u) => ({ ...u, area: e.target.value }))}
                  placeholder="Área (ej. Ventas)" className="rounded-lg border border-slate-300 px-3 py-2 text-sm" />
                <select value={newUser.license} onChange={(e) => setNewUser((u) => ({ ...u, license: e.target.value }))}
                  className="rounded-lg border border-slate-300 px-3 py-2 text-sm">
                  <option value="basic">Basic</option>
                  <option value="pro">Pro</option>
                  <option value="enterprise">Enterprise</option>
                </select>
                <button className="rounded-lg bg-slate-900 px-4 py-2 text-sm font-semibold text-white">Agregar usuario</button>
              </form>
            </div>
            {billingMsg && <div className="mt-2 text-xs text-slate-500">{billingMsg}</div>}

            {plans && (
              <div className="mt-5 border-t border-slate-100 pt-4">
                <div className="mb-1 text-sm font-semibold text-slate-700">Esquema de licencias recomendado</div>
                <p className="mb-3 text-xs text-slate-400">
                  Precios indicativos por industria (MXN, estimados/ajustables). Anual prepagado por asiento +
                  setup; sacar a prod en App Studio se cobra aparte.
                </p>
                <div className="grid grid-cols-1 gap-3 sm:grid-cols-2 lg:grid-cols-4">
                  {plans.plans.map((p) => (
                    <div key={p.id} className="rounded-xl border border-slate-200 p-3">
                      <div className="font-semibold text-slate-800">{p.name}</div>
                      <div className="text-xs text-slate-400">{p.audience} · {p.seats_range} asientos</div>
                      <div className="mt-2 text-lg font-bold text-slate-900">
                        {p.annual_per_seat != null ? `$${p.annual_per_seat.toLocaleString()}` : "A cotizar"}
                        {p.annual_per_seat != null && <span className="text-xs font-normal text-slate-400"> /asiento/año</span>}
                      </div>
                      <div className="text-xs text-slate-500">
                        Setup: {p.setup_fee != null ? `$${p.setup_fee.toLocaleString()}` : "—"} ·
                        Prod: {p.prod_deploy_price != null ? (p.prod_deploy_price === 0 ? "incluido" : `$${p.prod_deploy_price}`) : "—"}
                      </div>
                      <ul className="mt-2 space-y-0.5 text-xs text-slate-500">
                        {p.includes.slice(0, 3).map((i) => <li key={i}>• {i}</li>)}
                      </ul>
                    </div>
                  ))}
                </div>
              </div>
            )}
          </div>
        )}

        <div className="rounded-2xl border border-slate-200 bg-white p-5">
          <h2 className="mb-1 font-semibold text-slate-800">Marca y región (white-label)</h2>
          <p className="mb-4 text-sm text-slate-500">
            Personaliza el portal: nombre, logo, color y <b>país</b> (LATAM). El país ajusta trámites,
            divisiones (estado/provincia/departamento) y el contexto de la IA.
          </p>
          <form onSubmit={saveBranding} className="grid grid-cols-1 gap-3 sm:grid-cols-2">
            <select
              value={brand.country}
              onChange={(e) => setBrand((b) => ({ ...b, country: e.target.value }))}
              className="rounded-lg border border-slate-300 px-3 py-2 text-sm sm:col-span-2"
            >
              {countries.map((c) => <option key={c.code} value={c.code}>{c.name}</option>)}
            </select>
            <input
              value={brand.brand_name}
              onChange={(e) => setBrand((b) => ({ ...b, brand_name: e.target.value }))}
              placeholder="Nombre de marca (ej. Acme AI)"
              className="rounded-lg border border-slate-300 px-3 py-2 text-sm"
            />
            <input
              value={brand.brand_tagline}
              onChange={(e) => setBrand((b) => ({ ...b, brand_tagline: e.target.value }))}
              placeholder="Tagline (ej. IA privada de Acme)"
              className="rounded-lg border border-slate-300 px-3 py-2 text-sm"
            />
            <input
              value={brand.brand_logo_url}
              onChange={(e) => setBrand((b) => ({ ...b, brand_logo_url: e.target.value }))}
              placeholder="URL del logo (https://…)"
              className="rounded-lg border border-slate-300 px-3 py-2 text-sm sm:col-span-2"
            />
            <div className="flex items-center gap-2">
              <input
                type="color"
                value={brand.brand_color || "#7c3aed"}
                onChange={(e) => setBrand((b) => ({ ...b, brand_color: e.target.value }))}
                className="h-9 w-12 rounded border border-slate-300"
              />
              <span className="text-sm text-slate-500">Color primario {brand.brand_color || "#7c3aed"}</span>
            </div>
            <button className="rounded-lg px-4 py-2 text-sm font-semibold text-white sm:col-span-2"
              style={{ background: brand.brand_color || "#7c3aed" }}>
              Guardar marca
            </button>
          </form>
          {brandMsg && <div className="mt-2 text-xs text-slate-500">{brandMsg}</div>}
        </div>

        {security && (
          <div className="rounded-2xl border border-slate-200 bg-white p-5">
            <h2 className="mb-4 font-semibold text-slate-800">Postura de seguridad (Enterprise hardening)</h2>
            <div className="grid grid-cols-1 gap-3 sm:grid-cols-2 lg:grid-cols-4">
              <div className="rounded-xl border border-slate-200 p-4">
                <div className="text-xs uppercase tracking-wide text-slate-400">Cifrado en reposo</div>
                <div className="mt-1 font-semibold text-slate-800">
                  {security.encryption_at_rest.enabled ? security.encryption_at_rest.algo : "Desactivado"}
                </div>
                <div className="text-xs text-slate-400">KMS v{security.encryption_at_rest.kms_key_version}</div>
              </div>
              <div className="rounded-xl border border-slate-200 p-4">
                <div className="text-xs uppercase tracking-wide text-slate-400">Vector store</div>
                <div className="mt-1 font-semibold capitalize text-slate-800">{security.vector_store}</div>
              </div>
              <div className="rounded-xl border border-slate-200 p-4">
                <div className="text-xs uppercase tracking-wide text-slate-400">SSO / OIDC</div>
                <div className="mt-1 font-semibold text-slate-800">
                  {security.sso.enabled ? "Habilitado" : "Password"}
                </div>
                <div className="truncate text-xs text-slate-400">{security.sso.issuer ?? "—"}</div>
              </div>
              <div className="rounded-xl border border-slate-200 p-4">
                <div className="text-xs uppercase tracking-wide text-slate-400">Fallback de rutas</div>
                <div className="mt-1 font-semibold text-slate-800">{security.fallback_order.join(" → ")}</div>
              </div>
              <div className="rounded-xl border border-slate-200 p-4">
                <div className="text-xs uppercase tracking-wide text-slate-400">Workflows</div>
                <div className="mt-1 font-semibold capitalize text-slate-800">{security.workflows.engine}</div>
                <div className="truncate text-xs text-slate-400">{security.workflows.base_url ?? "—"}</div>
              </div>
            </div>
          </div>
        )}

        <div className="rounded-2xl border border-slate-200 bg-white p-5">
          <h2 className="mb-4 font-semibold text-slate-800">Rutas de modelo (router de privacidad)</h2>
          <div className="grid grid-cols-1 gap-3 sm:grid-cols-2 lg:grid-cols-4">
            {routes.map((r) => (
              <div key={r.route} className="rounded-xl border border-slate-200 p-4">
                <div className="text-sm font-semibold capitalize text-slate-800">{r.route}</div>
                <div className="text-xs font-medium text-violet-600">{r.provider}</div>
                <div className="mt-1 text-xs text-slate-500">{r.model}</div>
                <span
                  className={`mt-2 inline-block rounded-full px-2 py-0.5 text-xs ${
                    r.mode === "real" ? "bg-emerald-100 text-emerald-700" : "bg-amber-100 text-amber-700"
                  }`}
                >
                  {r.mode === "real" ? "Proveedor real" : "Mock (configurar .env)"}
                </span>
              </div>
            ))}
          </div>
        </div>

        {n8n && (
          <div className="rounded-2xl border border-slate-200 bg-white p-5">
            <div className="mb-1 flex items-center justify-between">
              <h2 className="font-semibold text-slate-800">Workflows · n8n</h2>
              <span className={`rounded-full px-2 py-0.5 text-xs ${
                n8n.effective_source === "tenant" ? "bg-violet-100 text-violet-700"
                  : n8n.effective_source === "global" ? "bg-emerald-100 text-emerald-700"
                    : "bg-slate-100 text-slate-500"
              }`}>
                {n8n.effective_source === "tenant" ? "n8n propio (BYO)"
                  : n8n.effective_source === "global" ? "Gestionado · sin configuración"
                    : "no disponible"}
              </span>
            </div>
            <p className="mb-3 text-sm text-slate-500">
              Tus workflows son <b>totalmente gestionados</b>: no necesitas configurar nada.
              {n8n.effective_source === "global" && n8n.auto_provision && (
                <> Se aprovisionan automáticamente {n8n.provisioned ? "(ya listos ✓)" : "al primer uso"}.</>
              )}
            </p>
            {n8n.effective_source === "global" && (
              <button
                onClick={async () => {
                  setN8nMsg("Provisionando…");
                  const r = await api.provisionN8n();
                  setN8nMsg(r.provisioned ? `✓ Workflows listos (${(r.created ?? []).length} nuevos)` : `⚠️ ${r.reason}`);
                  loadN8n();
                }}
                className="rounded-lg bg-slate-900 px-4 py-2 text-sm font-semibold text-white"
              >
                Re-provisionar mis workflows
              </button>
            )}

            <details className="mt-4">
              <summary className="cursor-pointer text-xs font-medium text-slate-400 hover:text-slate-600">
                Avanzado: usar mi propio n8n (BYO)
              </summary>
              <form onSubmit={saveN8n} className="mt-3 grid grid-cols-1 gap-3 sm:grid-cols-3">
                <input
                  value={n8nUrl}
                  onChange={(e) => setN8nUrl(e.target.value)}
                  placeholder="https://n8n.tuempresa.com/webhook (vacío = gestionado)"
                  className="rounded-lg border border-slate-300 px-3 py-2 text-sm sm:col-span-2"
                />
                <input
                  value={n8nKey}
                  onChange={(e) => setN8nKey(e.target.value)}
                  type="password"
                  placeholder={n8n.has_api_key ? "•••••• (sin cambios)" : "API key (opcional)"}
                  className="rounded-lg border border-slate-300 px-3 py-2 text-sm"
                />
                <button className="rounded-lg border border-slate-300 px-4 py-2 text-sm font-semibold text-slate-700 sm:col-span-3">
                  Guardar n8n propio
                </button>
              </form>
            </details>
            {n8nMsg && <div className="mt-2 text-xs text-slate-500">{n8nMsg}</div>}
          </div>
        )}

        <div className="rounded-2xl border border-slate-200 bg-white p-5">
          <h2 className="mb-1 font-semibold text-slate-800">MCP de empresa · Trámites</h2>
          <p className="mb-4 text-sm text-slate-500">
            Tu capa privada de contexto (sobre estado y país). Se nutre de lo que agregues aquí
            <b> y de tus documentos indexados (RAG)</b>. Aterriza las respuestas de tus agentes y casos
            de uso. {tramites.filter((t) => t.source === "empresa").length} entradas propias.
          </p>
          <form onSubmit={addTramite} className="grid grid-cols-1 gap-2 sm:grid-cols-2">
            <input value={newTramite.title} onChange={(e) => setNewTramite((t) => ({ ...t, title: e.target.value }))}
              placeholder="Título (ej. Política interna de facturación)" className="rounded-lg border border-slate-300 px-3 py-2 text-sm sm:col-span-2" />
            <input value={newTramite.authority} onChange={(e) => setNewTramite((t) => ({ ...t, authority: e.target.value }))}
              placeholder="Autoridad / área" className="rounded-lg border border-slate-300 px-3 py-2 text-sm" />
            <input value={newTramite.region} onChange={(e) => setNewTramite((t) => ({ ...t, region: e.target.value }))}
              placeholder="Estado/Provincia (opcional)" className="rounded-lg border border-slate-300 px-3 py-2 text-sm" />
            <input value={newTramite.keywords} onChange={(e) => setNewTramite((t) => ({ ...t, keywords: e.target.value }))}
              placeholder="Palabras clave (coma)" className="rounded-lg border border-slate-300 px-3 py-2 text-sm sm:col-span-2" />
            <textarea value={newTramite.requisitos} onChange={(e) => setNewTramite((t) => ({ ...t, requisitos: e.target.value }))}
              placeholder="Requisitos (uno por línea)" rows={2} className="rounded-lg border border-slate-300 px-3 py-2 text-sm" />
            <textarea value={newTramite.pasos} onChange={(e) => setNewTramite((t) => ({ ...t, pasos: e.target.value }))}
              placeholder="Pasos (uno por línea)" rows={2} className="rounded-lg border border-slate-300 px-3 py-2 text-sm" />
            <button className="rounded-lg bg-slate-900 px-4 py-2 text-sm font-semibold text-white sm:col-span-2">Agregar al MCP de empresa</button>
          </form>
          <div className="mt-4 flex flex-wrap items-center gap-2 border-t border-slate-100 pt-4">
            <span className="text-sm font-medium text-slate-600">Importar documento → trámite:</span>
            <select value={importDoc} onChange={(e) => setImportDoc(e.target.value)}
              className="rounded-lg border border-slate-300 px-3 py-2 text-sm">
              <option value="">Selecciona un documento…</option>
              {docs.map((d) => <option key={d.id} value={d.id}>{d.filename}</option>)}
            </select>
            <button onClick={doImport} disabled={!importDoc}
              className="rounded-lg bg-slate-900 px-4 py-2 text-sm font-semibold text-white disabled:opacity-40">
              Importar al MCP
            </button>
          </div>
          {tramiteMsg && <div className="mt-2 text-xs text-slate-500">{tramiteMsg}</div>}
          {tramites.filter((t) => t.source === "empresa").length > 0 && (
            <div className="mt-3 space-y-1">
              {tramites.filter((t) => t.source === "empresa").map((t) => (
                <div key={t.id} className="flex items-center justify-between rounded-lg border border-slate-200 px-3 py-2 text-sm">
                  <span className="text-slate-700">{t.title} {t.region && <span className="text-slate-400">· {t.region}</span>}</span>
                  <span className="rounded-full bg-violet-100 px-2 py-0.5 text-xs text-violet-700">empresa</span>
                </div>
              ))}
            </div>
          )}
        </div>

        <div className="rounded-2xl border border-slate-200 bg-white p-5">
          <h2 className="mb-1 font-semibold text-slate-800">Propuestas de casos de uso</h2>
          <p className="mb-4 text-sm text-slate-500">
            Revisa lo que piden los usuarios y cúralos al catálogo con un clic.
          </p>
          {proposals.length === 0 ? (
            <div className="text-sm text-slate-400">Sin propuestas todavía.</div>
          ) : (
            <div className="space-y-2">
              {proposals.map((p) => (
                <div key={p.id} className="flex items-center justify-between rounded-lg border border-slate-200 p-3">
                  <div>
                    <div className="text-sm font-medium text-slate-800">{p.title}</div>
                    <div className="text-xs text-slate-400">
                      {p.category}
                      {p.description ? ` · ${p.description}` : ""}
                    </div>
                  </div>
                  {p.status === "proposed" ? (
                    <div className="flex gap-2">
                      <button
                        onClick={() => curate(p.id)}
                        className="rounded-md bg-emerald-600 px-3 py-1 text-xs font-semibold text-white"
                      >
                        Curar al catálogo
                      </button>
                      <button
                        onClick={() => reject(p.id)}
                        className="rounded-md border border-slate-300 px-3 py-1 text-xs font-semibold text-slate-600"
                      >
                        Rechazar
                      </button>
                    </div>
                  ) : (
                    <span className={`rounded-full px-2 py-0.5 text-xs ${p.status === "curated" ? "bg-emerald-100 text-emerald-700" : "bg-slate-100 text-slate-500"}`}>
                      {p.status === "curated" ? "En catálogo" : "Rechazada"}
                    </span>
                  )}
                </div>
              ))}
            </div>
          )}
        </div>

        {eff && (
          <div className="rounded-2xl border border-slate-200 bg-white p-5">
            <h2 className="mb-1 font-semibold text-slate-800">Eficiencia de tokens (gasto)</h2>
            <p className="mb-4 text-xs text-slate-400">
              El modelo barato condensa contexto grande antes de ir a premium. Define el umbral y un
              tope de tokens por consulta (0 = sin tope). Ahorro acumulado estimado:
              <b> {eff.tokens_saved_total.toLocaleString()} tokens</b>.
            </p>
            <div className="flex flex-wrap items-end gap-3">
              <label className="flex items-center gap-1.5 text-sm text-slate-700">
                <input type="checkbox" checked={eff.condense_enabled} onChange={(e) => setEff({ ...eff, condense_enabled: e.target.checked })} />
                Condensar contexto
              </label>
              <label className="flex items-center gap-1.5 text-sm text-slate-700" title="Reordena los resultados del RAG con el reranker (NaN) para más precisión">
                <input type="checkbox" checked={eff.rerank_enabled} onChange={(e) => setEff({ ...eff, rerank_enabled: e.target.checked })} />
                Reranking RAG
              </label>
              <div>
                <div className="text-xs text-slate-400">Umbral (caracteres)</div>
                <input type="number" value={eff.condense_threshold_chars} onChange={(e) => setEff({ ...eff, condense_threshold_chars: Number(e.target.value) })}
                  className="w-32 rounded-lg border border-slate-300 px-3 py-2 text-sm" />
              </div>
              <div>
                <div className="text-xs text-slate-400">Tope tokens / consulta</div>
                <input type="number" value={eff.max_tokens_per_request} onChange={(e) => setEff({ ...eff, max_tokens_per_request: Number(e.target.value) })}
                  className="w-32 rounded-lg border border-slate-300 px-3 py-2 text-sm" />
              </div>
              <button onClick={() => api.updateEfficiency({ condense_enabled: eff.condense_enabled, condense_threshold_chars: eff.condense_threshold_chars, max_tokens_per_request: eff.max_tokens_per_request, rerank_enabled: eff.rerank_enabled }).then(setEff).catch(() => {})}
                className="rounded-lg bg-slate-900 px-4 py-2 text-sm font-semibold text-white">Guardar</button>
            </div>
          </div>
        )}

        {providers.length > 0 && (
          <div className="rounded-2xl border border-slate-200 bg-white p-5">
            <h2 className="mb-1 font-semibold text-slate-800">Modelos y conectores (on-prem + externos)</h2>
            <p className="mb-4 text-xs text-slate-400">
              Conecta modelos <b>on-prem</b> (Ollama local, VPC) y externos (NaN/premium). El enrutador de privacidad
              <b> redacta PII y minimiza</b> antes de cualquier salida; lo restringido se queda local. La llave se cifra.
              <br />Para on-prem desde la nube, expón tu lab con un <b>túnel</b> (Cloudflare/ngrok) y pon esa URL pública
              (ej. <code>https://&lt;túnel&gt;/v1</code>). Modelos de tu lab: <code>llama3.2:3b</code>, <code>deepseek-r1:8b</code>.
            </p>
            <div className="grid grid-cols-1 gap-4 lg:grid-cols-2">
              {providers.map((p) => {
                const d = provDraft[p.route] || { enabled: false, base_url: "", model: "", api_key: "" };
                const upd = (patch: Partial<typeof d>) => setProvDraft((s) => ({ ...s, [p.route]: { ...d, ...patch } }));
                return (
                  <div key={p.route} className="rounded-xl border border-slate-200 p-4">
                    <div className="mb-2 flex items-center justify-between">
                      <span className="text-sm font-semibold text-slate-800">
                        {PROVIDER_LABELS[p.route] || p.route}
                        {p.onprem && <span className="ml-2 rounded-full bg-emerald-100 px-2 py-0.5 text-[10px] font-medium text-emerald-700">on-prem</span>}
                      </span>
                      <label className="flex items-center gap-1.5 text-xs text-slate-600">
                        <input type="checkbox" checked={d.enabled} onChange={(e) => upd({ enabled: e.target.checked })} /> Activo
                      </label>
                    </div>
                    <input value={d.base_url} onChange={(e) => upd({ base_url: e.target.value })}
                      placeholder="Base URL (ej. https://api.openai.com/v1)" className="mb-2 w-full rounded-lg border border-slate-300 px-3 py-2 text-sm" />
                    <input value={d.model} onChange={(e) => upd({ model: e.target.value })}
                      placeholder="Modelo (ej. gpt-4o, claude-..., llama-3.1)" className="mb-2 w-full rounded-lg border border-slate-300 px-3 py-2 text-sm" />
                    <input value={d.api_key} onChange={(e) => upd({ api_key: e.target.value })} type="password"
                      placeholder={p.has_key ? "•••••• (guardada — escribe para reemplazar)" : "API key"}
                      className="mb-2 w-full rounded-lg border border-slate-300 px-3 py-2 text-sm" />
                    <div className="flex items-center gap-2">
                      <button onClick={() => saveProvider(p.route)} className="rounded-lg bg-slate-900 px-3 py-1.5 text-xs font-semibold text-white">Guardar</button>
                      <button onClick={() => testProvider(p.route)} className="rounded-lg border border-slate-300 px-3 py-1.5 text-xs font-semibold text-slate-700 hover:bg-slate-50">Probar conexión</button>
                    </div>
                    {provTest[p.route] && <div className="mt-2 text-xs text-slate-500">{provTest[p.route]}</div>}
                  </div>
                );
              })}
            </div>
          </div>
        )}

        <div className="rounded-2xl border border-slate-200 bg-white p-5">
          <h2 className="mb-1 font-semibold text-slate-800">Usuarios del tenant</h2>
          <p className="mb-4 text-xs text-slate-400">
            Permisos jerárquicos: el rol y el área deciden qué documentos y contexto ve cada quien.
            General/sin área es visible para todos; Admin, Security y Super Admin ven todas las áreas.
          </p>
          <table className="w-full text-sm">
            <thead className="border-b border-slate-200 text-xs uppercase text-slate-400">
              <tr>
                <th className="py-2 text-left">Nombre</th>
                <th className="py-2 text-left">Correo</th>
                <th className="py-2 text-left">Rol</th>
                <th className="py-2 text-left">Área</th>
                <th className="py-2 text-left">Licencia</th>
                <th className="py-2 text-center">MFA</th>
              </tr>
            </thead>
            <tbody>
              {users.map((u) => (
                <tr key={u.id} className="border-b border-slate-100">
                  <td className="py-2 text-slate-700">{u.name}</td>
                  <td className="py-2 text-slate-500">{u.email}</td>
                  <td className="py-2">
                    <select value={u.role} onChange={(e) => api.updateUser(u.id, { role: e.target.value }).then(() => api.users().then(setUsers)).catch((err) => setError(err.message))}
                      className="rounded-md border border-slate-200 bg-white px-2 py-1 text-xs">
                      {["user", "admin", "security", "devops", "super_admin"].map((r) => (
                        <option key={r} value={r}>{ROLE_LABELS[r]}</option>
                      ))}
                    </select>
                  </td>
                  <td className="py-2">
                    <input defaultValue={u.area} placeholder="—"
                      onBlur={(e) => e.target.value !== u.area && api.updateUser(u.id, { area: e.target.value }).then(() => api.users().then(setUsers)).catch(() => {})}
                      className="w-28 rounded-md border border-slate-200 px-2 py-1 text-xs" />
                  </td>
                  <td className="py-2">
                    <select value={u.license} onChange={(e) => api.updateUser(u.id, { license: e.target.value }).then(() => api.users().then(setUsers)).catch(() => {})}
                      className="rounded-md border border-slate-200 bg-white px-2 py-1 text-xs">
                      {["basic", "pro", "enterprise"].map((l) => <option key={l} value={l}>{l}</option>)}
                    </select>
                  </td>
                  <td className="py-2 text-center">{u.mfa_enabled ? "✓" : "—"}</td>
                </tr>
              ))}
            </tbody>
          </table>
        </div>

        {tenants.length > 0 && (
          <div className="rounded-2xl border border-violet-200 bg-white p-5">
            <h2 className="mb-1 font-semibold text-slate-800">Super Admin · Todas las organizaciones</h2>
            <p className="mb-4 text-xs text-slate-400">Vista global entre tenants (solo super admin).</p>
            <table className="w-full text-sm">
              <thead className="border-b border-slate-200 text-xs uppercase text-slate-400">
                <tr>
                  <th className="py-2 text-left">Organización</th>
                  <th className="py-2 text-left">Plan</th>
                  <th className="py-2 text-left">Estado</th>
                  <th className="py-2 text-left">País</th>
                  <th className="py-2 text-right">Asientos</th>
                  <th className="py-2 text-right">Usuarios</th>
                  <th className="py-2 text-right">Documentos</th>
                </tr>
              </thead>
              <tbody>
                {tenants.map((t) => (
                  <tr key={t.id} className="border-b border-slate-100">
                    <td className="py-2 font-medium text-slate-700">{t.name}</td>
                    <td className="py-2 text-slate-500">{t.plan}</td>
                    <td className="py-2 text-slate-500">{t.subscription_status}</td>
                    <td className="py-2 text-slate-500">{t.country}</td>
                    <td className="py-2 text-right tabular-nums text-slate-600">{t.seats_licensed}</td>
                    <td className="py-2 text-right tabular-nums text-slate-600">{t.users}</td>
                    <td className="py-2 text-right tabular-nums text-slate-600">{t.documents}</td>
                  </tr>
                ))}
              </tbody>
            </table>
          </div>
        )}
      </div>
    </Shell>
  );
}
