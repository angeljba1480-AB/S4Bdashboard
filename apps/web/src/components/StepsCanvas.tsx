"use client";

import { api } from "@/lib/api";
import { ArrowLeft, ArrowRight, Bot, Database, Mail, Plus, Save, Send, Trash2, Webhook, Workflow, X } from "lucide-react";
import { useEffect, useState } from "react";

type Step = Record<string, unknown> & { type: string; label?: string; id?: string };
type Opt = { id: string; name: string };
type Lists = { workflows: Opt[]; recipes: Opt[]; connectors: Opt[]; datasources: Opt[] };

const STEP_META: Record<string, { label: string; icon: React.ElementType; color: string }> = {
  fetch: { label: "Entrada", icon: Database, color: "text-sky-600" },
  workflow: { label: "Workflow (n8n)", icon: Webhook, color: "text-violet-600" },
  recipe: { label: "Caso de uso", icon: Workflow, color: "text-amber-600" },
  ai: { label: "IA (transformar)", icon: Bot, color: "text-emerald-600" },
  connector: { label: "Conector", icon: Send, color: "text-rose-600" },
  notify: { label: "Nota", icon: Mail, color: "text-slate-600" },
  deliver: { label: "Salida", icon: Send, color: "text-violet-600" },
};

function summary(s: Step): string {
  switch (s.type) {
    case "fetch": return String(s.label || s.kind || "documentos nuevos");
    case "workflow": return String(s.ref || "—");
    case "recipe": return String(s.ref || "—");
    case "ai": return String(s.prompt || "transformar con IA").slice(0, 40);
    case "connector": return String(s.ref || "—");
    case "notify": return String(s.message || "—").slice(0, 40);
    case "deliver": return ((s.channels as string[]) || ["notify"]).join(", ");
    default: return "";
  }
}

