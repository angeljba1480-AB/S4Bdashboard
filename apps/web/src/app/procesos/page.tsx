"use client";

import { PageHeader, Shell } from "@/components/Shell";
import { api } from "@/lib/api";
import type { LineNode, ProcessStepNode, ProcessTree, RoiSummary, ServiceNode, StepLinkDto, StepMetrics } from "@shared/types";
import { Building2, Gauge, LayoutGrid, Link2, List, Plus, Trash2, TrendingUp, Wand2, Workflow, X } from "lucide-react";
import { useCallback, useEffect, useState } from "react";
import { ProcessCanvas } from "./ProcessCanvas";

type StepStateT = "manual" | "candidate" | "automated";
const STATE_LABEL: Record<StepStateT, string> = { manual: "Manual", candidate: "Candidato", automated: "Automatizado" };
const STATE_CLS: Record<StepStateT, string> = {
  manual: "bg-slate-100 text-slate-600", candidate: "bg-amber-100 text-amber-700", automated: "bg-emerald-100 text-emerald-700",
};
const mxn = (n: number) => "$" + (n || 0).toLocaleString("es-MX", { maximumFractionDigits: 0 });

export default function ProcesosPage() {
  const [tree, setTree] = useState<ProcessTree | null>(null);
  const [roi, setRoi] = useState<RoiSummary | null>(null);
  const [active, setActive] = useState<ProcessStepNode | null>(null);
  const [view, setView] = useState<"list" | "canvas">("list");
  const [welcome, setWelcome] = useState(false);
  const [err, setErr] = useState("");

  // Llegada desde el onboarding recién completado: abrir el lienzo y dar la bienvenida.
  useEffect(() => {
    if (typeof window !== "undefined" && new URLSearchParams(window.location.search).get("onboarding") === "1") {
      setWelcome(true);
      setView("canvas");
    }
  }, []);

  const load = useCallback(() => {
    api.processTree().then(setTree).catch((e) => setErr(e instanceof Error ? e.message : "Error"));
    api.roi().then(setRoi).catch(() => {});
  }, []);
  useEffect(() => { load(); }, [load]);

  async function run(fn: () => Promise<unknown>) {
    setErr("");
    try { await fn(); load(); } catch (e) { setErr(e instanceof Error ? e.message : "Error"); }
  }

  const addLine = () => { const n = window.prompt("Línea de negocio (ej. SOC):"); if (n?.trim()) run(() => api.createLine({ name: n.trim() })); };
  const addService = (line: LineNode) => {
    const n = window.prompt(`Servicio de «${line.name}»:`); if (!n?.trim()) return;
    const ext = window.confirm("¿Servicio EXTERNO (SLA, cliente paga)?\nAceptar = externo · Cancelar = interno (OLA).");
    const sla = window.prompt(ext ? "SLA (ej. 99.9%):" : "OLA (ej. 4h):") || "";
    run(() => api.createService({ line_id: line.id, name: n.trim(), kind: ext ? "external" : "internal", sla_ola: sla }));
  };
  const addClient = (s: ServiceNode) => { const n = window.prompt(`Cliente de «${s.name}»:`); if (n?.trim()) run(() => api.addServiceClient(s.id, n.trim())); };
  const addProcess = (s: ServiceNode) => { const n = window.prompt(`Proceso de «${s.name}»:`); if (n?.trim()) run(() => api.createProcess({ service_id: s.id, name: n.trim() })); };
  const addStep = (pid: string, order: number) => { const n = window.prompt("Paso / actividad:"); if (n?.trim()) run(() => api.createStep({ process_id: pid, name: n.trim(), order })); };

  if (!tree) return <Shell><div className="p-8 text-sm text-slate-400">Cargando mapa de procesos…</div></Shell>;
  const empty = tree.lines.length === 0;

  return (
    <Shell>
      <PageHeader title="Mapa de Procesos"
        subtitle="Línea → Servicio (interno OLA / externo SLA) → Proceso → Paso. Liga cada paso a un agente/automatización y mide el ahorro real con tus costos." />
      <div className="p-6">
        {err && <div className="mb-4 rounded-lg bg-red-50 px-4 py-2 text-sm text-red-600">{err}</div>}

        {welcome && (
          <div className="mb-4 flex items-start gap-3 rounded-2xl border border-violet-200 bg-violet-50 px-4 py-3">
            <Workflow className="mt-0.5 h-5 w-5 shrink-0 text-violet-600" />
            <div className="flex-1 text-sm text-violet-900">
              <p className="font-semibold">¡Empresa configurada! Este es tu Mapa de Procesos.</p>
              <p className="mt-0.5 text-violet-700">Dibuja aquí tus líneas de negocio → servicios (interno OLA / externo SLA) → procesos → pasos. Liga cada paso a un agente o automatización para medir el ahorro real. Empieza creando tu primera línea de negocio.</p>
            </div>
            <button onClick={() => setWelcome(false)} className="rounded-md p-1 text-violet-400 hover:bg-violet-100 hover:text-violet-700"><X className="h-4 w-4" /></button>
          </div>
        )}

        {roi && <RoiBar roi={roi} />}

        <div className="mb-4 flex flex-wrap items-center gap-3">
          <button onClick={addLine} className="inline-flex items-center gap-1.5 rounded-lg bg-violet-600 px-3 py-2 text-sm font-semibold text-white hover:bg-violet-700">
            <Plus className="h-4 w-4" /> Nueva línea de negocio
          </button>
          <div className="flex rounded-lg bg-slate-100 p-1">
            <button onClick={() => setView("list")} className={`flex items-center gap-1 rounded-md px-3 py-1 text-sm font-semibold ${view === "list" ? "bg-white text-slate-900 shadow-sm" : "text-slate-500"}`}><List className="h-3.5 w-3.5" /> Lista</button>
            <button onClick={() => setView("canvas")} className={`flex items-center gap-1 rounded-md px-3 py-1 text-sm font-semibold ${view === "canvas" ? "bg-white text-slate-900 shadow-sm" : "text-slate-500"}`}><LayoutGrid className="h-3.5 w-3.5" /> Lienzo</button>
          </div>
          <span className="text-xs text-slate-400">Interno = OLA · Externo = SLA (cliente que paga). Clic en un paso para ligar IA y medir ROI.</span>
        </div>

        {empty ? (
          <div className="rounded-2xl border border-dashed border-slate-300 bg-white p-10 text-center">
            <Building2 className="mx-auto mb-3 h-8 w-8 text-slate-300" />
            <p className="text-sm text-slate-500">Aún no hay líneas de negocio. Crea la primera para empezar a mapear.</p>
          </div>
        ) : view === "canvas" ? (
          <ProcessCanvas tree={tree} savings={roi?.step_savings || {}} onOpenStep={setActive} />
        ) : (
          <div className="space-y-5">
            {tree.lines.map((line) => (
              <LineLane key={line.id} line={line} savings={roi?.step_savings || {}}
                onAddService={() => addService(line)} onDeleteLine={() => run(() => api.deleteLine(line.id))}
                onAddClient={addClient} onDeleteService={(id) => run(() => api.deleteService(id))}
                onAddProcess={addProcess} onDeleteProcess={(id) => run(() => api.deleteProcess(id))}
                onAddStep={addStep} onDeleteStep={(id) => run(() => api.deleteStep(id))} onOpenStep={setActive} />
            ))}
          </div>
        )}
      </div>
      {active && <StepModal step={active} roles={roi?.roles || []} onClose={() => setActive(null)} onChanged={load} />}
    </Shell>
  );
}

