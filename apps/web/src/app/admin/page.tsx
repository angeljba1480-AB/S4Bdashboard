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

  function loadProposals() {
    api.recipeProposals().then(setProposals).catch(() => {});
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