export function StepsCanvas({ automationId, lists, onClose }: {
  automationId: string;
  lists: Lists;
  onClose: () => void;
}) {
  const [steps, setSteps] = useState<Step[]>([]);
  const [editIdx, setEditIdx] = useState<number | null>(null);
  const [adding, setAdding] = useState(false);
  const [msg, setMsg] = useState("");
  const [dragIdx, setDragIdx] = useState<number | null>(null);

  useEffect(() => {
    api.automationSteps(automationId).then((r) => setSteps((r.steps as Step[]) || [])).catch(() => {});
  }, [automationId]);

  const def = (type: string): Step => {
    switch (type) {
      case "fetch": return { type, kind: "new_documents", label: "Documentos nuevos" };
      case "deliver": return { type, channels: ["notify"] };
      case "ai": return { type, prompt: "Resume y mejora el contenido en español." };
      case "notify": return { type, message: "" };
      default: return { type, ref: "" };
    }
  };
  function addStep(type: string) { setSteps((s) => [...s, def(type)]); setAdding(false); setEditIdx(steps.length); }
  function update(i: number, patch: Partial<Step>) { setSteps((s) => s.map((x, j) => (j === i ? { ...x, ...patch } : x))); }
  function move(i: number, dir: -1 | 1) {
    setSteps((s) => { const n = [...s]; const j = i + dir; if (j < 0 || j >= n.length) return n; [n[i], n[j]] = [n[j], n[i]]; return n; });
    setEditIdx(null);
  }
  function remove(i: number) { setSteps((s) => s.filter((_, j) => j !== i)); setEditIdx(null); }
  function drop(target: number) {
    if (dragIdx === null || dragIdx === target) { setDragIdx(null); return; }
    setSteps((s) => { const n = [...s]; const [m] = n.splice(dragIdx, 1); n.splice(target, 0, m); return n; });
    setDragIdx(null); setEditIdx(null);
  }
  async function save() {
    setMsg("");
    try { await api.setAutomationSteps(automationId, steps); setMsg("✓ Pipeline guardado"); }
    catch (e) { setMsg(e instanceof Error ? e.message : "No se pudo guardar"); }
  }

  return (
    <div className="rounded-xl border border-violet-200 bg-white p-4">
      <div className="mb-3 flex items-center justify-between">
        <span className="text-xs font-semibold uppercase tracking-wide text-slate-500">Constructor de pasos (pipeline) <span className="font-normal normal-case text-slate-300">· arrastra o usa ←→ para reordenar</span></span>
        <button onClick={onClose} className="text-slate-400 hover:text-slate-600"><X className="h-4 w-4" /></button>
      </div>

      {steps.length === 0 && <p className="mb-3 text-xs text-slate-400">Aún no hay pasos. Agrega el primero abajo.</p>}

      <div className="flex items-stretch gap-1 overflow-x-auto pb-2">
        {steps.map((s, i) => {
          const meta = STEP_META[s.type] || STEP_META.notify;
          const Icon = meta.icon;
          const active = editIdx === i;
          return (
            <div key={s.id || i} className="flex items-stretch gap-1"
              onDragOver={(e) => e.preventDefault()} onDrop={() => drop(i)}>
              <div
                draggable
                onDragStart={() => setDragIdx(i)}
                onDragEnd={() => setDragIdx(null)}
                title="Arrastra para reordenar"
                className={`flex w-44 shrink-0 cursor-move flex-col rounded-xl border-2 bg-white p-3 shadow-sm transition ${active ? "border-violet-500 ring-2 ring-violet-200" : "border-slate-200"} ${dragIdx === i ? "opacity-40" : ""}`}>
                <div className="mb-1 flex items-center gap-2">
                  <Icon className={`h-4 w-4 ${meta.color}`} />
                  <span className="text-[10px] font-semibold uppercase text-slate-400">paso {i + 1}</span>
                  <div className="ml-auto flex items-center gap-0.5">
                    <button onClick={() => move(i, -1)} disabled={i === 0} title="Mover izquierda" className="text-slate-300 hover:text-slate-600 disabled:opacity-30"><ArrowLeft className="h-3.5 w-3.5" /></button>
                    <button onClick={() => move(i, 1)} disabled={i === steps.length - 1} title="Mover derecha" className="text-slate-300 hover:text-slate-600 disabled:opacity-30"><ArrowRight className="h-3.5 w-3.5" /></button>
                    <button onClick={() => remove(i)} title="Eliminar" className="text-slate-300 hover:text-red-500"><Trash2 className="h-3.5 w-3.5" /></button>
                  </div>
                </div>
                <div className="text-xs font-semibold text-slate-700">{meta.label}</div>
                <div className="mt-0.5 line-clamp-2 text-[11px] text-slate-400">{summary(s)}</div>
                <button onClick={() => setEditIdx(active ? null : i)} className="mt-1 self-start text-[11px] font-semibold text-violet-600">{active ? "cerrar" : "✎ editar"}</button>
              </div>
              {i < steps.length - 1 && (
                <div className="flex items-center px-0.5 text-slate-300" aria-hidden>
                  <svg width="18" height="12" viewBox="0 0 18 12" fill="none"><path d="M0 6h14M14 6l-4-4M14 6l-4 4" stroke="currentColor" strokeWidth="1.5" strokeLinecap="round" strokeLinejoin="round" /></svg>
                </div>
              )}
            </div>
          );
        })}
      </div>

      {/* Editor del paso seleccionado */}
      {editIdx !== null && steps[editIdx] && (
        <div className="mt-3 rounded-lg border border-slate-200 bg-slate-50 p-3">
          <StepEditor step={steps[editIdx]} lists={lists} onChange={(p) => update(editIdx, p)} />
        </div>
      )}

      {/* Agregar paso */}
      <div className="mt-3 flex flex-wrap items-center gap-2 border-t border-slate-200 pt-3">
        {adding ? (
          <>
            <span className="text-xs text-slate-500">Tipo:</span>
            {Object.entries(STEP_META).map(([type, m]) => (
              <button key={type} onClick={() => addStep(type)} className="rounded-md border border-slate-300 px-2 py-1 text-xs hover:bg-white">{m.label}</button>
            ))}
            <button onClick={() => setAdding(false)} className="text-xs text-slate-400">cancelar</button>
          </>
        ) : (
          <button onClick={() => setAdding(true)} className="inline-flex items-center gap-1 rounded-md border border-dashed border-slate-300 px-3 py-1.5 text-xs font-semibold text-slate-600 hover:bg-slate-50">
            <Plus className="h-3.5 w-3.5" /> Agregar paso
          </button>
        )}
        <button onClick={save} className="ml-auto inline-flex items-center gap-1 rounded-md bg-violet-600 px-3 py-1.5 text-xs font-semibold text-white">
          <Save className="h-3.5 w-3.5" /> Guardar pipeline
        </button>
      </div>
      {msg && <div className="mt-2 text-xs text-slate-500">{msg}</div>}
    </div>
  );
}