function RoiBar({ roi }: { roi: RoiSummary }) {
  const t = roi.total;
  return (
    <div className="mb-5 rounded-2xl border border-emerald-200 bg-emerald-50/50 p-4">
      <div className="mb-3 flex items-center gap-2 text-sm font-bold text-emerald-800"><TrendingUp className="h-4 w-4" /> Beneficio real de la automatización (ROI)</div>
      <div className="grid grid-cols-2 gap-4 sm:grid-cols-4">
        <Kpi label="Ahorro / mes" value={mxn(t.savings_month)} />
        <Kpi label="Ahorro / año" value={mxn(t.savings_year)} />
        <Kpi label="Horas / mes ahorradas" value={t.hours_saved_month.toLocaleString("es-MX")} />
        <Kpi label="Pasos automatizados" value={`${t.steps_automated} / ${t.steps_measured}`} />
      </div>
      {roi.by_client.length > 0 && (
        <div className="mt-3 flex flex-wrap gap-2 border-t border-emerald-200 pt-2 text-xs">
          <span className="text-slate-500">Por cliente:</span>
          {roi.by_client.slice(0, 8).map((c) => (
            <span key={c.name} className="rounded-full bg-white px-2 py-0.5 text-emerald-700">{c.name}: <b>{mxn(c.savings_month)}/mes</b></span>
          ))}
        </div>
      )}
    </div>
  );
}
function Kpi({ label, value }: { label: string; value: string }) {
  return <div><div className="text-xs text-slate-500">{label}</div><div className="text-xl font-extrabold tabular-nums text-slate-900">{value}</div></div>;
}

