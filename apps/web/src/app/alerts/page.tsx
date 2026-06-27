"use client";

import { PageHeader, Shell } from "@/components/Shell";
import { api } from "@/lib/api";
import { Bell, Plus, TestTube, Trash2 } from "lucide-react";
import { useEffect, useState } from "react";

type Rule = { id: string; name: string; event_type: string; channels: string[]; webhook_url: string; telegram_chat_id: string; has_telegram_token: boolean; enabled: boolean };
const ALL_CHANNELS = [
  { id: "popup", label: "Pop-up (in-app)" },
  { id: "webhook", label: "Webhook" },
  { id: "telegram", label: "Telegram" },
  { id: "whatsapp", label: "WhatsApp (vía proveedor/Zapier)" },
];

export default function AlertsPage() {
  const [rules, setRules] = useState<Rule[]>([]);
  const [events, setEvents] = useState<{ key: string; label: string }[]>([]);
  const [form, setForm] = useState({ name: "", event_type: "finetune", channels: ["popup"] as string[], webhook_url: "", telegram_token: "", telegram_chat_id: "" });
  const [msg, setMsg] = useState("");

  function load() { api.alertRules().then(setRules).catch(() => {}); }
  useEffect(() => { load(); api.alertEventTypes().then(setEvents).catch(() => {}); }, []);

  function toggleChannel(c: string) {
    setForm((f) => ({ ...f, channels: f.channels.includes(c) ? f.channels.filter((x) => x !== c) : [...f.channels, c] }));
  }

  async function create() {
    if (!form.name.trim()) { setMsg("Pon un nombre."); return; }
    try {
      await api.createAlertRule({ ...form });
      setForm({ name: "", event_type: form.event_type, channels: ["popup"], webhook_url: "", telegram_token: "", telegram_chat_id: "" });
      setMsg("Regla creada."); load();
    } catch (e) { setMsg(e instanceof Error ? e.message : "Error"); }
  }
  async function remove(id: string) { await api.deleteAlertRule(id); load(); }
  async function test() {
    const r = await api.testAlert();
    setMsg(r.fired > 0 ? `Alerta de prueba enviada a ${r.fired} regla(s). Revisa la campana arriba.` : "No hay reglas para el evento «test». Crea una con evento Prueba.");
  }

  const needWebhook = form.channels.includes("webhook") || form.channels.includes("whatsapp");
  const needTelegram = form.channels.includes("telegram");

  return (
    <Shell>
      <PageHeader title="Alertas" subtitle="Recibe avisos cuando ocurren eventos. Canales: pop-up in-app, webhook, Telegram y WhatsApp." />
      <div className="grid grid-cols-1 gap-6 p-8 lg:grid-cols-2">
        {/* Crear regla */}
        <div className="rounded-2xl border border-slate-200 bg-white p-5">
          <h2 className="mb-3 flex items-center gap-1.5 font-semibold text-slate-800"><Bell className="h-4 w-4 text-violet-600" /> Nueva alerta</h2>
          <input value={form.name} onChange={(e) => setForm({ ...form, name: e.target.value })}
            placeholder="Nombre (ej. Avísame de fine-tuning)" className="mb-2 w-full rounded-lg border border-slate-300 px-3 py-2 text-sm" />
          <label className="text-xs font-semibold uppercase tracking-wide text-slate-500">Evento</label>
          <select value={form.event_type} onChange={(e) => setForm({ ...form, event_type: e.target.value })}
            className="mb-3 mt-1 w-full rounded-lg border border-slate-300 px-3 py-2 text-sm">
            {events.map((ev) => <option key={ev.key} value={ev.key}>{ev.label}</option>)}
          </select>
          <div className="mb-2 text-xs font-semibold uppercase tracking-wide text-slate-500">Canales</div>
          <div className="mb-3 grid grid-cols-2 gap-2">
            {ALL_CHANNELS.map((c) => (
              <label key={c.id} className={`flex cursor-pointer items-center gap-2 rounded-lg border px-3 py-2 text-sm ${form.channels.includes(c.id) ? "border-violet-400 bg-violet-50" : "border-slate-200"}`}>
                <input type="checkbox" checked={form.channels.includes(c.id)} onChange={() => toggleChannel(c.id)} />
                {c.label}
              </label>
            ))}
          </div>
          {needWebhook && (
            <input value={form.webhook_url} onChange={(e) => setForm({ ...form, webhook_url: e.target.value })}
              placeholder="URL del webhook (Slack/Teams/WhatsApp vía Zapier/proveedor)" className="mb-2 w-full rounded-lg border border-slate-300 px-3 py-2 text-sm" />
          )}
          {needTelegram && (
            <div className="mb-2 grid grid-cols-1 gap-2">
              <input value={form.telegram_token} onChange={(e) => setForm({ ...form, telegram_token: e.target.value })}
                placeholder="Token del bot de Telegram" className="w-full rounded-lg border border-slate-300 px-3 py-2 text-sm" />
              <input value={form.telegram_chat_id} onChange={(e) => setForm({ ...form, telegram_chat_id: e.target.value })}
                placeholder="chat_id de Telegram" className="w-full rounded-lg border border-slate-300 px-3 py-2 text-sm" />
            </div>
          )}
          <div className="flex gap-2">
            <button onClick={create} className="flex items-center gap-1.5 rounded-lg bg-violet-600 px-4 py-2 text-sm font-semibold text-white"><Plus className="h-4 w-4" /> Crear</button>
            <button onClick={test} className="flex items-center gap-1.5 rounded-lg border border-slate-300 px-4 py-2 text-sm font-semibold text-slate-600"><TestTube className="h-4 w-4" /> Probar</button>
          </div>
          {msg && <div className="mt-3 rounded-lg border border-slate-200 bg-slate-50 px-3 py-2 text-xs text-slate-600">{msg}</div>}
        </div>

        {/* Reglas */}
        <div className="rounded-2xl border border-slate-200 bg-white p-5">
          <h2 className="mb-3 font-semibold text-slate-800">Mis alertas</h2>
          <div className="space-y-2">
            {rules.length === 0 && <p className="text-xs text-slate-400">Aún no tienes alertas configuradas.</p>}
            {rules.map((r) => (
              <div key={r.id} className="flex items-center justify-between rounded-lg border border-slate-100 px-3 py-2 text-sm">
                <span className="min-w-0">
                  <span className="font-medium text-slate-700">{r.name}</span>
                  <span className="block truncate text-xs text-slate-400">{r.event_type} · {r.channels.join(", ")}</span>
                </span>
                <button onClick={() => remove(r.id)} title="Eliminar" className="shrink-0 rounded-md border border-slate-300 p-1 text-red-500"><Trash2 className="h-3.5 w-3.5" /></button>
              </div>
            ))}
          </div>
          <p className="mt-4 text-xs text-slate-400">
            WhatsApp se entrega a través de tu proveedor (Twilio/Meta) o un Zap: usa el canal
            WhatsApp con la URL del webhook de tu proveedor. Telegram es directo con el bot.
          </p>
        </div>
      </div>
    </Shell>
  );
}
