"use client";

import { PageHeader, Shell } from "@/components/Shell";
import { api } from "@/lib/api";
import { CheckCircle2, KeyRound, Link2, Mail, Trash2, Webhook } from "lucide-react";
import { useEffect, useState } from "react";

type MailProvider = { provider: string; label: string; enabled: boolean; configured: boolean; connected: boolean; identifier: string };

export default function IntegrationsPage() {
  const [keys, setKeys] = useState<{ id: string; name: string; prefix: string; status: string }[]>([]);
  const [newKeyName, setNewKeyName] = useState("");
  const [newKeyValue, setNewKeyValue] = useState("");
  const [templates, setTemplates] = useState<Awaited<ReturnType<typeof api.connectorTemplates>>>([]);
  const [connectors, setConnectors] = useState<{ id: string; kind: string; name: string; enabled: boolean }[]>([]);
  const [cnx, setCnx] = useState({ kind: "crm", name: "", base_url: "", auth_header: "Authorization", token: "" });
  const [cnxMsg, setCnxMsg] = useState("");
  const [webhooks, setWebhooks] = useState<{ id: string; name: string; default_event: string; url: string }[]>([]);
  const [whName, setWhName] = useState("");
  const [whSecret, setWhSecret] = useState<{ url: string; secret: string } | null>(null);
  const [mailProviders, setMailProviders] = useState<MailProvider[]>([]);
  const [mailMsg, setMailMsg] = useState("");
  const apiBase = api.base;

  function load() {
    api.apiKeys().then(setKeys).catch(() => {});
    api.connectors().then(setConnectors).catch(() => {});
    api.webhooks().then(setWebhooks).catch(() => {});
    api.oauthProviders().then((r) => setMailProviders(r.providers)).catch(() => {});
  }
  useEffect(() => {
    load();
    api.connectorTemplates().then(setTemplates).catch(() => {});
    const c = new URLSearchParams(window.location.search).get("connected");
    if (c === "error") setMailMsg("No se pudo conectar el correo. Intenta de nuevo.");
    else if (c) setMailMsg(`Correo conectado correctamente (${c}).`);
  }, []);

  async function connectMail(provider: string) {
    try {
      const { authorize_url } = await api.oauthAuthorize(provider);
      window.location.href = authorize_url;
    } catch (e) {
      setMailMsg(e instanceof Error ? e.message : "No se pudo iniciar la conexión");
    }
  }
  async function disconnectMail(provider: string) {
    await api.oauthDisconnect(provider);
    load();
  }

  async function createKey() {
    const r = await api.createApiKey(newKeyName || "Integración");
    setNewKeyValue(r.api_key);
    setNewKeyName("");
    load();
  }
  function applyTemplate(id: string) {
    const t = templates.find((x) => x.id === id);
    if (t) setCnx({ kind: t.kind, name: t.name, base_url: t.base_url, auth_header: t.auth_header, token: "" });
  }
  async function addConnector(e: React.FormEvent) {
    e.preventDefault();
    if (!cnx.name || !cnx.base_url) return;
    await api.createConnector(cnx);
    setCnx({ kind: "crm", name: "", base_url: "", auth_header: "Authorization", token: "" });
    load();
  }
  async function createWebhook() {
    const r = await api.createWebhook({ name: whName || "Webhook entrante", default_event: "document_uploaded" });
    setWhSecret({ url: r.url, secret: r.secret });
    setWhName("");
    load();
  }

  return (
    <Shell>
      <PageHeader title="Integraciones" subtitle="Conecta MaestroAI con tus sistemas: CRM, ERP, delivery y más." />
      <div className="space-y-6 p-8">
        {/* Mailbox connect (OAuth) */}
        <div className="rounded-2xl border border-slate-200 bg-white p-5">
          <div className="mb-1 flex items-center gap-2"><Mail className="h-5 w-5 text-violet-600" /><h2 className="font-semibold text-slate-800">Conectar correo (Outlook / Gmail)</h2></div>
          <p className="mb-3 text-sm text-slate-500">
            Conecta tu cuenta para que el caso <b>«Resumen de correo y agenda»</b> lea tu bandeja y
            calendario reales. El contenido pasa por el enrutador de privacidad (PII redactado).
          </p>
          {mailMsg && <div className="mb-3 rounded-lg border border-violet-200 bg-violet-50 px-3 py-2 text-xs text-violet-800">{mailMsg}</div>}
          <div className="space-y-2">
            {mailProviders.map((p) => (
              <div key={p.provider} className="flex items-center justify-between rounded-lg border border-slate-200 px-3 py-2 text-sm">
                <span className="flex items-center gap-2 text-slate-700">
                  <Mail className="h-4 w-4 text-slate-400" /> {p.label}
                  {p.connected && <span className="flex items-center gap-1 text-emerald-600"><CheckCircle2 className="h-4 w-4" /> {p.identifier || "conectado"}</span>}
                  {!p.configured && <span className="text-xs text-amber-600">· no configurado por el admin</span>}
                </span>
                {p.connected ? (
                  <button onClick={() => disconnectMail(p.provider)} className="text-xs font-semibold text-red-600">Desconectar</button>
                ) : (
                  <button onClick={() => connectMail(p.provider)} disabled={!p.configured}
                    className="rounded-md bg-violet-600 px-3 py-1 text-xs font-semibold text-white disabled:opacity-40">
                    Conectar
                  </button>
                )}
              </div>
            ))}
            {mailProviders.length === 0 && <div className="text-xs text-slate-400">Cargando proveedores…</div>}
          </div>
        </div>

        {/* API keys */}
        <div className="rounded-2xl border border-slate-200 bg-white p-5">
          <div className="mb-1 flex items-center gap-2"><KeyRound className="h-5 w-5 text-violet-600" /><h2 className="font-semibold text-slate-800">API keys (entrada)</h2></div>
          <p className="mb-3 text-sm text-slate-500">Para que otros sistemas llamen a MaestroAI vía <code>/v1</code> con el header <code>X-API-Key</code>.</p>
          <div className="flex flex-wrap gap-2">
            <input value={newKeyName} onChange={(e) => setNewKeyName(e.target.value)} placeholder="Nombre (ej. CRM Acme)"
              className="rounded-lg border border-slate-300 px-3 py-2 text-sm" />
            <button onClick={createKey} className="rounded-lg bg-slate-900 px-4 py-2 text-sm font-semibold text-white">Generar API key</button>
          </div>
          {newKeyValue && (
            <div className="mt-2 rounded-lg border border-amber-200 bg-amber-50 px-3 py-2 text-xs text-amber-800">
              Cópiala ahora (no se vuelve a mostrar): <code className="break-all font-mono">{newKeyValue}</code>
            </div>
          )}
          <div className="mt-2 space-y-1">
            {keys.map((k) => (
              <div key={k.id} className="flex items-center justify-between rounded-lg border border-slate-200 px-3 py-2 text-sm">
                <span className="text-slate-700">{k.name} <span className="font-mono text-slate-400">{k.prefix}…</span></span>
                {k.status === "active" ? <button onClick={() => api.revokeApiKey(k.id).then(load)} className="text-xs font-semibold text-red-600">Revocar</button> : <span className="text-xs text-slate-400">revocada</span>}
              </div>
            ))}
          </div>
          <pre className="mt-3 overflow-auto rounded-lg bg-slate-900 p-3 text-xs text-slate-100">{`curl -X POST ${apiBase}/v1/cases/cotizacion/run \\
  -H "X-API-Key: mai_..." -H "Content-Type: application/json" \\
  -d '{"inputs":{"cliente":"ACME","concepto":"servicio","monto":"5000"}}'`}</pre>
        </div>

        {/* Connectors */}
        <div className="rounded-2xl border border-slate-200 bg-white p-5">
          <div className="mb-1 flex items-center gap-2"><Link2 className="h-5 w-5 text-blue-600" /><h2 className="font-semibold text-slate-800">Conectores (salida)</h2></div>
          <p className="mb-3 text-sm text-slate-500">MaestroAI envía datos a tus sistemas. Empieza con una plantilla:</p>
          <div className="mb-3 flex flex-wrap gap-2">
            {templates.map((t) => (
              <button key={t.id} onClick={() => applyTemplate(t.id)}
                className="rounded-full border border-slate-200 px-3 py-1 text-xs font-medium text-slate-600 hover:border-violet-400">
                {t.name} <span className="uppercase text-slate-400">{t.kind}</span>
              </button>
            ))}
          </div>
          <form onSubmit={addConnector} className="flex flex-wrap gap-2">
            <select value={cnx.kind} onChange={(e) => setCnx({ ...cnx, kind: e.target.value })} className="rounded-lg border border-slate-300 px-3 py-2 text-sm">
              <option value="crm">CRM</option><option value="erp">ERP</option><option value="delivery">Delivery</option><option value="custom">Custom</option>
            </select>
            <input value={cnx.name} onChange={(e) => setCnx({ ...cnx, name: e.target.value })} placeholder="Nombre" className="rounded-lg border border-slate-300 px-3 py-2 text-sm" />
            <input value={cnx.base_url} onChange={(e) => setCnx({ ...cnx, base_url: e.target.value })} placeholder="https://… (endpoint)" className="flex-1 rounded-lg border border-slate-300 px-3 py-2 text-sm" />
            <input value={cnx.token} onChange={(e) => setCnx({ ...cnx, token: e.target.value })} type="password" placeholder="Token (opcional)" className="rounded-lg border border-slate-300 px-3 py-2 text-sm" />
            <button className="rounded-lg bg-slate-900 px-4 py-2 text-sm font-semibold text-white">Agregar conector</button>
          </form>
          <div className="mt-2 space-y-1">
            {connectors.map((c) => (
              <div key={c.id} className="flex items-center justify-between rounded-lg border border-slate-200 px-3 py-2 text-sm">
                <span className="text-slate-700"><span className="uppercase text-slate-400">{c.kind}</span> · {c.name}</span>
                <div className="flex gap-3">
                  <button onClick={() => api.testConnector(c.id).then((r) => setCnxMsg(`${c.name}: ${r.status} · ${r.detail}`))} className="text-xs font-semibold text-violet-700">Probar</button>
                  <button onClick={() => api.deleteConnector(c.id).then(load)} className="text-slate-400 hover:text-red-600"><Trash2 className="h-4 w-4" /></button>
                </div>
              </div>
            ))}
          </div>
          {cnxMsg && <div className="mt-2 text-xs text-slate-500">{cnxMsg}</div>}
        </div>

        {/* Inbound webhooks */}
        <div className="rounded-2xl border border-slate-200 bg-white p-5">
          <div className="mb-1 flex items-center gap-2"><Webhook className="h-5 w-5 text-emerald-600" /><h2 className="font-semibold text-slate-800">Webhooks entrantes (firmados)</h2></div>
          <p className="mb-3 text-sm text-slate-500">Un sistema externo notifica eventos firmando el cuerpo con HMAC-SHA256 (header <code>X-Signature</code>).</p>
          <div className="flex flex-wrap gap-2">
            <input value={whName} onChange={(e) => setWhName(e.target.value)} placeholder="Nombre (ej. CRM events)" className="rounded-lg border border-slate-300 px-3 py-2 text-sm" />
            <button onClick={createWebhook} className="rounded-lg bg-slate-900 px-4 py-2 text-sm font-semibold text-white">Crear webhook</button>
          </div>
          {whSecret && (
            <div className="mt-2 rounded-lg border border-amber-200 bg-amber-50 px-3 py-2 text-xs text-amber-800">
              URL: <code>{apiBase}{whSecret.url}</code><br />Secreto (cópialo ahora): <code className="break-all font-mono">{whSecret.secret}</code>
            </div>
          )}
          <div className="mt-2 space-y-1">
            {webhooks.map((w) => (
              <div key={w.id} className="flex items-center justify-between rounded-lg border border-slate-200 px-3 py-2 text-sm">
                <span className="text-slate-700">{w.name} <span className="font-mono text-slate-400">{w.url}</span></span>
                <button onClick={() => api.deleteWebhook(w.id).then(load)} className="text-slate-400 hover:text-red-600"><Trash2 className="h-4 w-4" /></button>
              </div>
            ))}
          </div>
        </div>
      </div>
    </Shell>
  );
}
