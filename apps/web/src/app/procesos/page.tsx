"use client";

import { PageHeader, Shell } from "@/components/Shell";
import { api } from "@/lib/api";
import type { LineNode, ProcessTree, ServiceNode } from "@shared/types";
import { Building2, Plus, Trash2, Wand2, Workflow } from "lucide-react";
import Link from "next/link";
import { useCallback, useEffect, useState } from "react";

type StepStateT = "manual" | "candidate" | "automated";
const STATE_LABEL: Record<StepStateT, string> = { manual: "Manual", candidate: "Candidato", automated: "Automatizado" };
const STATE_CLS: Record<StepStateT, string> = {
  manual: "bg-slate-100 text-slate-600",
  candidate: "bg-amber-100 text-amber-700",
  automated: "bg-emerald-100 text-emerald-700",
};
const nextState: Record<StepStateT, StepStateT> = { manual: "candidate", candidate: "automated", automated: "manual" };

export default function ProcesosPage() {
  const [tree, setTree] = useState<ProcessTree | null>(null);
  const [err, setErr] = useState("");

  const load = useCallback(() => {
    api.processTree().then(setTree).catch((e) => setErr(e instanceof Error ? e.message : "Error"));
  }, []);
  useEffect(() => { load(); }, [load]);

  async function run(fn: () => Promise<unknown>) {
    setErr("");
    try { await fn(); load(); }
    catch (e) { setErr(e instanceof Error ? e.message : "Error"); }
  }

  const addLine = () => {
    const name = window.prompt("Nombre de la línea de negocio (ej. SOC, Consultoría):");
    if (name?.trim()) run(() => api.createLine({ name: name.trim() }));
  };
  const addService = (line: LineNode) => {
    const name = window.prompt(`Servicio de «${line.name}»:`);
    if (!name?.trim()) return;
    const ext = window.confirm("¿Es un servicio EXTERNO (SLA, cliente paga)?\nAceptar = externo · Cancelar = interno (OLA).");
    const sla = window.prompt(ext ? "SLA (ej. 99.9% disponibilidad):" : "OLA (ej. respuesta en 4h):") || "";
    run(() => api.createService({ line_id: line.id, name: name.trim(), kind: ext ? "external" : "internal", sla_ola: sla }));
  };
  const addClient = (svc: ServiceNode) => {
    const name = window.prompt(`Cliente que recibe «${svc.name}»:`);
    if (name?.trim()) run(() => api.addServiceClient(svc.id, name.trim()));
  };
  const addProcess = (svc: ServiceNode) => {
    const name = window.prompt(`Proceso de «${svc.name}»:`);
    if (name?.trim()) run(() => api.createProcess({ service_id: svc.id, name: name.trim() }));
  };
  const addStep = (processId: string, order: number) => {
    const name = window.prompt("Paso / actividad:");
    if (name?.trim()) run(() => api.createStep({ process_id: processId, name: name.trim(), order }));
  };
  const cycleState = (stepId: string, processId: string, state: StepStateT) =>
    run(() => api.updateStep(stepId, { process_id: processId, name: "", automation_state: nextState[state] }));

  if (!tree) return <Shell><div className="p-8 text-sm text-slate-400">Cargando mapa de procesos…</div></Shell>;

  const empty = tree.lines.length === 0;

  return (
    <Shell>
      <PageHeader
        title="Mapa de Procesos"
        subtitle="Línea de negocio → Servicio (interno OLA / externo SLA) → Proceso → Paso. La columna vertebral: cada paso puede automatizarse con IA y medir su beneficio."
      />
      <div className="p-6">
        {err && <div className="mb-4 rounded-lg bg-red-50 px-4 py-2 text-sm text-red-600">{err}</div>}

        <div className="mb-4 flex items-center gap-3">
          <button onClick={addLine} className="inline-flex items-center gap-1.5 rounded-lg bg-violet-600 px-3 py-2 text-sm font-semibold text-white hover:bg-violet-700">
            <Plus className="h-4 w-4" /> Nueva línea de negocio
          </button>
          <span className="text-xs text-slate-400">Interno = OLA (áreas internas) · Externo = SLA (cliente que paga)</span>
        </div>

        {empty ? (
          <div className="rounded-2xl border border-dashed border-slate-300 bg-white p-10 text-center">
            <Building2 className="mx-auto mb-3 h-8 w-8 text-slate-300" />
            <p className="text-sm text-slate-500">Aún no hay líneas de negocio. Crea la primera para empezar a mapear tus servicios y procesos.</p>
          </div>
        ) : (
          <div className="space-y-5">
            {tree.lines.map((line) => (
              <LineLane key={line.id} line={line}
                onAddService={() => addService(line)}
                onDeleteLine={() => run(() => api.deleteLine(line.id))}
                onAddClient={addClient}
                onDeleteService={(id) => run(() => api.deleteService(id))}
                onAddProcess={addProcess}
                onDeleteProcess={(id) => run(() => api.deleteProcess(id))}
                onAddStep={addStep}
                onDeleteStep={(id) => run(() => api.deleteStep(id))}
                onCycleState={cycleState}
              />
            ))}
          </div>
        )}
      </div>
    </Shell>
  );
}

function LineLane({ line, onAddService, onDeleteLine, onAddClient, onDeleteService, onAddProcess, onDeleteProcess, onAddStep, onDeleteStep, onCycleState }: {
  line: LineNode;
  onAddService: () => void; onDeleteLine: () => void;
  onAddClient: (s: ServiceNode) => void; onDeleteService: (id: string) => void;
  onAddProcess: (s: ServiceNode) => void; onDeleteProcess: (id: string) => void;
  onAddStep: (processId: string, order: number) => void; onDeleteStep: (id: string) => void;
  onCycleState: (stepId: string, processId: string, state: StepStateT) => void;
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
                <span className={`rounded-full px-2 py-0.5 text-[11px] font-semibold ${svc.kind === "external" ? "bg-blue-100 text-blue-700" : "bg-purple-100 text-purple-700"}`}>
                  {svc.kind === "external" ? "Externo · SLA" : "Interno · OLA"}
                </span>
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
                    {proc.steps.map((st) => (
                      <div key={st.id} className="flex items-center justify-between gap-2 rounded border border-slate-100 bg-slate-50 px-2 py-1">
                        <span className="truncate text-xs text-slate-600" title={st.name}>{st.name}</span>
                        <div className="flex shrink-0 items-center gap-1">
                          <button onClick={() => onCycleState(st.id, proc.id, st.automation_state as StepStateT)}
                            title="Cambiar estado de automatización"
                            className={`rounded px-1.5 py-0.5 text-[10px] font-semibold ${STATE_CLS[st.automation_state as StepStateT]}`}>
                            {STATE_LABEL[st.automation_state as StepStateT]}
                          </button>
                          <Link href="/agents" title="Automatizar con IA (Fase 3)" className="rounded p-0.5 text-violet-500 hover:bg-violet-50"><Wand2 className="h-3.5 w-3.5" /></Link>
                          <button onClick={() => onDeleteStep(st.id)} className="rounded p-0.5 text-slate-300 hover:text-red-600" aria-label="Borrar paso"><Trash2 className="h-3 w-3" /></button>
                        </div>
                      </div>
                    ))}
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
