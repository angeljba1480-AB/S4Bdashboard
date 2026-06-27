"use client";

import { PageHeader, Shell } from "@/components/Shell";
import { api } from "@/lib/api";
import { Info, Play, Workflow } from "lucide-react";
import { useEffect, useState } from "react";

type RunInfo = { status: string; engine: string; source: string; run_id: string; response: Record<string, unknown> | null; busy?: boolean };

export default function WorkflowsPage() {
  const [workflows, setWorkflows] = useState<{ id: string; name: string; steps: string }[]>([]);
  const [result, setResult] = useState<Record<string, RunInfo>>({});

  useEffect(() => {
    api.workflows().then(setWorkflows);
  }, []);

  async function run(id: string) {
    setResult((r) => ({ ...r, [id]: { status: "", engine: "", source: "", run_id: "", response: null, busy: true } }));
    try {
      const res = await api.runWorkflow(id);
      setResult((r) => ({ ...r, [id]: { status: res.status, engine: res.engine, source: res.source, run_id: res.run_id, response: res.response } }));
    } catch (e) {
      setResult((r) => ({ ...r, [id]: { status: "error", engine: "", source: "", run_id: "", response: { error: e instanceof Error ? e.message : "Error" } } }));
    }
  }

  return (
    <Shell>
      <PageHeader title="Workflows operativos" subtitle="Ingesta, RAG, SOW, diagnóstico cyber, centro de mando, fine-tuning." />
      <div className="px-8 pt-4">
        <div className="flex items-start gap-2 rounded-xl border border-slate-200 bg-slate-50 px-4 py-3 text-xs text-slate-600">
          <Info className="mt-0.5 h-4 w-4 shrink-0 text-slate-400" />
          <span>
            Ejecutar dispara el flujo en <b>n8n</b>. El <b>resultado</b> aparece abajo solo si tu
            workflow termina con un nodo <b>“Respond to Webhook”</b> que devuelva datos. Si no,
            el flujo es asíncrono y su salida queda donde el propio flujo la escriba:
            un <b>documento</b> (Documentos/RAG), un <b>correo</b>, una <b>hoja</b>, Teams, etc.
            El estado <i>completed</i> confirma que n8n lo recibió y ejecutó.
          </span>
        </div>
      </div>
      <div className="grid grid-cols-1 gap-4 p-8 md:grid-cols-2">
        {workflows.map((w) => {
          const r = result[w.id];
          return (
            <div key={w.id} className="rounded-2xl border border-slate-200 bg-white p-5">
              <div className="mb-2 flex items-center gap-2">
                <div className="flex h-9 w-9 items-center justify-center rounded-lg bg-indigo-50">
                  <Workflow className="h-4 w-4 text-indigo-600" />
                </div>
                <span className="font-semibold text-slate-900">{w.name}</span>
              </div>
              <p className="mb-4 text-sm text-slate-500">{w.steps}</p>
              <div className="flex items-center gap-3">
                <button
                  onClick={() => run(w.id)}
                  className="flex items-center gap-1.5 rounded-lg bg-slate-900 px-3 py-1.5 text-sm font-medium text-white hover:bg-slate-700"
                >
                  <Play className="h-3.5 w-3.5" /> Ejecutar
                </button>
                {r?.busy && <span className="text-sm text-slate-400">Ejecutando…</span>}
                {r && !r.busy && (
                  <span className={`text-sm ${r.status === "error" || r.status === "failed" ? "text-red-600" : r.status === "simulated" ? "text-amber-600" : "text-emerald-600"}`}>
                    {r.status}{r.engine ? ` · ${r.engine}` : ""}{r.run_id ? ` (run ${r.run_id})` : ""}
                  </span>
                )}
              </div>
              {r && !r.busy && (
                <div className="mt-3">
                  {r.status === "simulated" && (
                    <div className="rounded-lg border border-amber-200 bg-amber-50 px-3 py-2 text-xs text-amber-800">
                      n8n no está configurado: ejecución simulada. Conéctalo en <b>Integraciones → n8n</b>.
                    </div>
                  )}
                  {r.response && Object.keys(r.response).length > 0 ? (
                    <>
                      <div className="mb-1 text-[11px] font-semibold uppercase tracking-wide text-slate-400">Resultado (respuesta de n8n)</div>
                      <pre className="max-h-56 overflow-auto rounded-lg border border-slate-100 bg-slate-50 p-3 text-xs text-slate-700">
                        {JSON.stringify(r.response, null, 2)}
                      </pre>
                    </>
                  ) : (
                    r.status !== "simulated" && (
                      <div className="text-xs text-slate-400">
                        Sin datos de respuesta. La salida del flujo queda donde n8n la escriba (documento, correo, hoja…).
                      </div>
                    )
                  )}
                </div>
              )}
            </div>
          );
        })}
      </div>
    </Shell>
  );
}
