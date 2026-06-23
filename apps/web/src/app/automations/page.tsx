"use client";

import { PageHeader, Shell } from "@/components/Shell";
import { api } from "@/lib/api";
import { Clock, Play, Plus, Trash2, Zap } from "lucide-react";
import { useEffect, useState } from "react";

type Template = Awaited<ReturnType<typeof api.automationTemplates>>[number];
type Automation = Awaited<ReturnType<typeof api.automations>>[number];

const TRIGGER_LABEL: Record<string, string> = { manual: "Manual", schedule: "Programada", event: "Por evento" };

export default function AutomationsPage() {
  const [templates, setTemplates] = useState<Template[]>([]);
  const [list, setList] = useState<Automation[]>([]);
  const [msg, setMsg] = useState("");
  const [workflows, setWorkflows] = useState<{ id: string; name: string }[]>([]);
  const [recipes, setRecipes] = useState<{ id: string; name: string }[]>([]);
  const [connectors, setConnectors] = useState<{ id: string; name: string }[]>([]);
  const [custom, setCustom] = useState({ name: "", trigger: "manual", schedule: "daily", event: "document_uploaded", action_type: "workflow", action_ref: "", message: "" });

  function load() {
    api.automations().then(setList).catch(() => {});
  }
  useEffect(() => {
    api.automationTemplates().then(setTemplates).catch(() => {});
    load();
    api.workflows().then((w) => setWorkflows(w.map((x) => ({ id: x.id, name: x.name })))).catch(() => {});
    api.recipes().then((r) => setRecipes(r.map((x) => ({ id: x.id, name: x.name })))).catch(() => {});
    api.connectors().then((c) => setConnectors(c.map((x) => ({ id: x.id, name: x.name })))).catch(() => {});
  }, []);

  const refOptions = custom.action_type === "workflow" ? workflows
    : custom.action_type === "recipe" ? recipes
    : custom.action_type === "connector" ? connectors : [];

  async function createCustom(e: React.FormEvent) {
    e.preventDefault();
    if (!custom.name.trim()) return;
    await api.createAutomation({
      name: custom.name, trigger: custom.trigger,
      schedule: custom.trigger === "schedule" ? custom.schedule : "",
      event: custom.trigger === "event" ? custom.event : "",
      action_type: custom.action_type, action_ref: custom.action_ref,
      config: custom.action_type === "notify" ? { message: custom.message } : {},
    });
    setCustom({ ...custom, name: "", action_ref: "", message: "" });
    setMsg("✓ Automatización creada");
    load();
  }

  async function add(t: Template) {
    await api.createAutomationFromTemplate(t.id);
    load();
  }
  async function run(a: Automation) {
    setMsg(`Ejecutando «${a.name}»…`);
    const r = await api.runAutomation(a.id);
    setMsg(`«${a.name}»: ${r.status} · ${r.detail}`);
    load();
  }
  async function toggle(a: Automation) {
    await api.toggleAutomation(a.id);
    load();
  }
  async function remove(a: Automation) {
    await api.deleteAutomation(a.id);
    load();
  }

  return (
    <Shell>
      <PageHeader title="Automatizaciones" subtitle="Conecta disparadores con acciones: resúmenes, cobranza, alertas, reportes…" />
      <div className="space-y-6 p-8">
        {msg && <div className="rounded-lg bg-slate-100 px-4 py-2 text-sm text-slate-600">{msg}</div>}

        {/* Template gallery */}
        <div>
          <h2 className="mb-3 font-semibold text-slate-800">Plantillas</h2>
          <div className="grid gap-4 sm:grid-cols-2 lg:grid-cols-3">
            {templates.map((t) => (
              <div key={t.id} className="flex flex-col rounded-2xl border border-slate-200 bg-white p-5">
                <div className="mb-2 flex h-9 w-9 items-center justify-center rounded-lg bg-violet-50">
                  <Zap className="h-5 w-5 text-violet-600" />
                </div>
                <div className="font-semibold text-slate-800">{t.name}</div>
                <p className="mt-1 flex-1 text-sm text-slate-500">{t.description}</p>
                <div className="mt-2 flex items-center gap-2 text-xs text-slate-400">
                  <Clock className="h-3.5 w-3.5" /> {TRIGGER_LABEL[t.trigger]}{t.schedule ? ` · ${t.schedule}` : ""}{t.event ? ` · ${t.event}` : ""}
                </div>
                <button onClick={() => add(t)}
                  className="mt-3 inline-flex items-center gap-1.5 self-start rounded-lg bg-slate-900 px-3 py-1.5 text-xs font-semibold text-white">
                  <Plus className="h-3.5 w-3.5" /> Activar
                </button>
              </div>
            ))}
          </div>
        </div>

        {/* Custom builder */}
        <details className="rounded-2xl border border-slate-200 bg-white p-5">
          <summary className="cursor-pointer font-semibold text-slate-800">Crear a la medida</summary>
          <form onSubmit={createCustom} className="mt-4 grid grid-cols-1 gap-3 sm:grid-cols-2">
            <input value={custom.name} onChange={(e) => setCustom({ ...custom, name: e.target.value })}
              placeholder="Nombre de la automatización" className="rounded-lg border border-slate-300 px-3 py-2 text-sm sm:col-span-2" />
            <select value={custom.trigger} onChange={(e) => setCustom({ ...custom, trigger: e.target.value })}
              className="rounded-lg border border-slate-300 px-3 py-2 text-sm">
              <option value="manual">Disparador: Manual</option>
              <option value="schedule">Disparador: Programada</option>
              <option value="event">Disparador: Por evento</option>
            </select>
            {custom.trigger === "schedule" && (
              <select value={custom.schedule} onChange={(e) => setCustom({ ...custom, schedule: e.target.value })}
                className="rounded-lg border border-slate-300 px-3 py-2 text-sm">
                <option value="daily">Diaria</option><option value="weekly">Semanal</option><option value="monthly">Mensual</option>
              </select>
            )}
            {custom.trigger === "event" && (
              <select value={custom.event} onChange={(e) => setCustom({ ...custom, event: e.target.value })}
                className="rounded-lg border border-slate-300 px-3 py-2 text-sm">
                <option value="document_uploaded">Al subir un documento</option>
              </select>
            )}
            <select value={custom.action_type} onChange={(e) => setCustom({ ...custom, action_type: e.target.value, action_ref: "" })}
              className="rounded-lg border border-slate-300 px-3 py-2 text-sm">
              <option value="workflow">Acción: Workflow (n8n)</option>
              <option value="recipe">Acción: Caso de uso</option>
              <option value="connector">Acción: Conector (CRM/ERP/delivery)</option>
              <option value="notify">Acción: Notificar</option>
            </select>
            {custom.action_type !== "notify" ? (
              <select value={custom.action_ref} onChange={(e) => setCustom({ ...custom, action_ref: e.target.value })}
                className="rounded-lg border border-slate-300 px-3 py-2 text-sm">
                <option value="">Selecciona…</option>
                {refOptions.map((o) => <option key={o.id} value={o.id}>{o.name}</option>)}
              </select>
            ) : (
              <input value={custom.message} onChange={(e) => setCustom({ ...custom, message: e.target.value })}
                placeholder="Mensaje de la notificación" className="rounded-lg border border-slate-300 px-3 py-2 text-sm" />
            )}
            <button className="rounded-lg bg-violet-600 px-4 py-2 text-sm font-semibold text-white sm:col-span-2">Crear automatización</button>
          </form>
        </details>

        {/* My automations */}
        <div>
          <h2 className="mb-3 font-semibold text-slate-800">Mis automatizaciones</h2>
          {list.length === 0 ? (
            <p className="text-sm text-slate-400">Activa una plantilla para empezar.</p>
          ) : (
            <div className="space-y-2">
              {list.map((a) => (
                <div key={a.id} className="flex items-center justify-between rounded-xl border border-slate-200 bg-white p-4">
                  <div>
                    <div className="font-medium text-slate-800">{a.name}</div>
                    <div className="text-xs text-slate-400">
                      {TRIGGER_LABEL[a.trigger]}{a.schedule ? ` · ${a.schedule}` : ""}{a.event ? ` · ${a.event}` : ""} ·
                      acción: {a.action_type} {a.action_ref && `(${a.action_ref})`}
                      {a.last_run && ` · última: ${a.status}`}
                    </div>
                  </div>
                  <div className="flex items-center gap-2">
                    <button onClick={() => toggle(a)}
                      className={`rounded-full px-2 py-0.5 text-xs ${a.enabled ? "bg-emerald-100 text-emerald-700" : "bg-slate-100 text-slate-500"}`}>
                      {a.enabled ? "Activa" : "Pausada"}
                    </button>
                    <button onClick={() => run(a)} className="inline-flex items-center gap-1 rounded-lg bg-violet-600 px-3 py-1.5 text-xs font-semibold text-white">
                      <Play className="h-3.5 w-3.5" /> Ejecutar
                    </button>
                    <button onClick={() => remove(a)} className="text-slate-400 hover:text-red-600">
                      <Trash2 className="h-4 w-4" />
                    </button>
                  </div>
                </div>
              ))}
            </div>
          )}
        </div>
      </div>
    </Shell>
  );
}
