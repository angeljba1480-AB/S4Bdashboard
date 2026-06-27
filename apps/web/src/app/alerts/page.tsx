"use client";

import { PageHeader, Shell } from "@/components/Shell";
import { api } from "@/lib/api";
import { Bell, Plus, TestTube, Trash2 } from "lucide-react";
import { useEffect, useState } from "react";

type Rule = { id: string; name: string; event_type: string; channels: string[]; webhook_url: string; telegram_chat_id: string; has_telegram_token: boolean; schedule: string; last_digest_at: string; enabled: boolean };
const ALL_CHANNELS = [
  { id: "popup", label: "Pop-up (in-app)" },
  { id: "webhook", label: "Webhook" },
  { id: "telegram", label: "Telegram" },
  { id: "whatsapp", label: "WhatsApp (CallMeBot)" },
];
const SCHEDULES = [
  { id: "", label: "Tiempo real (cuando ocurre)" },
  { id: "daily", label: "Resumen diario (digest)" },
  { id: "weekly", label: "Resumen semanal (digest)" },
];

export default function AlertsPage() {
  const [rules, setRules] = useState<Rule[]>([]);
  const [events, setEvents] = useState<{ key: string; label: string }[]>([]);
  const [form, setForm] = useState({ name: "", event_type: "finetune", channels: ["popup"] as string[], webhook_url: "", telegram_token: "", telegram_chat_id: "", schedule: "" });
  const [msg, setMsg] = useState("");
  const [threshold, setThreshold] = useState(0);
  const [wa, setWa] = useState({ phone: "", apikey: "", configured: false });
  const [waMsg, setWaMsg] = useState("");

  function load() { api.alertRules().then(setRules).catch(() => {}); }
  useEffect(() => {
    load();
    api.alertEventTypes().then(setEvents).catch(() => {});
    api.getAlertThreshold().then((r) => setThreshold(r.spend_threshold_usd)).catch(() => {});
    api.whatsappConfig().then((r) => setWa((s) => ({ ...s, phone: r.phone, configured: r.configured }))).catch(() => {});
  }, []);

  async function saveWa() {
    try {
      const r = await api.setWhatsappConfig(wa.phone.trim(), wa.apikey.trim());
      setWa((s) => ({ ...s, phone: r.phone, configured: r.configured, apikey: "" }));
      setWaMsg(r.configured ? "WhatsApp configurado." : "WhatsApp desconectado.");
    } catch (e) { setWaMsg(e instanceof Error ? e.message : "Error"); }
  }
  async function testWa() {
    try { const r = await api.testWhatsapp(); setWaMsg(r.ok ? "Mensaje de prueba enviado a tu WhatsApp." : r.detail); }
    catch (e) { setWaMsg(e instanceof Error ? e.message : "Error"); }
  }

  function toggleChannel(c: string) {
    setForm((f) => ({ ...f, channels: f.channels.includes(c) ? f.channels.filter((x) => x !== c) : [...f.channels, c] }));
  }

  async function create() {
    if (!form.name.trim()) { setMsg("Pon un nombre."); return; }
    try {
      await api.createAlertRule({ ...form });
      setForm({ name: "", event_type: form.event_type, channels: ["popup"], webhook_url: "", telegram_token: "", telegram_chat_id: "", schedule: form.schedule });
      setMsg("Regla creada."); load();
    } catch (e) { setMsg(e instanceof Error ? e.message : "Error"); }
  }
  async function remove(id: string) { await api.deleteAlertRule(id); load(); }
  async function test() {
    const r = await api.testAlert();
    setMsg(r.fired > 0 ? `Alerta de prueba enviada a ${r.fired} regla(s). Revisa la campana arriba.` : "No hay reglas para el evento «test». Crea una con evento Prueba.");
  }
  async function runDigest(freq: string) {
    const r = await api.runDigests(freq);
    setMsg(r.sent > 0 ? `Resumen ${freq === "daily" ? "diario" : "semanal"} enviado a ${r.sent} regla(s).` : `No hay reglas programadas (${freq}). Crea una con cadencia de resumen.`);
  }
  async function saveThreshold() {
    const r = await api.setAlertThreshold(threshold);
    setThreshold(r.spend_threshold_usd);
    setMsg(r.spend_threshold_usd > 0 ? `Umbral de gasto: $${r.spend_threshold_usd}/día.` : "Umbral de gasto desactivado.");
  }

  const needWebhook = form.channels.includes("webhook");
  const needWa = form.channels.includes("whatsapp");
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
          <label className="text-xs font-semibold uppercase tracking-wide text-slate-500">Cadencia</label>
          <select value={form.schedule} onChange={(e) => setForm({ ...form, schedule: e.target.value })}
            className="mb-3 mt-1 w-full rounded-lg border border-slate-300 px-3 py-2 text-sm">
            {SCHEDULES.map((s) => <option key={s.id} value={s.id}>{s.label}</option>)}
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
              placeholder="URL del webhook (Slack/Teams/Zapier)" className="mb-2 w-full rounded-lg border border-slate-300 px-3 py-2 text-sm" />
          )}
          {needWa && (
            <p className="mb-2 rounded-lg border border-emerald-200 bg-emerald-50 px-3 py-2 text-xs text-emerald-700">
              WhatsApp se entrega por CallMeBot. Configúralo abajo en «WhatsApp (CallMeBot)».
            </p>
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
                  <span className="block truncate text-xs text-slate-400">{r.event_type} · {r.channels.join(", ")}{r.schedule ? ` · ${r.schedule === "daily" ? "resumen diario" : "resumen semanal"}` : ""}</span>
                </span>
                <button onClick={() => remove(r.id)} title="Eliminar" className="shrink-0 rounded-md border border-slate-300 p-1 text-red-500"><Trash2 className="h-3.5 w-3.5" /></button>
              </div>
            ))}
          </div>
          <p className="mt-4 text-xs text-slate-400">
            WhatsApp se entrega por CallMeBot (configúralo abajo). Telegram es directo con el bot.
            Webhook sirve para Slack/Teams/Zapier.
          </p>

          {/* Resúmenes programados + umbral de gasto */}
          <div className="mt-5 border-t border-slate-100 pt-4">
            <h3 className="mb-2 text-sm font-semibold text-slate-700">Resúmenes programados</h3>
            <p className="mb-2 text-xs text-slate-400">
              Las reglas con cadencia «resumen» juntan la actividad del periodo en un solo aviso.
              Se envían automáticamente desde un cron; aquí puedes dispararlos manualmente.
            </p>
            <div className="flex gap-2">
              <button onClick={() => runDigest("daily")} className="rounded-lg border border-slate-300 px-3 py-1.5 text-xs font-semibold text-slate-600">Enviar resumen diario</button>
              <button onClick={() => runDigest("weekly")} className="rounded-lg border border-slate-300 px-3 py-1.5 text-xs font-semibold text-slate-600">Enviar resumen semanal</button>
            </div>
          </div>
          <div className="mt-5 border-t border-slate-100 pt-4">
            <h3 className="mb-2 text-sm font-semibold text-slate-700">Umbral de gasto (alerta automática)</h3>
            <p className="mb-2 text-xs text-slate-400">
              Si el gasto de tokens del día supera este monto (USD), se dispara una alerta del evento
              «Umbral de gasto». 0 = desactivado. Crea una regla con ese evento para recibirla.
            </p>
            <div className="flex items-center gap-2">
              <span className="text-sm text-slate-500">$</span>
              <input type="number" min={0} step="0.01" value={threshold}
                onChange={(e) => setThreshold(parseFloat(e.target.value) || 0)}
                className="w-28 rounded-lg border border-slate-300 px-3 py-1.5 text-sm" />
              <span className="text-xs text-slate-400">/ día</span>
              <button onClick={saveThreshold} className="rounded-lg bg-slate-900 px-3 py-1.5 text-xs font-semibold text-white">Guardar</button>
            </div>
          </div>

          {/* WhatsApp (CallMeBot) */}
          <div className="mt-5 border-t border-slate-100 pt-4">
            <h3 className="mb-1 text-sm font-semibold text-slate-700">WhatsApp (CallMeBot) {wa.configured && <span className="text-xs font-normal text-emerald-600">· conectado</span>}</h3>
            <p className="mb-2 text-xs text-slate-400">
              Activa el canal WhatsApp y el botón «Enviar a WhatsApp» de los casos. Registra tu
              número con el bot de CallMeBot (envíale «I allow callmebot to send me messages» al
              +34&nbsp;644&nbsp;51&nbsp;95&nbsp;23) y pega aquí tu número y la apikey que te dé.
            </p>
            <div className="grid grid-cols-1 gap-2 sm:grid-cols-2">
              <input value={wa.phone} onChange={(e) => setWa({ ...wa, phone: e.target.value })}
                placeholder="Número (+5215512345678)" className="rounded-lg border border-slate-300 px-3 py-1.5 text-sm" />
              <input value={wa.apikey} onChange={(e) => setWa({ ...wa, apikey: e.target.value })}
                placeholder={wa.configured ? "apikey (guardada — deja vacío para conservar)" : "apikey de CallMeBot"}
                className="rounded-lg border border-slate-300 px-3 py-1.5 text-sm" />
            </div>
            <div className="mt-2 flex gap-2">
              <button onClick={saveWa} className="rounded-lg bg-slate-900 px-3 py-1.5 text-xs font-semibold text-white">Guardar</button>
              <button onClick={testWa} className="rounded-lg border border-slate-300 px-3 py-1.5 text-xs font-semibold text-slate-600">Probar</button>
            </div>
            {waMsg && <div className="mt-2 rounded-lg border border-slate-200 bg-slate-50 px-3 py-2 text-xs text-slate-600">{waMsg}</div>}
          </div>
        </div>
      </div>
    </Shell>
  );
}
