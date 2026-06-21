"use client";

import { PageHeader, Shell } from "@/components/Shell";
import { api } from "@/lib/api";
import { useEffect, useState } from "react";

type Security = Awaited<ReturnType<typeof api.security>>;
type N8n = Awaited<ReturnType<typeof api.getN8n>>;

export default function AdminPage() {
  const [routes, setRoutes] = useState<{ route: string; provider: string; enabled: boolean; model: string; mode: string }[]>([]);
  const [users, setUsers] = useState<{ id: string; email: string; name: string; role: string; mfa_enabled: boolean }[]>([]);
  const [security, setSecurity] = useState<Security | null>(null);
  const [n8n, setN8n] = useState<N8n | null>(null);
  const [n8nUrl, setN8nUrl] = useState("");
  const [n8nKey, setN8nKey] = useState("");
  const [n8nMsg, setN8nMsg] = useState("");
  const [proposals, setProposals] = useState<
    { id: string; title: string; description: string; category: string; status: string }[]
  >([]);
  const [error, setError] = useState("");

  const [brand, setBrand] = useState({ brand_name: "", brand_logo_url: "", brand_color: "", brand_tagline: "" });
  const [brandMsg, setBrandMsg] = useState("");
  const [billing, setBilling] = useState<Awaited<ReturnType<typeof api.getBilling>> | null>(null);
  const [newUser, setNewUser] = useState({ email: "", name: "", role: "user" });
  const [billingMsg, setBillingMsg] = useState("");

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
      setNewUser({ email: "", name: "", role: "user" });
      setBillingMsg("✓ Usuario agregado");
      api.users().then(setUsers).catch(() => {});
      loadBilling();
    } catch (err) {
      setBillingMsg(err instanceof Error ? err.message : "Error (¿asientos agotados?)");
    }
  }

  function loadProposals() {
    api.recipeProposals().then(setProposals).catch(() => {});
  }
  function loadBranding() {
    api.getBranding()
      .then((b) => setBrand({ brand_name: b.brand_name, brand_logo_url: b.brand_logo_url, brand_color: b.brand_color, brand_tagline: b.brand_tagline }))
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
    api.security().then(setSecurity).catch(() => {});
    loadN8n();
    loadProposals();
    loadBranding();
    loadBilling();
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
      <PageHeader title="Administración" subtitle="Usuarios, roles, modelos habilitados y rutas de privacidad." />
      <div className="space-y-6 p-8">
        {error && <div className="rounded-lg bg-red-50 px-4 py-2 text-sm text-red-600">{error}</div>}

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
                <button className="rounded-lg bg-slate-900 px-4 py-2 text-sm font-semibold text-white">Agregar usuario</button>
              </form>
            </div>
            {billingMsg && <div className="mt-2 text-xs text-slate-500">{billingMsg}</div>}
          </div>
        )}

        <div className="rounded-2xl border border-slate-200 bg-white p-5">
          <h2 className="mb-1 font-semibold text-slate-800">Marca (white-label)</h2>
          <p className="mb-4 text-sm text-slate-500">
            Personaliza el portal para tu organización: nombre, logo y color. Cada tenant tiene la suya.
          </p>
          <form onSubmit={saveBranding} className="grid grid-cols-1 gap-3 sm:grid-cols-2">
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

        <div className="rounded-2xl border border-slate-200 bg-white p-5">
          <h2 className="mb-4 font-semibold text-slate-800">Usuarios del tenant</h2>
          <table className="w-full text-sm">
            <thead className="border-b border-slate-200 text-xs uppercase text-slate-400">
              <tr>
                <th className="py-2 text-left">Nombre</th>
                <th className="py-2 text-left">Correo</th>
                <th className="py-2 text-left">Rol</th>
                <th className="py-2 text-center">MFA</th>
              </tr>
            </thead>
            <tbody>
              {users.map((u) => (
                <tr key={u.id} className="border-b border-slate-100">
                  <td className="py-2 text-slate-700">{u.name}</td>
                  <td className="py-2 text-slate-500">{u.email}</td>
                  <td className="py-2 text-slate-500">{u.role}</td>
                  <td className="py-2 text-center">{u.mfa_enabled ? "✓" : "—"}</td>
                </tr>
              ))}
            </tbody>
          </table>
        </div>
      </div>
    </Shell>
  );
}