function StepEditor({ step, lists, onChange }: { step: Step; lists: Lists; onChange: (p: Partial<Step>) => void }) {
  const inputCls = "rounded-md border border-slate-300 px-2 py-1 text-xs";
  const channels = (step.channels as string[]) || ["notify"];
  const toggleCh = (ch: string) => onChange({ channels: channels.includes(ch) ? channels.filter((c) => c !== ch) : [...channels, ch] });

  if (step.type === "fetch") return (
    <div className="flex flex-wrap items-center gap-2">
      <select value={String(step.kind || "new_documents")} onChange={(e) => onChange({ kind: e.target.value, ref: "", label: e.target.selectedOptions[0].text })} className={inputCls}>
        <option value="new_documents">Documentos nuevos</option>
        <option value="drive_folder">Carpeta de Drive</option>
        <option value="datasource">Fuente de datos</option>
        <option value="manual">Sin entrada</option>
      </select>
      {step.kind === "datasource" && (
        <select value={String(step.ref || "")} onChange={(e) => onChange({ ref: e.target.value, label: e.target.selectedOptions[0].text })} className={inputCls}>
          <option value="">Selecciona…</option>{lists.datasources.map((d) => <option key={d.id} value={d.id}>{d.name}</option>)}
        </select>
      )}
    </div>
  );
  if (step.type === "workflow") return (
    <select value={String(step.ref || "")} onChange={(e) => onChange({ ref: e.target.value, label: e.target.selectedOptions[0].text })} className={inputCls}>
      <option value="">Selecciona workflow…</option>{lists.workflows.map((w) => <option key={w.id} value={w.id}>{w.name}</option>)}
    </select>
  );
  if (step.type === "recipe") return (
    <select value={String(step.ref || "")} onChange={(e) => onChange({ ref: e.target.value, label: e.target.selectedOptions[0].text })} className={inputCls}>
      <option value="">Selecciona caso…</option>{lists.recipes.map((r) => <option key={r.id} value={r.id}>{r.name}</option>)}
    </select>
  );
  if (step.type === "connector") return (
    <select value={String(step.ref || "")} onChange={(e) => onChange({ ref: e.target.value, label: e.target.selectedOptions[0].text })} className={inputCls}>
      <option value="">Selecciona conector…</option>{lists.connectors.map((c) => <option key={c.id} value={c.id}>{c.name}</option>)}
    </select>
  );
  if (step.type === "ai") return (
    <textarea value={String(step.prompt || "")} onChange={(e) => onChange({ prompt: e.target.value })} rows={2} className={`w-full ${inputCls}`} placeholder="Instrucción para la IA (transforma el contenido del paso anterior)" />
  );
  if (step.type === "notify") return (
    <input value={String(step.message || "")} onChange={(e) => onChange({ message: e.target.value })} className={`w-full ${inputCls}`} placeholder="Texto / contenido base" />
  );
  if (step.type === "deliver") return (
    <div className="flex flex-wrap items-center gap-3">
      {([["notify", "Notificación"], ["whatsapp", "WhatsApp"], ["email", "Correo"]] as const).map(([ch, lbl]) => (
        <label key={ch} className="flex items-center gap-1 text-xs text-slate-600"><input type="checkbox" checked={channels.includes(ch)} onChange={() => toggleCh(ch)} />{lbl}</label>
      ))}
      {channels.includes("email") && (
        <input value={String(step.email_to || "")} onChange={(e) => onChange({ email_to: e.target.value })} placeholder="correo destino (opcional)" className={inputCls} />
      )}
    </div>
  );
  return null;
}
