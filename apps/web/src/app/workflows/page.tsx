"use client";

import { PageHeader, Shell } from "@/components/Shell";
import { api } from "@/lib/api";
import { Play, Workflow } from "lucide-react";
import { useEffect, useState } from "react";

export default function WorkflowsPage() {
  const [workflows, setWorkflows] = useState<{ id: string; name: string; steps: string }[]>([]);
  const [result, setResult] = useState<Record<string, string>>({});

  useEffect(() => {
    api.workflows().then(setWorkflows);
  }, []);

  async function run(id: string) {
    setResult((r) => ({ ...r, [id]: "Ejecutando…" }));
    const res = await api.runWorkflow(id);
    setResult((r) => ({ ...r, [id]: `${res.status} · ${res.engine} (run ${res.run_id})` }));
  }

  return (
    <Shell>
      <PageHeader title="Workflows operativos" subtitle="Ingesta, RAG, SOW, diagnóstico cyber, centro de mando, fine-tuning." />
      <div className="grid grid-cols-1 gap-4 p-8 md:grid-cols-2">
        {workflows.map((w) => (
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
              {result[w.id] && <span className="text-sm text-emerald-600">{result[w.id]}</span>}
            </div>
          </div>
        ))}
      </div>
    </Shell>
  );
}