function LineLane({ line, savings, onAddService, onDeleteLine, onAddClient, onDeleteService, onAddProcess, onDeleteProcess, onAddStep, onDeleteStep, onOpenStep }: {
  line: LineNode; savings: RoiSummary["step_savings"];
  onAddService: () => void; onDeleteLine: () => void; onAddClient: (s: ServiceNode) => void; onDeleteService: (id: string) => void;
  onAddProcess: (s: ServiceNode) => void; onDeleteProcess: (id: string) => void;
  onAddStep: (pid: string, order: number) => void; onDeleteStep: (id: string) => void; onOpenStep: (s: ProcessStepNode) => void;
}) {
  return (
    <div className="rounded-2xl border border-slate-200 bg-white">
      <div className="flex items-center justify-between border-b border-slate-100 px-5 py-3">
        <div className="flex items-center gap-2 font-bold text-slate-800"><Building2 className="h-4 w-4 text-violet-600" /> {line.name}</div>
        <div className="flex items-center gap-2">
          <button onClick={onAddService} className="inline-flex items-center gap-1 rounded-lg border border-slate-300 px-2.5 py-1 text-xs font-semibold text-slate-600 hover:bg-slate-50"><Plus className="h-3.5 w-3.5" /> Servicio</button>
          <button onClick={onDeleteLine} className="rounded-lg p-1.5 text-slate-400 hover:bg-red-50 hover:text-red-600" aria-label="Borrar línea"><Trash2 className="h-4 w-4" /></button>
        </div>
      </div>
      <div className="flex gap-4 overflow-x-auto p-4">
        {line.services.length === 0 && <p className="text-sm text-slate-400">Sin servicios. Agrega uno →</p>}
        {line.services.map((svc) => (
          <div key={svc.id} className="w-72 shrink-0 rounded-xl border border-slate-200 bg-slate-50/60">
            <div className="border-b border-slate-100 p-3">
              <div className="flex items-start justify-between gap-2">
                <div className="font-semibold text-slate-800">{svc.name}</div>
                <button onClick={() => onDeleteService(svc.id)} className="rounded p-1 text-slate-400 hover:bg-red-50 hover:text-red-600" aria-label="Borrar servicio"><Trash2 className="h-3.5 w-3.5" /></button>
              </div>
              <div className="mt-1 flex flex-wrap items-center gap-1.5">
                <span className={`rounded-full px-2 py-0.5 text-[11px] font-semibold ${svc.kind === "external" ? "bg-blue-100 text-blue-700" : "bg-purple-100 text-purple-700"}`}>{svc.kind === "external" ? "Externo · SLA" : "Interno · OLA"}</span>
                {svc.sla_ola && <span className="text-[11px] text-slate-500">{svc.sla_ola}</span>}
              </div>
              {svc.kind === "external" && (
                <div className="mt-2 flex flex-wrap items-center gap-1">
                  {svc.clients.map((c) => <span key={c} className="rounded-full bg-emerald-50 px-2 py-0.5 text-[11px] text-emerald-700">{c}</span>)}
                  <button onClick={() => onAddClient(svc)} className="rounded-full border border-dashed border-slate-300 px-2 py-0.5 text-[11px] text-slate-500 hover:bg-white">+ cliente</button>
                </div>
              )}
            </div>
            <div className="space-y-2 p-3">
              {svc.processes.map((proc) => (
                <div key={proc.id} className="rounded-lg border border-slate-200 bg-white p-2">
                  <div className="mb-1.5 flex items-center justify-between">
                    <div className="flex items-center gap-1.5 text-sm font-medium text-slate-700"><Workflow className="h-3.5 w-3.5 text-slate-400" /> {proc.name}</div>
                    <button onClick={() => onDeleteProcess(proc.id)} className="rounded p-0.5 text-slate-300 hover:text-red-600" aria-label="Borrar proceso"><Trash2 className="h-3 w-3" /></button>
                  </div>
                  <div className="space-y-1">
                    {proc.steps.map((st) => {
                      const sv = savings[st.id];
                      return (
                        <div key={st.id} className="flex items-center justify-between gap-2 rounded border border-slate-100 bg-slate-50 px-2 py-1">
                          <button onClick={() => onOpenStep(st)} className="min-w-0 flex-1 truncate text-left text-xs text-slate-600 hover:text-violet-700" title={st.name}>{st.name}</button>
                          <div className="flex shrink-0 items-center gap-1">
                            {sv && sv.savings_month > 0 && <span className="rounded bg-emerald-100 px-1 py-0.5 text-[10px] font-semibold text-emerald-700" title="Ahorro mensual estimado">{mxn(sv.savings_month)}/m</span>}
                            <span className={`rounded px-1.5 py-0.5 text-[10px] font-semibold ${STATE_CLS[st.automation_state as StepStateT]}`}>{STATE_LABEL[st.automation_state as StepStateT]}</span>
                            <button onClick={() => onOpenStep(st)} className="rounded p-0.5 text-violet-500 hover:bg-violet-50" aria-label="Ligar IA y medir"><Wand2 className="h-3.5 w-3.5" /></button>
                            <button onClick={() => onDeleteStep(st.id)} className="rounded p-0.5 text-slate-300 hover:text-red-600" aria-label="Borrar paso"><Trash2 className="h-3 w-3" /></button>
                          </div>
                        </div>
                      );
                    })}
                    <button onClick={() => onAddStep(proc.id, proc.steps.length + 1)} className="w-full rounded border border-dashed border-slate-300 px-2 py-1 text-[11px] text-slate-500 hover:bg-white">+ paso</button>
                  </div>
                </div>
              ))}
              <button onClick={() => onAddProcess(svc)} className="w-full rounded-lg border border-dashed border-slate-300 px-2 py-1.5 text-xs font-medium text-slate-500 hover:bg-white">+ proceso</button>
            </div>
          </div>
        ))}
      </div>
    </div>
  );
}

