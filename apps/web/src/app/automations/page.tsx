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
  const [valid, setValid] = useState<Record<string, Awaited<ReturnType<typeof api.validateAutomation>>>>({});
  const [deliver, setDeliver] = useState<Record<string, string[]>>({});
  const [emailTo, setEmailTo] = useState<Record<string, string>>({});
  const [source, setSource] = useState<Record<string, { kind: string; ref: string; label: string }>>({});
  const [datasources, setDatasources] = useState<{ id: string; name: string }[]>([]);
  const [driveFolders, setDriveFolders] = useState<{ id: string; name: string }[]>([]);

  function load() {
    api.automations().then(setList).catch(() => {});
  }
  useEffect(() => {
    api.automationTemplates().then(setTemplates).catch(() => {});
    load();
    api.workflows().then((w) => setWorkflows(w.map((x) => ({ id: x.id, name: x.name })))).catch(() => {});
    api.recipes().then((r) => setRecipes(r.map((x) => ({ id: x.id, name: x.name })))).catch(() => {});
    api.connectors().then((c) => setConnectors(c.map((x) => ({ id: x.id, name: x.name })))).catch(() => {});
    api.dataSources().then((d) => setDatasources(d.map((x) => ({ id: x.id, name: x.name })))).catch(() => {});
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
  async function doValidate(a: Automation) {
    setMsg("");
    // Pre-carga los controles de entrada/salida con lo que ya tiene guardado.
    const cfg = (a.config || {}) as { deliver?: string[]; email_to?: string; source?: { kind: string; ref: string; label: string } };
    setDeliver((d) => ({ ...d, [a.id]: cfg.deliver || ["notify"] }));
    setEmailTo((e) => ({ ...e, [a.id]: cfg.email_to || "" }));
    setSource((s) => ({ ...s, [a.id]: cfg.source || { kind: "new_documents", ref: "", label: "" } }));
    try { const r = await api.validateAutomation(a.id); setValid((v) => ({ ...v, [a.id]: r })); }
    catch (e) { setMsg(e instanceof Error ? e.message : "No se pudo validar"); }
  }
  async function doSchedule(a: Automation, frequency: string) {
    setMsg("");
    try { await api.scheduleAutomation(a.id, frequency); setMsg(`✓ «${a.name}» programada · ${frequency}`); load(); }
    catch (e) { setMsg(e instanceof Error ? e.message : "No se pudo programar"); }
  }
  function toggleChannel(aid: string, ch: string) {
    setDeliver((d) => {
      const cur = d[aid] || ["notify"];
      return { ...d, [aid]: cur.includes(ch) ? cur.filter((c) => c !== ch) : [...cur, ch] };
    });
  }
  async function saveDelivery(a: Automation) {
    setMsg("");
    try {
      await api.setAutomationDelivery(a.id, deliver[a.id] || ["notify"], emailTo[a.id] || "");
      setMsg(`✓ Salida guardada para «${a.name}»`);
      load(); doValidate(a);
    } catch (e) { setMsg(e instanceof Error ? e.message : "No se pudo guardar la salida"); }
  }
  async function loadDriveFolders() {
    try { const r = await api.driveFiles(); setDriveFolders(r.files.filter((f) => f.is_folder).map((f) => ({ id: f.id, name: f.name }))); }
    catch { setDriveFolders([]); }
  }
  function setSrc(aid: string, patch: Partial<{ kind: string; ref: string; label: string }>) {
    setSource((s) => ({ ...s, [aid]: { ...(s[aid] || { kind: "new_documents", ref: "", label: "" }), ...patch } }));
  }
  async function saveSource(a: Automation) {
    setMsg("");
    try {
      const s = source[a.id] || { kind: "new_documents", ref: "", label: "" };
      await api.setAutomationSource(a.id, s);
      setMsg(`✓ Entrada guardada para «${a.name}»`);
      load(); doValidate(a);
    } catch (e) { setMsg(e instanceof Error ? e.message : "No se pudo guardar la entrada"); }
  }

  return (
    <Shell>
      <PageHeader title="Automatizaciones" subtitle="Conecta disparadores con acciones: resúmenes, cobranza, alertas, reportes…" help="n8n" />
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
                <div key={a.id} className="rounded-xl border border-slate-200 bg-white p-4">
                  <div className="flex items-center justify-between">
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
                      <button onClick={() => doValidate(a)} className="rounded-lg border border-slate-300 px-3 py-1.5 text-xs font-semibold text-slate-600 hover:bg-slate-50">
                        Validar
                      </button>
                      <button onClick={() => run(a)} className="inline-flex items-center gap-1 rounded-lg bg-violet-600 px-3 py-1.5 text-xs font-semibold text-white">
                        <Play className="h-3.5 w-3.5" /> Ejecutar
                      </button>
                      <button onClick={() => remove(a)} className="text-slate-400 hover:text-red-600">
                        <Trash2 className="h-4 w-4" />
                      </button>
                    </div>
                  </div>
                  {valid[a.id] && (
                    <div className="mt-3 rounded-lg border border-slate-100 bg-slate-50 p-3">
                      <div className="mb-2 text-xs font-semibold text-slate-500">
                        {valid[a.id].ready ? "✓ Todo listo para ejecutar" : "Faltan requisitos:"}
                      </div>
                      <ol className="space-y-1">
                        {valid[a.id].steps.map((s, i) => {
                          const ok = s.status === "ok";
                          const opt = !ok && s.optional;
                          return (
                            <li key={i} className="flex items-center gap-2 text-xs text-slate-600">
                              <span className={ok ? "text-emerald-600" : opt ? "text-amber-500" : "text-red-600"}>{ok ? "✓" : opt ? "○" : "✗"}</span>
                              <b>{s.label}:</b> {s.detail}
                              {!ok && s.link && <a href={s.link} className="text-violet-600 underline">configurar</a>}
                            </li>
                          );
                        })}
                      </ol>

                      {/* Entrada: qué procesar (solo workflows / n8n) */}
                      {a.action_type === "workflow" && (
                        <div className="mt-3 border-t border-slate-200 pt-2">
                          <div className="mb-1.5 text-xs font-semibold text-slate-500">Entrada · qué procesar</div>
                          <div className="flex flex-wrap items-center gap-2">
                            <select value={source[a.id]?.kind || "new_documents"}
                              onChange={(e) => { setSrc(a.id, { kind: e.target.value, ref: "", label: "" }); if (e.target.value === "drive_folder") loadDriveFolders(); }}
                              className="rounded-md border border-slate-300 px-2 py-1 text-xs">
                              <option value="new_documents">Documentos nuevos (desde última corrida)</option>
                              <option value="drive_folder">Carpeta de Drive</option>
                              <option value="datasource">Fuente de datos (legado)</option>
                              <option value="manual">Sin entrada (lo arma el flujo)</option>
                            </select>
                            {source[a.id]?.kind === "datasource" && (
                              <select value={source[a.id]?.ref || ""}
                                onChange={(e) => { const o = datasources.find((d) => d.id === e.target.value); setSrc(a.id, { ref: e.target.value, label: o?.name || "" }); }}
                                className="rounded-md border border-slate-300 px-2 py-1 text-xs">
                                <option value="">Selecciona fuente…</option>
                                {datasources.map((d) => <option key={d.id} value={d.id}>{d.name}</option>)}
                              </select>
                            )}
                            {source[a.id]?.kind === "drive_folder" && (
                              <select value={source[a.id]?.ref || ""}
                                onChange={(e) => { const o = driveFolders.find((d) => d.id === e.target.value); setSrc(a.id, { ref: e.target.value, label: o?.name || "" }); }}
                                className="rounded-md border border-slate-300 px-2 py-1 text-xs">
                                <option value="">{driveFolders.length ? "Selecciona carpeta…" : "Conecta Drive en Documentos"}</option>
                                {driveFolders.map((d) => <option key={d.id} value={d.id}>{d.name}</option>)}
                              </select>
                            )}
                            <button onClick={() => saveSource(a)} className="rounded-md bg-slate-900 px-2.5 py-1 text-xs font-semibold text-white">Guardar entrada</button>
                          </div>
                        </div>
                      )}

                      {/* Salida: a dónde mandar el resultado */}
                      <div className="mt-3 border-t border-slate-200 pt-2">
                        <div className="mb-1.5 text-xs font-semibold text-slate-500">Salida · a dónde mandar el resultado</div>
                        <div className="flex flex-wrap items-center gap-3">
                          {([["notify", "Notificación"], ["whatsapp", "WhatsApp"], ["email", "Correo"]] as const).map(([ch, lbl]) => (
                            <label key={ch} className="flex items-center gap-1 text-xs text-slate-600">
                              <input type="checkbox" checked={(deliver[a.id] || ["notify"]).includes(ch)} onChange={() => toggleChannel(a.id, ch)} />
                              {lbl}
                            </label>
                          ))}
                          {(deliver[a.id] || []).includes("email") && (
                            <input value={emailTo[a.id] || ""} onChange={(e) => setEmailTo((v) => ({ ...v, [a.id]: e.target.value }))}
                              placeholder="correo destino (opcional)" className="rounded-md border border-slate-300 px-2 py-1 text-xs" />
                          )}
                          <button onClick={() => saveDelivery(a)} className="rounded-md bg-slate-900 px-2.5 py-1 text-xs font-semibold text-white">Guardar salida</button>
                        </div>
                      </div>

                      <div className="mt-3 flex items-center gap-2 border-t border-slate-200 pt-2">
                        <span className="text-xs text-slate-500">Programar:</span>
                        {["daily", "weekly", "monthly"].map((f) => (
                          <button key={f} onClick={() => doSchedule(a, f)}
                            className="rounded-md border border-slate-300 px-2 py-1 text-xs hover:bg-white">
                            {f === "daily" ? "Diario" : f === "weekly" ? "Semanal" : "Mensual"}
                          </button>
                        ))}
                      </div>
                    </div>
                  )}
                </div>
              ))}
            </div>
          )}
        </div>
      </div>
    </Shell>
  );
}
