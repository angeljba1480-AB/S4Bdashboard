"use client";

import { PageHeader, Shell } from "@/components/Shell";
import { api } from "@/lib/api";
import { CheckCircle2, Eye, EyeOff, Info, KeyRound, Link2, Mail, Trash2, Webhook } from "lucide-react";
import { useEffect, useState } from "react";

type MailProvider = { provider: string; label: string; kind: string; enabled?: boolean; configured: boolean };
type MailConnection = { id: string; provider: string; label: string; identifier: string };

const IMAP_PRESETS: Record<string, { host: string; port: number }> = {
  "Yahoo": { host: "imap.mail.yahoo.com", port: 993 },
  "iCloud": { host: "imap.mail.me.com", port: 993 },
  "Zoho": { host: "imap.zoho.com", port: 993 },
  "GoDaddy": { host: "imap.secureserver.net", port: 993 },
  "Hostinger": { host: "imap.hostinger.com", port: 993 },
  "Otro / personalizado": { host: "", port: 993 },
};

export default function IntegrationsPage() {
  const [keys, setKeys] = useState<{ id: string; name: string; prefix: string; status: string }[]>([]);
  const [newKeyName, setNewKeyName] = useState("");
  const [newKeyValue, setNewKeyValue] = useState("");
  const [templates, setTemplates] = useState<Awaited<ReturnType<typeof api.connectorTemplates>>>([]);
  const [connectors, setConnectors] = useState<Awaited<ReturnType<typeof api.connectors>>>([]);
  const [cnx, setCnx] = useState({ kind: "crm", name: "", base_url: "", auth_header: "Authorization", token: "" });
  const [cnxMsg, setCnxMsg] = useState("");
  const [openCnx, setOpenCnx] = useState<string | null>(null);
  const [revealed, setRevealed] = useState<Record<string, string>>({});
  const [webhooks, setWebhooks] = useState<{ id: string; name: string; default_event: string; url: string }[]>([]);
  const [whName, setWhName] = useState("");
  const [whSecret, setWhSecret] = useState<{ url: string; secret: string } | null>(null);
  const [mailProviders, setMailProviders] = useState<MailProvider[]>([]);
  const [mailConnections, setMailConnections] = useState<MailConnection[]>([]);
  const [mailMsg, setMailMsg] = useState("");
  const [imap, setImap] = useState({ preset: "Yahoo", host: "imap.mail.yahoo.com", port: 993, email: "", password: "" });
  const [imapBusy, setImapBusy] = useState(false);
  const [sources, setSources] = useState<Awaited<ReturnType<typeof api.dataSources>>>([]);
  const [ds, setDs] = useState({ name: "", dsn: "", query: "", category: "" });
  const [dsMsg, setDsMsg] = useState("");
  const [csv, setCsv] = useState({ name: "", csv_text: "", delimiter: ",", category: "" });
  const [csvMsg, setCsvMsg] = useState("");
  const apiBase = api.base;

  async function addSource() {
    if (!ds.name || !ds.dsn || !ds.query) { setDsMsg("Completa nombre, DSN y consulta."); return; }
    try {
      await api.createDataSource(ds);
      setDs({ name: "", dsn: "", query: "", category: "" });
      setDsMsg("Fuente creada.");
      api.dataSources().then(setSources).catch(() => {});
    } catch (e) { setDsMsg(e instanceof Error ? e.message : "Error"); }
  }
  async function testSource(id: string) {
    try { const r = await api.testDataSource(id); setDsMsg(`OK · columnas: ${r.columns.join(", ")} (${r.total_preview} filas)`); }
    catch (e) { setDsMsg(e instanceof Error ? e.message : "Error al probar"); }
  }
  async function importSource(id: string) {
    try { const r = await api.importDataSource(id); setDsMsg(`Importado ${r.rows} filas → ${r.filename}`); }
    catch (e) { setDsMsg(e instanceof Error ? e.message : "Error al importar"); }
  }
  async function importCsv() {
    if (!csv.csv_text.trim()) { setCsvMsg("Pega el contenido del CSV."); return; }
    try {
      const r = await api.importCsv(csv);
      setCsv({ name: "", csv_text: "", delimiter: ",", category: "" });
      setCsvMsg(`Importado ${r.rows} filas → ${r.filename}`);
    } catch (e) { setCsvMsg(e instanceof Error ? e.message : "Error al importar"); }
  }

  function load() {
    api.apiKeys().then(setKeys).catch(() => {});
    api.connectors().then(setConnectors).catch(() => {});
    api.webhooks().then(setWebhooks).catch(() => {});
    api.oauthProviders().then((r) => { setMailProviders(r.providers); setMailConnections(r.connections); }).catch(() => {});
    api.dataSources().then(setSources).catch(() => {});
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
  async function disconnectConnection(id: string) {
    await api.oauthDisconnectConnection(id);
    load();
  }
  function pickPreset(name: string) {
    const p = IMAP_PRESETS[name];
    setImap((s) => ({ ...s, preset: name, host: p.host, port: p.port }));
  }
  async function connectImap() {
    if (!imap.host || !imap.email || !imap.password) {
      setMailMsg("Completa servidor, correo y contraseña.");
      return;
    }
    setImapBusy(true);
    setMailMsg("");
    try {
      const r = await api.connectImap({ host: imap.host, port: Number(imap.port), email: imap.email, password: imap.password });
      setMailMsg(`Correo conectado por IMAP (${r.identifier}).`);
      setImap((s) => ({ ...s, password: "" }));
      load();
    } catch (e) {
      setMailMsg(e instanceof Error ? e.message : "No se pudo conectar por IMAP");
    } finally {
      setImapBusy(false);
    }
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
  async function toggleConnectorSecret(id: string) {
    if (revealed[id] !== undefined) { setRevealed((s) => { const n = { ...s }; delete n[id]; return n; }); return; }
    try { const r = await api.revealConnector(id); setRevealed((s) => ({ ...s, [id]: r.token || "(sin token)" })); }
    catch (e) { setRevealed((s) => ({ ...s, [id]: e instanceof Error ? e.message : "Error" })); }
  }
  async function toggleDsnSecret(id: string) {
    if (revealed[id] !== undefined) { setRevealed((s) => { const n = { ...s }; delete n[id]; return n; }); return; }
    try { const r = await api.revealDataSource(id); setRevealed((s) => ({ ...s, [id]: r.dsn || "(vacío)" })); }
    catch (e) { setRevealed((s) => ({ ...s, [id]: e instanceof Error ? e.message : "Error" })); }
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
            {mailProviders.filter((p) => p.kind === "oauth").map((p) => {
              const accounts = mailConnections.filter((c) => c.provider === p.provider);
              return (
                <div key={p.provider} className="rounded-lg border border-slate-200 px-3 py-2">
                  <div className="flex items-center justify-between text-sm">
                    <span className="flex items-center gap-2 text-slate-700">
                      <Mail className="h-4 w-4 text-slate-400" /> {p.label} <span className="text-xs text-slate-400">(1 clic)</span>
                      {!p.configured && <span className="text-xs text-amber-600">· no configurado por el admin</span>}
                    </span>
                    <button onClick={() => connectMail(p.provider)} disabled={!p.configured}
                      className="rounded-md bg-violet-600 px-3 py-1 text-xs font-semibold text-white disabled:opacity-40">
                      {accounts.length > 0 ? "Conectar otra cuenta" : "Conectar"}
                    </button>
                  </div>
                  {accounts.map((c) => (
                    <div key={c.id} className="mt-2 flex items-center justify-between rounded-md bg-slate-50 px-3 py-1.5 text-sm">
                      <span className="flex items-center gap-1 text-emerald-600"><CheckCircle2 className="h-4 w-4" /> {c.identifier || "conectado"}</span>
                      <button onClick={() => disconnectConnection(c.id)} className="text-xs font-semibold text-red-600">Desconectar</button>
                    </div>
                  ))}
                </div>
              );
            })}
            {mailProviders.length === 0 && <div className="text-xs text-slate-400">Cargando proveedores…</div>}
          </div>

          {/* Generic IMAP — covers Yahoo, iCloud, Zoho, hosting/corporate, etc. */}
          {(() => {
            const imapAccounts = mailConnections.filter((c) => c.provider === "imap");
            return (
              <div className="mt-3 rounded-lg border border-slate-200 bg-slate-50 p-3">
                <div className="mb-1 text-sm font-medium text-slate-700">Otro correo (IMAP) — Yahoo, iCloud, Zoho, hosting/empresa…</div>
                {imapAccounts.map((c) => (
                  <div key={c.id} className="mb-1 flex items-center justify-between rounded-md bg-white px-3 py-1.5 text-sm">
                    <span className="flex items-center gap-1 text-emerald-600"><CheckCircle2 className="h-4 w-4" /> {c.identifier}</span>
                    <button onClick={() => disconnectConnection(c.id)} className="text-xs font-semibold text-red-600">Desconectar</button>
                  </div>
                ))}
                <p className="mb-2 text-xs text-slate-500">
                  Solo tu correo y contraseña (usa <b>contraseña de aplicación</b> si tu proveedor la pide). Se guarda cifrada.
                </p>
                <div className="grid grid-cols-2 gap-2">
                  <select value={imap.preset} onChange={(e) => pickPreset(e.target.value)} className="rounded-lg border border-slate-300 px-3 py-2 text-sm">
                    {Object.keys(IMAP_PRESETS).map((k) => <option key={k} value={k}>{k}</option>)}
                  </select>
                  <input value={imap.host} onChange={(e) => setImap({ ...imap, host: e.target.value })} placeholder="Servidor IMAP" className="rounded-lg border border-slate-300 px-3 py-2 text-sm" />
                  <input value={imap.email} onChange={(e) => setImap({ ...imap, email: e.target.value })} placeholder="tu@correo.com" className="rounded-lg border border-slate-300 px-3 py-2 text-sm" />
                  <input value={imap.password} onChange={(e) => setImap({ ...imap, password: e.target.value })} type="password" placeholder="Contraseña (de aplicación)" className="rounded-lg border border-slate-300 px-3 py-2 text-sm" />
                </div>
                <button onClick={connectImap} disabled={imapBusy}
                  className="mt-2 rounded-md bg-violet-600 px-3 py-1.5 text-xs font-semibold text-white disabled:opacity-50">
                  {imapBusy ? "Conectando…" : imapAccounts.length > 0 ? "Conectar otra cuenta IMAP" : "Conectar IMAP"}
                </button>
              </div>
            );
          })()}
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
              <div key={c.id} className="rounded-lg border border-slate-200 px-3 py-2 text-sm">
                <div className="flex items-center justify-between">
                  <span className="text-slate-700"><span className="uppercase text-slate-400">{c.kind}</span> · {c.name}
                    {c.has_token && <span className="ml-2 rounded bg-amber-100 px-1.5 py-0.5 text-[10px] font-medium text-amber-700">token</span>}
                  </span>
                  <div className="flex items-center gap-3">
                    <button onClick={() => setOpenCnx(openCnx === c.id ? null : c.id)} title="Ver detalles" className="text-slate-400 hover:text-slate-700"><Info className="h-4 w-4" /></button>
                    <button onClick={() => api.testConnector(c.id).then((r) => setCnxMsg(`${c.name}: ${r.status} · ${r.detail}`))} className="text-xs font-semibold text-violet-700">Probar</button>
                    <button onClick={() => api.deleteConnector(c.id).then(load)} className="text-slate-400 hover:text-red-600"><Trash2 className="h-4 w-4" /></button>
                  </div>
                </div>
                {openCnx === c.id && (
                  <div className="mt-2 space-y-1 rounded-lg bg-slate-50 p-3 text-xs text-slate-600">
                    <div><span className="text-slate-400">Endpoint:</span> <span className="font-mono break-all">{c.base_url || "—"}</span></div>
                    <div><span className="text-slate-400">Header de auth:</span> <span className="font-mono">{c.auth_header}</span></div>
                    <div className="flex items-center gap-2">
                      <span className="text-slate-400">Secreto:</span>
                      <span className="font-mono break-all">{c.has_token ? (revealed[c.id] !== undefined ? revealed[c.id] : "••••••••") : "(sin token)"}</span>
                      {c.has_token && (
                        <button onClick={() => toggleConnectorSecret(c.id)} title={revealed[c.id] !== undefined ? "Ocultar" : "Mostrar"} className="text-slate-400 hover:text-slate-700">
                          {revealed[c.id] !== undefined ? <EyeOff className="h-3.5 w-3.5" /> : <Eye className="h-3.5 w-3.5" />}
                        </button>
                      )}
                    </div>
                    {c.example?.payload_example && (
                      <div className="pt-1">
                        <div className="text-slate-400">Ejemplo de payload ({c.kind}):</div>
                        <pre className="mt-0.5 overflow-x-auto rounded bg-white p-2 font-mono text-[11px] text-slate-600">{JSON.stringify(c.example.payload_example, null, 2)}</pre>
                        {c.example.auth_hint && <div className="text-slate-400">Auth: <span className="font-mono">{c.example.auth_hint}</span></div>}
                      </div>
                    )}
                  </div>
                )}
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

        {/* Data sources — legacy DB connector (read-only) */}
        <div className="rounded-2xl border border-slate-200 bg-white p-5">
          <div className="mb-1 flex items-center gap-2"><Link2 className="h-5 w-5 text-indigo-600" /><h2 className="font-semibold text-slate-800">Fuentes de datos (sistemas a la medida)</h2></div>
          <p className="mb-3 text-sm text-slate-500">
            Conecta una base de datos de <b>solo lectura</b> (DSN tipo
            <code> postgresql://… </code> o <code> mysql://… </code>) con una consulta <b>SELECT</b>;
            el resultado se importa al repositorio + RAG. Para el resto de sistemas usa n8n o webhooks.
          </p>
          <div className="grid grid-cols-1 gap-2 sm:grid-cols-2">
            <input value={ds.name} onChange={(e) => setDs({ ...ds, name: e.target.value })} placeholder="Nombre (ej. Clientes ERP)" className="rounded-lg border border-slate-300 px-3 py-2 text-sm" />
            <input value={ds.category} onChange={(e) => setDs({ ...ds, category: e.target.value })} placeholder="Categoría (opcional)" className="rounded-lg border border-slate-300 px-3 py-2 text-sm" />
            <input value={ds.dsn} onChange={(e) => setDs({ ...ds, dsn: e.target.value })} placeholder="DSN (postgresql://usuario:pass@host:5432/db)" className="rounded-lg border border-slate-300 px-3 py-2 text-sm sm:col-span-2" />
            <input value={ds.query} onChange={(e) => setDs({ ...ds, query: e.target.value })} placeholder="SELECT nombre, monto FROM clientes" className="rounded-lg border border-slate-300 px-3 py-2 text-sm sm:col-span-2" />
          </div>
          <button onClick={addSource} className="mt-2 rounded-lg bg-slate-900 px-4 py-2 text-sm font-semibold text-white">Agregar fuente</button>
          {dsMsg && <div className="mt-2 text-xs text-slate-500">{dsMsg}</div>}
          <div className="mt-3 space-y-1">
            {sources.map((s) => (
              <div key={s.id} className="rounded-lg border border-slate-200 px-3 py-2 text-sm">
                <div className="flex items-center justify-between">
                  <span className="truncate text-slate-700">{s.name} <span className="font-mono text-xs text-slate-400">{s.query.slice(0, 40)}…</span></span>
                  <div className="flex flex-shrink-0 items-center gap-3">
                    <button onClick={() => toggleDsnSecret(s.id)} title="Ver DSN (sensible)" className="text-slate-400 hover:text-slate-700">
                      {revealed[s.id] !== undefined ? <EyeOff className="h-4 w-4" /> : <Eye className="h-4 w-4" />}
                    </button>
                    <button onClick={() => testSource(s.id)} className="text-xs font-semibold text-violet-700">Probar</button>
                    <button onClick={() => importSource(s.id)} className="text-xs font-semibold text-emerald-700">Importar</button>
                    <button onClick={() => api.deleteDataSource(s.id).then(() => api.dataSources().then(setSources))} className="text-slate-400 hover:text-red-600"><Trash2 className="h-4 w-4" /></button>
                  </div>
                </div>
                {revealed[s.id] !== undefined && (
                  <div className="mt-1 rounded bg-slate-50 p-2 font-mono text-[11px] break-all text-slate-600">{revealed[s.id]}</div>
                )}
              </div>
            ))}
          </div>
        </div>

        {/* CSV import — legacy systems that can only export flat files */}
        <div className="rounded-2xl border border-slate-200 bg-white p-5">
          <div className="mb-1 flex items-center gap-2"><Link2 className="h-5 w-5 text-indigo-600" /><h2 className="font-semibold text-slate-800">Importar CSV (exportaciones de sistemas legados)</h2></div>
          <p className="mb-3 text-sm text-slate-500">
            ¿El sistema no tiene API pero exporta <b>CSV/Excel</b>? Pega el contenido aquí
            (la primera fila son los encabezados) y se importa al repositorio + RAG, clasificado y cifrado.
          </p>
          <div className="grid grid-cols-1 gap-2 sm:grid-cols-3">
            <input value={csv.name} onChange={(e) => setCsv({ ...csv, name: e.target.value })} placeholder="Nombre (ej. Cartera CSV)" className="rounded-lg border border-slate-300 px-3 py-2 text-sm" />
            <input value={csv.category} onChange={(e) => setCsv({ ...csv, category: e.target.value })} placeholder="Categoría (opcional)" className="rounded-lg border border-slate-300 px-3 py-2 text-sm" />
            <input value={csv.delimiter} onChange={(e) => setCsv({ ...csv, delimiter: e.target.value })} placeholder="Delimitador (, o ;)" maxLength={1} className="rounded-lg border border-slate-300 px-3 py-2 text-sm" />
          </div>
          <textarea value={csv.csv_text} onChange={(e) => setCsv({ ...csv, csv_text: e.target.value })} placeholder={"nombre,monto\nACME,5000\nGlobex,8200"} rows={5} className="mt-2 w-full rounded-lg border border-slate-300 px-3 py-2 font-mono text-xs" />
          <button onClick={importCsv} className="mt-2 rounded-lg bg-slate-900 px-4 py-2 text-sm font-semibold text-white">Importar CSV</button>
          {csvMsg && <div className="mt-2 text-xs text-slate-500">{csvMsg}</div>}
        </div>
      </div>
    </Shell>
  );
}
