"use client";

import { PageHeader, Shell } from "@/components/Shell";
import { api } from "@/lib/api";
import type { Flowchart, FlowchartSummary, FlowNode } from "@shared/types";
import { CornerDownRight, Plus, RotateCcw, Trash2, Undo2 } from "lucide-react";
import { useEffect, useState } from "react";

const TYPE_STYLE: Record<FlowNode["type"], { box: string; chip: string; label: string }> = {
  start: { box: "border-violet-300 bg-violet-50", chip: "bg-violet-600", label: "Inicio" },
  step: { box: "border-slate-300 bg-white", chip: "bg-slate-400", label: "Paso" },
  decision: { box: "border-amber-300 bg-amber-50", chip: "bg-amber-500", label: "Decisión" },
  danger: { box: "border-red-300 bg-red-50", chip: "bg-red-600", label: "Privado / sensible" },
  end: { box: "border-emerald-300 bg-emerald-50", chip: "bg-emerald-600", label: "Fin" },
};

const FREE_KEY = "maestro_free_flow";

export default function FlowchartsPage() {
  const [list, setList] = useState<FlowchartSummary[]>([]);
  const [selected, setSelected] = useState<string>("");
  const [flow, setFlow] = useState<Flowchart | null>(null);
  const [currentId, setCurrentId] = useState<string>("");
  const [history, setHistory] = useState<string[]>([]);
  // free mode
  const [freeNodes, setFreeNodes] = useState<FlowNode[]>([]);
  const [draft, setDraft] = useState<{ title: string; detail: string; type: FlowNode["type"] }>({ title: "", detail: "", type: "step" });

  useEffect(() => {
    api.flowcharts().then((l) => {
      setList(l);
      if (l[0]) select(l[0].id);
    }).catch(() => {});
    try {
      const raw = localStorage.getItem(FREE_KEY);
      if (raw) setFreeNodes(JSON.parse(raw));
    } catch { /* ignore */ }
  }, []);

  function select(id: string) {
    setSelected(id);
    if (id === "free") { setFlow(null); return; }
    api.flowchart(id).then((f) => {
      setFlow(f);
      setCurrentId(f.start);
      setHistory([]);
    }).catch(() => {});
  }

  function goTo(id: string) {
    setHistory((h) => [...h, currentId]);
    setCurrentId(id);
  }
  function back() {
    setHistory((h) => {
      if (!h.length) return h;
      setCurrentId(h[h.length - 1]);
      return h.slice(0, -1);
    });
  }

  // Build a Flowchart object for free mode (linear: each node points to the next).
  const freeFlow: Flowchart | null = freeNodes.length
    ? {
        id: "free", title: "Flujo libre", description: "Tu flujo personalizado.",
        start: freeNodes[0].id,
        nodes: freeNodes.map((n, i) => ({ ...n, next: freeNodes[i + 1]?.id })),
      }
    : null;

  const activeFlow = selected === "free" ? freeFlow : flow;
  const current = activeFlow?.nodes.find((n) => n.id === currentId) || activeFlow?.nodes[0] || null;

  function saveFree(nodes: FlowNode[]) {
    setFreeNodes(nodes);
    try { localStorage.setItem(FREE_KEY, JSON.stringify(nodes)); } catch { /* ignore */ }
  }
  function addFreeNode() {
    if (!draft.title.trim()) return;
    const node: FlowNode = { id: `n${Date.now()}`, type: draft.type, title: draft.title.trim(), detail: draft.detail.trim() };
    const next = [...freeNodes, node];
    saveFree(next);
    setDraft({ title: "", detail: "", type: "step" });
    if (next.length === 1) { setCurrentId(node.id); setHistory([]); }
  }
  function removeFreeNode(id: string) {
    saveFree(freeNodes.filter((n) => n.id !== id));
  }

  return (
    <Shell>
      <PageHeader title="Flujogramas" subtitle="La lógica del producto, navegable. Recorre los flujos base o diseña el tuyo." />
      <div className="grid grid-cols-1 gap-6 p-8 lg:grid-cols-4">
        {/* List */}
        <aside className="space-y-2 lg:col-span-1">
          {list.map((f) => (
            <button key={f.id} onClick={() => select(f.id)}
              className={`w-full rounded-xl border p-3 text-left transition ${selected === f.id ? "border-violet-400 bg-violet-50" : "border-slate-200 bg-white hover:border-violet-300"}`}>
              <div className="text-sm font-semibold text-slate-800">{f.title}</div>
              <div className="mt-0.5 text-xs text-slate-500">{f.description}</div>
            </button>
          ))}
          <button onClick={() => select("free")}
            className={`w-full rounded-xl border border-dashed p-3 text-left transition ${selected === "free" ? "border-violet-400 bg-violet-50" : "border-slate-300 bg-white hover:border-violet-300"}`}>
            <div className="flex items-center gap-1.5 text-sm font-semibold text-slate-800"><Plus className="h-4 w-4" /> Flujo libre</div>
            <div className="mt-0.5 text-xs text-slate-500">Diseña tu propio flujo paso a paso.</div>
          </button>
        </aside>

        {/* Diagram + navigation */}
        <section className="lg:col-span-3">
          {selected === "free" && (
            <div className="mb-5 rounded-2xl border border-slate-200 bg-white p-4">
              <h3 className="mb-2 text-sm font-semibold text-slate-800">Construye tu flujo</h3>
              <div className="flex flex-wrap items-end gap-2">
                <input value={draft.title} onChange={(e) => setDraft((d) => ({ ...d, title: e.target.value }))}
                  placeholder="Título del paso" className="flex-1 rounded-lg border border-slate-300 px-3 py-2 text-sm" />
                <select value={draft.type} onChange={(e) => setDraft((d) => ({ ...d, type: e.target.value as FlowNode["type"] }))}
                  className="rounded-lg border border-slate-300 px-3 py-2 text-sm">
                  <option value="start">Inicio</option>
                  <option value="step">Paso</option>
                  <option value="decision">Decisión</option>
                  <option value="danger">Privado / sensible</option>
                  <option value="end">Fin</option>
                </select>
                <button onClick={addFreeNode} className="rounded-lg bg-violet-600 px-4 py-2 text-sm font-semibold text-white">Agregar</button>
              </div>
              <input value={draft.detail} onChange={(e) => setDraft((d) => ({ ...d, detail: e.target.value }))}
                placeholder="Detalle (opcional)" className="mt-2 w-full rounded-lg border border-slate-300 px-3 py-2 text-sm" />
            </div>
          )}

          {!activeFlow && (
            <div className="rounded-2xl border border-dashed border-slate-300 bg-white p-10 text-center text-sm text-slate-400">
              {selected === "free" ? "Agrega tu primer paso arriba." : "Selecciona un flujograma."}
            </div>
          )}

          {activeFlow && (
            <div className="grid grid-cols-1 gap-6 lg:grid-cols-3">
              {/* The diagram */}
              <div className="lg:col-span-2">
                <h2 className="font-semibold text-slate-800">{activeFlow.title}</h2>
                <p className="mt-1 text-sm text-slate-500">{activeFlow.description}</p>
                {activeFlow.note && (
                  <div className="mt-2 rounded-lg border border-amber-200 bg-amber-50 px-3 py-2 text-xs text-amber-800">⚠️ {activeFlow.note}</div>
                )}
                <div className="mt-4 space-y-0">
                  {activeFlow.nodes.map((n, i) => {
                    const st = TYPE_STYLE[n.type];
                    const isCurrent = n.id === currentId;
                    return (
                      <div key={n.id}>
                        {i > 0 && <div className="ml-5 h-4 w-px bg-slate-300" />}
                        <button onClick={() => goTo(n.id)}
                          className={`flex w-full items-start gap-3 rounded-xl border p-3 text-left transition ${st.box} ${isCurrent ? "ring-2 ring-violet-500" : ""}`}>
                          <span className={`mt-0.5 flex h-5 items-center rounded-full px-2 text-[10px] font-bold uppercase text-white ${st.chip}`}>{st.label}</span>
                          <span className="flex-1">
                            <span className="block text-sm font-semibold text-slate-800">{n.title}</span>
                            {n.detail && <span className="mt-0.5 block text-xs text-slate-500">{n.detail}</span>}
                            {n.branches && (
                              <span className="mt-1.5 flex flex-wrap gap-1.5">
                                {n.branches.map((b) => (
                                  <span key={b.to + b.label} className="inline-flex items-center gap-1 rounded-full bg-white px-2 py-0.5 text-[11px] font-medium text-slate-600 ring-1 ring-slate-200">
                                    <CornerDownRight className="h-3 w-3" /> {b.label}
                                  </span>
                                ))}
                              </span>
                            )}
                          </span>
                          {selected === "free" && (
                            <span onClick={(e) => { e.stopPropagation(); removeFreeNode(n.id); }}
                              className="text-slate-300 hover:text-red-600"><Trash2 className="h-4 w-4" /></span>
                          )}
                        </button>
                      </div>
                    );
                  })}
                </div>
              </div>

              {/* Step-through navigation */}
              {current && (
                <div className="lg:col-span-1">
                  <div className="sticky top-6 rounded-2xl border border-slate-200 bg-white p-4">
                    <div className="text-xs font-semibold uppercase text-slate-400">Recorrido guiado</div>
                    <div className="mt-2 text-sm font-semibold text-slate-800">{current.title}</div>
                    {current.detail && <p className="mt-1 text-sm text-slate-500">{current.detail}</p>}

                    <div className="mt-4 space-y-2">
                      {current.branches?.map((b) => (
                        <button key={b.to + b.label} onClick={() => goTo(b.to)}
                          className="flex w-full items-center justify-between rounded-lg bg-violet-600 px-3 py-2 text-sm font-semibold text-white hover:bg-violet-700">
                          {b.label} <CornerDownRight className="h-4 w-4" />
                        </button>
                      ))}
                      {!current.branches && current.next && (
                        <button onClick={() => goTo(current.next!)}
                          className="w-full rounded-lg bg-violet-600 px-3 py-2 text-sm font-semibold text-white hover:bg-violet-700">
                          Continuar →
                        </button>
                      )}
                      {!current.branches && !current.next && (
                        <div className="rounded-lg bg-emerald-50 px-3 py-2 text-center text-sm font-medium text-emerald-700">Fin del flujo ✓</div>
                      )}
                    </div>

                    <div className="mt-3 flex gap-2">
                      <button onClick={back} disabled={!history.length}
                        className="flex flex-1 items-center justify-center gap-1 rounded-lg border border-slate-300 px-3 py-1.5 text-xs font-semibold text-slate-600 disabled:opacity-40">
                        <Undo2 className="h-3.5 w-3.5" /> Atrás
                      </button>
                      <button onClick={() => { setCurrentId(activeFlow.start); setHistory([]); }}
                        className="flex flex-1 items-center justify-center gap-1 rounded-lg border border-slate-300 px-3 py-1.5 text-xs font-semibold text-slate-600">
                        <RotateCcw className="h-3.5 w-3.5" /> Reiniciar
                      </button>
                    </div>
                  </div>
                </div>
              )}
            </div>
          )}
        </section>
      </div>
    </Shell>
  );
}