function StepModal({ step, roles, onClose, onChanged }: { step: ProcessStepNode; roles: string[]; onClose: () => void; onChanged: () => void }) {
  const [links, setLinks] = useState<StepLinkDto[]>([]);
  const [metrics, setMetrics] = useState<StepMetrics>({ baseline: null, after: null });
  const [busy, setBusy] = useState(false);

  const reload = useCallback(() => {
    api.stepLinks(step.id).then(setLinks).catch(() => {});
    api.stepMetrics(step.id).then(setMetrics).catch(() => {});
  }, [step.id]);
  useEffect(() => { reload(); }, [reload]);

  async function addLink() {
    const name = window.prompt("Nombre del agente/automatización que hace este paso:");
    if (!name?.trim()) return;
    const isAgent = window.confirm("¿Es un AGENTE?\nAceptar = agente · Cancelar = automatización.");
    setBusy(true);
    try { await api.addStepLink(step.id, { target_type: isAgent ? "agent" : "automation", target_name: name.trim() }); reload(); onChanged(); }
    finally { setBusy(false); }
  }

  return (
    <div className="fixed inset-0 z-50 flex items-center justify-center bg-black/30 p-4" onClick={onClose}>
      <div className="max-h-[85vh] w-full max-w-lg overflow-auto rounded-2xl bg-white p-5 shadow-xl" onClick={(e) => e.stopPropagation()}>
        <div className="mb-3 flex items-center justify-between">
          <h2 className="font-bold text-slate-900">{step.name}</h2>
          <button onClick={onClose} className="rounded p-1 text-slate-400 hover:bg-slate-100" aria-label="Cerrar"><X className="h-4 w-4" /></button>
        </div>

        <section className="mb-5">
          <div className="mb-2 flex items-center gap-1.5 text-sm font-semibold text-slate-700"><Link2 className="h-4 w-4 text-violet-600" /> Automatizado por</div>
          <div className="space-y-1">
            {links.length === 0 && <p className="text-xs text-slate-400">Sin recursos ligados. Liga el agente/automatización que ejecuta este paso.</p>}
            {links.map((l) => (
              <div key={l.id} className="flex items-center justify-between rounded-lg border border-slate-200 px-2.5 py-1.5 text-sm">
                <span><span className="mr-1.5 rounded bg-slate-100 px-1.5 py-0.5 text-[10px] uppercase text-slate-500">{l.target_type}</span>{l.target_name}</span>
                <button onClick={async () => { await api.deleteStepLink(l.id); reload(); onChanged(); }} className="text-slate-300 hover:text-red-600" aria-label="Quitar"><Trash2 className="h-3.5 w-3.5" /></button>
              </div>
            ))}
          </div>
          <button onClick={addLink} disabled={busy} className="mt-2 inline-flex items-center gap-1 rounded-lg border border-violet-300 px-2.5 py-1 text-xs font-semibold text-violet-700 hover:bg-violet-50 disabled:opacity-50"><Plus className="h-3.5 w-3.5" /> Ligar agente/automatización</button>
        </section>

        <section>
          <div className="mb-2 flex items-center gap-1.5 text-sm font-semibold text-slate-700"><Gauge className="h-4 w-4 text-emerald-600" /> Medir beneficio (ROI)</div>
          <div className="grid grid-cols-2 gap-3">
            <MetricForm stepId={step.id} phase="baseline" title="Antes (baseline)" roles={roles} initial={metrics.baseline} onSaved={() => { reload(); onChanged(); }} />
            <MetricForm stepId={step.id} phase="after" title="Después (con IA)" roles={roles} initial={metrics.after} onSaved={() => { reload(); onChanged(); }} />
          </div>
          <Savings m={metrics} />
        </section>
      </div>
    </div>
  );
}

