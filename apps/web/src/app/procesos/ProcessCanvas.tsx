"use client";

import { api } from "@/lib/api";
import type { ProcessStepNode, ProcessTree, RoiSummary } from "@shared/types";
import { Building2, GripVertical, Wand2, Workflow } from "lucide-react";
import { useCallback, useEffect, useRef, useState } from "react";

type Pos = { x: number; y: number };
type Positions = Record<string, Pos>;

const SVC_W = 288;      // ancho de la tarjeta de servicio
const LINE_W = 180;     // ancho del nodo de línea
const mxn = (n: number) => "$" + (n || 0).toLocaleString("es-MX", { maximumFractionDigits: 0 });
const STATE_CLS: Record<string, string> = {
  manual: "bg-slate-100 text-slate-600", candidate: "bg-amber-100 text-amber-700", automated: "bg-emerald-100 text-emerald-700",
};

/** Posiciones por defecto si el tenant aún no guardó layout: líneas en columna, servicios en fila. */
function autoLayout(tree: ProcessTree): Positions {
  const pos: Positions = {};
  let y = 30;
  for (const line of tree.lines) {
    pos[line.id] = { x: 30, y };
    line.services.forEach((s, j) => { pos[s.id] = { x: 260 + j * (SVC_W + 32), y: y }; });
    y += Math.max(1, 1) * 260;
  }
  return pos;
}

