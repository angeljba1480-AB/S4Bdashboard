"use client";

import { PageHeader, Shell } from "@/components/Shell";
import { api } from "@/lib/api";
import { Eye, Mail, Save, Send } from "lucide-react";
import { useEffect, useState } from "react";

const CHANNELS = [
  { id: "popup", label: "Pop-up (in-app)" },
  { id: "email", label: "Correo" },
  { id: "whatsapp", label: "WhatsApp" },
];

type Cfg = { enabled: boolean; account_id: string; schedule: string; channels: string[]; email_to: string; language: string; notes: string; discard_propaganda: boolean; pending_enabled: boolean; pending_days: number; last_run_at: string };

export default function MailDigestPage() {
  const [cfg, setCfg] = useState<Cfg | null>(null);
  const [accounts, setAccounts] = useState<{ id: string; provider: string; identifier: string }[]>([]);
  const [preview, setPreview] = useState("");
  const [msg, setMsg] = useState("");
  const [busy, setBusy] = useState(false);

  useEffect(() => {
    api.mailDigestConfig().then(setCfg).catch(() => {});
    api.oauthProviders().then((r) => setAccounts(r.connections)).catch(() => {});
  }, []);

  function set<K extends keyof Cfg>(k: K, v: Cfg[K]) { setCfg((c) => (c ? { ...c, [k]: v } : c)); }
  function toggleChannel(id: string) {
    setCfg((c) => (c ? { ...c, channels: c.channels.includes(id) ? c.channels.filter((x) => x !== id) : [...c.channels, id] } : c));
  }

  async function save() {
    if (!cfg) return;
    setBusy(true); setMsg("");
    try { await api.setMailDigestConfig(cfg); setMsg("Configuración guardada."); }
    catch (e) { setMsg(e instanceof Error ? e.message : "Error"); }
    finally { setBusy(false); }
  }
  async function doPreview() {
    setBusy(true); setMsg(""); setPreview("");
    try {
      const r = await api.mailDigestPreview();
      if (r.ok) { setPreview(r.text); setMsg(`Generado desde ${r.account} · ${r.counts.messages ?? 0} correos.`); }
      else setMsg(r.message || "No se pudo generar.");
    } catch (e) { setMsg(e instanceof Error ? e.message : "Error"); }
    finally { setBusy(false); }
  }
  async function runNow() {
    setBusy(true); setMsg("");
    try { const r = await api.mailDigestRunNow(); setMsg(`Enviado por: ${Object.keys(r.sent).filter((k) => r.sent[k]).join(", ") || "ningún canal"}.`); }
    catch (e) { setMsg(e instanceof Error ? e.message : "Error"); }
    finally { setBusy(false); }
  }

  if (!cfg) return <Shell><div className="p-8 text-sm text-slate-400">Cargando…</div></Shell>;

  return (
    <Shell>
      <PageHeader title="Resumen de correo automatizado" subtitle="Cada día clasifico tu buzón (categoría/prioridad), descarto propaganda y detecto pendientes; lo recibes por pop-up, correo y/o WhatsApp." />
      <div className="grid grid-cols-1 gap-6 p-8 lg:grid-cols-2">
        <div className="rounded-2xl border border-slate-200 bg-white p-5">
          <h2 className="mb-3 flex items-center gap-1.5 font-semibold text-slate-800"><Mail className="h-4 w-4 text-violet-600" /> Configuración</h2>

          <label className="flex items-center gap-2 text-sm text-slate-700">
            <input type="checkbox" checked={cfg.enabled} onChange={(e) => set("enabled", e.target.checked)} />
            Activar el resumen automático
          </label>

          <div className="mt-3 text-xs font-semibold uppercase tracking-wide text-slate-500">Cuenta de correo</div>
          <select value={cfg.account_id} onChange={(e) => set("account_id", e.target.value)}
            className="mt-1 w-full rounded-lg border border-slate-300 px-3 py-2 text-sm">
            <option value="">Cuenta conectada más reciente</option>
            {accounts.map((a) => <option key={a.id} value={a.id}>{a.identifier} ({a.provider})</option>)}
          </select>

          <div className="mt-3 grid grid-cols-2 gap-3">
            <div>
              <div className="text-xs font-semibold uppercase tracking-wide text-slate-500">Frecuencia</div>
              <select value={cfg.schedule} onChange={(e) => set("schedule", e.target.value)}
                className="mt-1 w-full rounded-lg border border-slate-300 px-3 py-2 text-sm">
                <option value="daily">Todos los días</option>
                <option value="weekdays">Días hábiles</option>
              </select>
            </div>
            <div>
              <div className="text-xs font-semibold uppercase tracking-wide text-slate-500">Idioma</div>
              <select value={cfg.language} onChange={(e) => set("language", e.target.value)}
                className="mt-1 w-full rounded-lg border border-slate-300 px-3 py-2 text-sm">
                <option value="es">Español</option>
                <option value="bilingue">Bilingüe (ES/EN)</option>
              </select>
            </div>
          </div>

          <div className="mt-3 text-xs font-semibold uppercase tracking-wide text-slate-500">Canales</div>
          <div className="mt-1 flex flex-wrap gap-2">
            {CHANNELS.map((c) => (
              <label key={c.id} className={`flex cursor-pointer items-center gap-2 rounded-lg border px-3 py-1.5 text-sm ${cfg.channels.includes(c.id) ? "border-violet-400 bg-violet-50" : "border-slate-200"}`}>
                <input type="checkbox" checked={cfg.channels.includes(c.id)} onChange={() => toggleChannel(c.id)} /> {c.label}
              </label>
            ))}
          </div>
          {cfg.channels.includes("email") && (
            <input value={cfg.email_to} onChange={(e) => set("email_to", e.target.value)}
              placeholder="Destinatarios (coma) — vacío = tu propia cuenta" className="mt-2 w-full rounded-lg border border-slate-300 px-3 py-2 text-sm" />
          )}
          {cfg.channels.includes("whatsapp") && (
            <p className="mt-2 rounded-lg border border-emerald-200 bg-emerald-50 px-3 py-2 text-xs text-emerald-700">
              WhatsApp usa CallMeBot. Configúralo en Alertas → WhatsApp.
            </p>
          )}

          <div className="mt-3 text-xs font-semibold uppercase tracking-wide text-slate-500">Contexto (opcional)</div>
          <textarea value={cfg.notes} onChange={(e) => set("notes", e.target.value)} rows={2}
            placeholder="Ej. Somos una pyme de servicios; prioriza correos de clientes y facturación."
            className="mt-1 w-full rounded-lg border border-slate-300 px-3 py-2 text-sm" />

          <div className="mt-3 space-y-1">
            <label className="flex items-center gap-2 text-sm text-slate-700">
              <input type="checkbox" checked={cfg.discard_propaganda} onChange={(e) => set("discard_propaganda", e.target.checked)} />
              Descartar propaganda/spam del resumen
            </label>
            <label className="flex items-center gap-2 text-sm text-slate-700">
              <input type="checkbox" checked={cfg.pending_enabled} onChange={(e) => set("pending_enabled", e.target.checked)} />
              Detectar pendientes por responder
            </label>
          </div>

          <div className="mt-4 flex flex-wrap gap-2">
            <button onClick={save} disabled={busy} className="flex items-center gap-1.5 rounded-lg bg-violet-600 px-4 py-2 text-sm font-semibold text-white disabled:opacity-50"><Save className="h-4 w-4" /> Guardar</button>
            <button onClick={doPreview} disabled={busy} className="flex items-center gap-1.5 rounded-lg border border-slate-300 px-4 py-2 text-sm font-semibold text-slate-600"><Eye className="h-4 w-4" /> Vista previa</button>
            <button onClick={runNow} disabled={busy} className="flex items-center gap-1.5 rounded-lg bg-slate-900 px-4 py-2 text-sm font-semibold text-white"><Send className="h-4 w-4" /> Enviar ahora</button>
          </div>
          {msg && <div className="mt-3 rounded-lg border border-slate-200 bg-slate-50 px-3 py-2 text-xs text-slate-600">{msg}</div>}
          {cfg.last_run_at && <p className="mt-2 text-xs text-slate-400">Última ejecución: {new Date(cfg.last_run_at).toLocaleString()}</p>}
        </div>

        <div className="rounded-2xl border border-slate-200 bg-white p-5">
          <h2 className="mb-3 font-semibold text-slate-800">Vista previa</h2>
          {preview ? (
            <pre className="max-h-[28rem] overflow-auto whitespace-pre-wrap rounded-lg bg-slate-50 p-3 text-xs text-slate-700">{preview}</pre>
          ) : (
            <p className="text-sm text-slate-400">Pulsa «Vista previa» para generar el resumen de tu correo sin enviarlo.</p>
          )}
          <p className="mt-4 text-xs text-slate-400">
            El envío automático lo dispara un cron (diario o días hábiles) que llama a la plataforma —
            mismo modelo de bajo costo, sin servidor propio. Aquí puedes probarlo manualmente.
          </p>
        </div>
      </div>
    </Shell>
  );
}