function MetricForm({ stepId, phase, title, roles, initial, onSaved }: {
  stepId: string; phase: "baseline" | "after"; title: string; roles: string[];
  initial: StepMetrics["baseline"]; onSaved: () => void;
}) {
  const [hours, setHours] = useState(String(initial?.hours_per_cycle ?? ""));
  const [role, setRole] = useState(initial?.role ?? "");
  const [cost, setCost] = useState(String(initial?.cost_per_cycle ?? ""));
  const [vol, setVol] = useState(String(initial?.volume_month ?? ""));
  const [busy, setBusy] = useState(false);
  useEffect(() => {
    setHours(String(initial?.hours_per_cycle ?? "")); setRole(initial?.role ?? "");
    setCost(String(initial?.cost_per_cycle ?? "")); setVol(String(initial?.volume_month ?? ""));
  }, [initial]);

  async function save() {
    setBusy(true);
    try {
      await api.saveStepMetric(stepId, { phase, hours_per_cycle: Number(hours) || 0, role,
        cost_per_cycle: Number(cost) || 0, volume_month: Number(vol) || 0 });
      onSaved();
    } finally { setBusy(false); }
  }
  return (
    <div className="rounded-lg border border-slate-200 p-2.5">
      <div className="mb-1.5 text-xs font-semibold text-slate-600">{title}</div>
      <label className="block text-[11px] text-slate-400">Horas/ciclo</label>
      <input value={hours} onChange={(e) => setHours(e.target.value)} inputMode="decimal" className="mb-1 w-full rounded border border-slate-300 px-2 py-1 text-sm" />
      <label className="block text-[11px] text-slate-400">Rol (costo-hora del Tablero)</label>
      <input list="roles-dl" value={role} onChange={(e) => setRole(e.target.value)} placeholder="opcional" className="mb-1 w-full rounded border border-slate-300 px-2 py-1 text-sm" />
      <datalist id="roles-dl">{roles.map((r) => <option key={r} value={r} />)}</datalist>
      <label className="block text-[11px] text-slate-400">Costo/ciclo (vacío = derivar de horas×rol)</label>
      <input value={cost} onChange={(e) => setCost(e.target.value)} inputMode="decimal" className="mb-1 w-full rounded border border-slate-300 px-2 py-1 text-sm" />
      <label className="block text-[11px] text-slate-400">Ciclos/mes</label>
      <input value={vol} onChange={(e) => setVol(e.target.value)} inputMode="decimal" className="mb-2 w-full rounded border border-slate-300 px-2 py-1 text-sm" />
      <button onClick={save} disabled={busy} className="w-full rounded-lg bg-slate-900 px-2 py-1 text-xs font-semibold text-white disabled:opacity-50">{busy ? "Guardando…" : "Guardar"}</button>
    </div>
  );
}

function Savings({ m }: { m: StepMetrics }) {
  if (!m.baseline) return null;
  const vol = (m.after?.volume_month || m.baseline.volume_month) || 0;
  const saveCycle = m.baseline.cost_per_cycle - (m.after?.cost_per_cycle || 0);
  const month = saveCycle * vol;
  const hours = (m.baseline.hours_per_cycle - (m.after?.hours_per_cycle || 0)) * vol;
  return (
    <div className="mt-3 rounded-lg border border-emerald-200 bg-emerald-50 p-3 text-sm text-emerald-800">
      Ahorro estimado: <b>{mxn(month)}/mes</b> ({mxn(month * 12)}/año) · <b>{hours.toLocaleString("es-MX")}</b> horas/mes
      {!m.after && <div className="mt-1 text-xs text-emerald-600">Captura el “después” para confirmar el ahorro real.</div>}
    </div>
  );
}