export function ProcessCanvas({ tree, savings, onOpenStep }: {
  tree: ProcessTree; savings: RoiSummary["step_savings"]; onOpenStep: (s: ProcessStepNode) => void;
}) {
  const [pos, setPos] = useState<Positions>({});
  const [zoom, setZoom] = useState(1);
  const drag = useRef<{ id: string; dx: number; dy: number } | null>(null);
  const saveTimer = useRef<ReturnType<typeof setTimeout> | null>(null);
  const stageRef = useRef<HTMLDivElement | null>(null);

  useEffect(() => {
    let cancelled = false;
    api.canvasLayout().then((r) => {
      if (cancelled) return;
      const auto = autoLayout(tree);
      setPos({ ...auto, ...(r.positions || {}) }); // guardadas ganan; el resto por defecto
    }).catch(() => setPos(autoLayout(tree)));
    return () => { cancelled = true; };
  }, [tree]);

  const persist = useCallback((next: Positions) => {
    if (saveTimer.current) clearTimeout(saveTimer.current);
    saveTimer.current = setTimeout(() => { api.saveCanvasLayout(next).catch(() => {}); }, 600);
  }, []);

  const onPointerDown = (id: string) => (e: React.PointerEvent) => {
    e.preventDefault();
    const p = pos[id] || { x: 40, y: 40 };
    drag.current = { id, dx: e.clientX / zoom - p.x, dy: e.clientY / zoom - p.y };
    (e.target as HTMLElement).setPointerCapture?.(e.pointerId);
  };
  const onPointerMove = (e: React.PointerEvent) => {
    if (!drag.current) return;
    const { id, dx, dy } = drag.current;
    const x = Math.max(0, Math.round(e.clientX / zoom - dx));
    const y = Math.max(0, Math.round(e.clientY / zoom - dy));
    setPos((prev) => ({ ...prev, [id]: { x, y } }));
  };
  const onPointerUp = () => {
    if (drag.current) { setPos((prev) => { persist(prev); return prev; }); drag.current = null; }
  };

  // Conectores Línea → Servicio (ancla derecha de la línea → izquierda del servicio).
  const edges: { x1: number; y1: number; x2: number; y2: number }[] = [];
  for (const line of tree.lines) {
    const lp = pos[line.id]; if (!lp) continue;
    for (const s of line.services) {
      const sp = pos[s.id]; if (!sp) continue;
      edges.push({ x1: lp.x + LINE_W, y1: lp.y + 18, x2: sp.x, y2: sp.y + 22 });
    }
  }
  const maxX = Math.max(1200, ...Object.values(pos).map((p) => p.x + SVC_W + 60));
  const maxY = Math.max(600, ...Object.values(pos).map((p) => p.y + 420));

  return (
    <div>
      <div className="mb-2 flex items-center gap-2">
        <span className="text-xs text-slate-400">Arrastra los nodos; las posiciones se guardan solas. Clic en un paso para ligar IA / medir ROI. Estructura nueva → usa la vista Lista.</span>
        <div className="ml-auto flex items-center gap-1">
          <button onClick={() => setZoom((z) => Math.max(0.5, +(z - 0.1).toFixed(2)))} className="rounded border border-slate-300 px-2 py-0.5 text-sm">−</button>
          <span className="w-10 text-center text-xs tabular-nums text-slate-500">{Math.round(zoom * 100)}%</span>
          <button onClick={() => setZoom((z) => Math.min(1.5, +(z + 0.1).toFixed(2)))} className="rounded border border-slate-300 px-2 py-0.5 text-sm">+</button>
        </div>
      </div>
      <div className="overflow-auto rounded-2xl border border-slate-200 bg-[radial-gradient(circle,#e2e8f0_1px,transparent_1px)] [background-size:20px_20px]"
        style={{ maxHeight: "70vh" }} onPointerMove={onPointerMove} onPointerUp={onPointerUp} onPointerLeave={onPointerUp}>
        <div ref={stageRef} className="relative" style={{ width: maxX, height: maxY, transform: `scale(${zoom})`, transformOrigin: "top left" }}>
          <svg className="pointer-events-none absolute inset-0 h-full w-full">
            {edges.map((e, i) => (
              <path key={i} d={`M ${e.x1} ${e.y1} C ${e.x1 + 50} ${e.y1}, ${e.x2 - 50} ${e.y2}, ${e.x2} ${e.y2}`}
                stroke="#cbd5e1" strokeWidth={2} fill="none" />
            ))}
          </svg>

          {tree.lines.map((line) => {
            const lp = pos[line.id]; if (!lp) return null;
            return (
              <div key={line.id} className="absolute" style={{ left: lp.x, top: lp.y, width: LINE_W }}>
                <div onPointerDown={onPointerDown(line.id)}
                  className="flex cursor-grab items-center gap-1.5 rounded-lg bg-violet-600 px-3 py-2 text-sm font-bold text-white shadow active:cursor-grabbing">
                  <GripVertical className="h-3.5 w-3.5 opacity-70" /> <Building2 className="h-4 w-4" /> {line.name}
                </div>
              </div>
            );
          })}

          {tree.lines.flatMap((line) => line.services.map((svc) => {
            const sp = pos[svc.id]; if (!sp) return null;
            return (
              <div key={svc.id} className="absolute rounded-xl border border-slate-200 bg-white shadow-sm" style={{ left: sp.x, top: sp.y, width: SVC_W }}>
                <div onPointerDown={onPointerDown(svc.id)} className="flex cursor-grab items-center justify-between gap-2 rounded-t-xl border-b border-slate-100 bg-slate-50 px-3 py-2 active:cursor-grabbing">
                  <div className="flex items-center gap-1.5 font-semibold text-slate-800"><GripVertical className="h-3.5 w-3.5 text-slate-300" /> {svc.name}</div>
                  <span className={`rounded-full px-2 py-0.5 text-[10px] font-semibold ${svc.kind === "external" ? "bg-blue-100 text-blue-700" : "bg-purple-100 text-purple-700"}`}>{svc.kind === "external" ? "SLA" : "OLA"}</span>
                </div>
                <div className="p-2.5">
                  {svc.kind === "external" && svc.clients.length > 0 && (
                    <div className="mb-2 flex flex-wrap gap-1">
                      {svc.clients.map((c) => <span key={c} className="rounded-full bg-emerald-50 px-2 py-0.5 text-[10px] text-emerald-700">{c}</span>)}
                    </div>
                  )}
                  <div className="space-y-1.5">
                    {svc.processes.map((proc) => (
                      <div key={proc.id} className="rounded-lg border border-slate-100 p-1.5">
                        <div className="mb-1 flex items-center gap-1 text-xs font-medium text-slate-600"><Workflow className="h-3 w-3 text-slate-400" /> {proc.name}</div>
                        {proc.steps.map((st) => {
                          const sv = savings[st.id];
                          return (
                            <div key={st.id} className="flex items-center justify-between gap-1 rounded bg-slate-50 px-1.5 py-1">
                              <button onClick={() => onOpenStep(st)} className="min-w-0 flex-1 truncate text-left text-[11px] text-slate-600 hover:text-violet-700" title={st.name}>{st.name}</button>
                              {sv && sv.savings_month > 0 && <span className="rounded bg-emerald-100 px-1 text-[9px] font-semibold text-emerald-700">{mxn(sv.savings_month)}/m</span>}
                              <span className={`rounded px-1 text-[9px] font-semibold ${STATE_CLS[st.automation_state]}`}>{st.automation_state[0].toUpperCase()}</span>
                              <button onClick={() => onOpenStep(st)} className="text-violet-500 hover:text-violet-700" aria-label="Ligar IA / medir"><Wand2 className="h-3 w-3" /></button>
                            </div>
                          );
                        })}
                        {proc.steps.length === 0 && <div className="px-1 text-[10px] text-slate-300">sin pasos</div>}
                      </div>
                    ))}
                    {svc.processes.length === 0 && <div className="text-[10px] text-slate-300">sin procesos</div>}
                  </div>
                </div>
              </div>
            );
          }))}
        </div>
      </div>
    </div>
  );
}
