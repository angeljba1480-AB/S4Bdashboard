"use client";

import { api } from "@/lib/api";
import type { ProcessStepNode, ProcessTree, RoiSummary } from "@shared/types";
import { Building2, GripVertical, LayoutTemplate, Users, Wand2, Workflow } from "lucide-react";
import { useCallback, useEffect, useRef, useState } from "react";

type Pos = { x: number; y: number };
type Positions = Record<string, Pos>;

const SVC_W = 288;
const LINE_W = 180;
const CLIENT_W = 150;
const GRID = 20;
const snap = (n: number) => Math.round(n / GRID) * GRID;
const clientId = (svcId: string, name: string) => `cli:${svcId}:${name}`;
const mxn = (n: number) => "$" + (n || 0).toLocaleString("es-MX", { maximumFractionDigits: 0 });
const STATE_CLS: Record<string, string> = {
  manual: "bg-slate-100 text-slate-600", candidate: "bg-amber-100 text-amber-700", automated: "bg-emerald-100 text-emerald-700",
};

/** Layout ordenado por defecto: líneas en columna; servicios en fila; clientes a la derecha del servicio. */
function autoLayout(tree: ProcessTree): Positions {
  const pos: Positions = {};
  let y = 40;
  for (const line of tree.lines) {
    pos[line.id] = { x: 40, y };
    let rowH = 200;
    line.services.forEach((s, j) => {
      const sx = 280 + j * (SVC_W + CLIENT_W + 90);
      pos[s.id] = { x: sx, y };
      s.clients.forEach((c, k) => { pos[clientId(s.id, c)] = { x: sx + SVC_W + 50, y: y + k * 46 }; });
      rowH = Math.max(rowH, 60 + s.clients.length * 46, 200);
    });
    y += rowH + 60;
  }
  return pos;
}

export function ProcessCanvas({ tree, savings, onOpenStep }: {
  tree: ProcessTree; savings: RoiSummary["step_savings"]; onOpenStep: (s: ProcessStepNode) => void;
}) {
  const [pos, setPos] = useState<Positions>({});
  const [zoom, setZoom] = useState(1);
  const [selected, setSelected] = useState<string | null>(null);
  const drag = useRef<{ id: string; dx: number; dy: number } | null>(null);
  const pan = useRef<{ x: number; y: number; sl: number; st: number } | null>(null);
  const saveTimer = useRef<ReturnType<typeof setTimeout> | null>(null);
  const scroller = useRef<HTMLDivElement | null>(null);

  useEffect(() => {
    let cancelled = false;
    api.canvasLayout().then((r) => {
      if (cancelled) return;
      setPos({ ...autoLayout(tree), ...(r.positions || {}) });
    }).catch(() => setPos(autoLayout(tree)));
    return () => { cancelled = true; };
  }, [tree]);

  const persist = useCallback((next: Positions) => {
    if (saveTimer.current) clearTimeout(saveTimer.current);
    saveTimer.current = setTimeout(() => { api.saveCanvasLayout(next).catch(() => {}); }, 600);
  }, []);

  const startNodeDrag = (id: string) => (e: React.PointerEvent) => {
    e.preventDefault(); e.stopPropagation();
    setSelected(id);
    const p = pos[id] || { x: 40, y: 40 };
    drag.current = { id, dx: e.clientX / zoom - p.x, dy: e.clientY / zoom - p.y };
    (e.currentTarget as HTMLElement).setPointerCapture?.(e.pointerId);
  };
  const startPan = (e: React.PointerEvent) => {
    if (!scroller.current) return;
    pan.current = { x: e.clientX, y: e.clientY, sl: scroller.current.scrollLeft, st: scroller.current.scrollTop };
  };
  const onMove = (e: React.PointerEvent) => {
    if (drag.current) {
      const { id, dx, dy } = drag.current;
      const x = Math.max(0, Math.round(e.clientX / zoom - dx));
      const y = Math.max(0, Math.round(e.clientY / zoom - dy));
      setPos((prev) => ({ ...prev, [id]: { x, y } }));
    } else if (pan.current && scroller.current) {
      scroller.current.scrollLeft = pan.current.sl - (e.clientX - pan.current.x);
      scroller.current.scrollTop = pan.current.st - (e.clientY - pan.current.y);
    }
  };
  const onUp = () => {
    if (drag.current) {
      const id = drag.current.id;
      setPos((prev) => { const n = { ...prev, [id]: { x: snap(prev[id].x), y: snap(prev[id].y) } }; persist(n); return n; });
      drag.current = null;
    }
    pan.current = null;
  };
  const onWheel = (e: React.WheelEvent) => {
    if (!e.ctrlKey) return; // Ctrl/⌘ + rueda = zoom; sin Ctrl deja hacer scroll normal
    e.preventDefault();
    setZoom((z) => Math.min(1.5, Math.max(0.5, +(z - Math.sign(e.deltaY) * 0.1).toFixed(2))));
  };
  const autoArrange = () => { const a = autoLayout(tree); setPos(a); persist(a); };

  // Conectores (con flecha): Línea→Servicio y Servicio(externo)→Cliente.
  const edges: { x1: number; y1: number; x2: number; y2: number }[] = [];
  for (const line of tree.lines) {
    const lp = pos[line.id]; if (!lp) continue;
    for (const s of line.services) {
      const sp = pos[s.id]; if (!sp) continue;
      edges.push({ x1: lp.x + LINE_W, y1: lp.y + 18, x2: sp.x, y2: sp.y + 22 });
      for (const c of s.clients) {
        const cp = pos[clientId(s.id, c)]; if (!cp) continue;
        edges.push({ x1: sp.x + SVC_W, y1: sp.y + 22, x2: cp.x, y2: cp.y + 14 });
      }
    }
  }
  const allPts = Object.values(pos);
  const maxX = Math.max(1200, ...allPts.map((p) => p.x + SVC_W + CLIENT_W + 120));
  const maxY = Math.max(600, ...allPts.map((p) => p.y + 440));

  return (
    <div>
      <div className="mb-2 flex flex-wrap items-center gap-2">
        <span className="text-xs text-slate-400">Arrastra nodos (se guardan y alinean a la rejilla). Arrastra el fondo para desplazar · Ctrl/⌘+rueda para zoom.</span>
        <div className="ml-auto flex items-center gap-2">
          <button onClick={autoArrange} className="inline-flex items-center gap-1 rounded-lg border border-slate-300 px-2.5 py-1 text-xs font-semibold text-slate-600 hover:bg-slate-50"><LayoutTemplate className="h-3.5 w-3.5" /> Auto-organizar</button>
          <div className="flex items-center gap-1">
            <button onClick={() => setZoom((z) => Math.max(0.5, +(z - 0.1).toFixed(2)))} className="rounded border border-slate-300 px-2 py-0.5 text-sm">−</button>
            <span className="w-10 text-center text-xs tabular-nums text-slate-500">{Math.round(zoom * 100)}%</span>
            <button onClick={() => setZoom((z) => Math.min(1.5, +(z + 0.1).toFixed(2)))} className="rounded border border-slate-300 px-2 py-0.5 text-sm">+</button>
          </div>
        </div>
      </div>
      <div ref={scroller}
        className="overflow-auto rounded-2xl border border-slate-200 bg-[radial-gradient(circle,#e2e8f0_1px,transparent_1px)] [background-size:20px_20px]"
        style={{ maxHeight: "70vh", cursor: pan.current ? "grabbing" : "default", touchAction: "none" }}
        onPointerDown={startPan} onPointerMove={onMove} onPointerUp={onUp} onPointerLeave={onUp} onWheel={onWheel}>
        <div className="relative" style={{ width: maxX, height: maxY, transform: `scale(${zoom})`, transformOrigin: "top left" }}>
          <svg className="pointer-events-none absolute inset-0 h-full w-full">
            <defs>
              <marker id="arrow" markerWidth="8" markerHeight="8" refX="6" refY="3" orient="auto" markerUnits="strokeWidth">
                <path d="M0,0 L6,3 L0,6 Z" fill="#94a3b8" />
              </marker>
            </defs>
            {edges.map((e, i) => (
              <path key={i} d={`M ${e.x1} ${e.y1} C ${e.x1 + 50} ${e.y1}, ${e.x2 - 50} ${e.y2}, ${e.x2} ${e.y2}`}
                stroke="#94a3b8" strokeWidth={1.75} fill="none" markerEnd="url(#arrow)" />
            ))}
          </svg>

          {/* Nodos de Línea */}
          {tree.lines.map((line) => {
            const lp = pos[line.id]; if (!lp) return null;
            return (
              <div key={line.id} className="absolute" style={{ left: lp.x, top: lp.y, width: LINE_W }}>
                <div onPointerDown={startNodeDrag(line.id)}
                  className={`flex cursor-grab items-center gap-1.5 rounded-lg bg-violet-600 px-3 py-2 text-sm font-bold text-white shadow active:cursor-grabbing ${selected === line.id ? "ring-2 ring-violet-300" : ""}`}>
                  <GripVertical className="h-3.5 w-3.5 opacity-70" /> <Building2 className="h-4 w-4" /> {line.name}
                </div>
              </div>
            );
          })}

          {/* Nodos de Cliente (servicios externos) */}
          {tree.lines.flatMap((line) => line.services.flatMap((svc) => svc.clients.map((c) => {
            const cp = pos[clientId(svc.id, c)]; if (!cp) return null;
            return (
              <div key={clientId(svc.id, c)} className="absolute" style={{ left: cp.x, top: cp.y, width: CLIENT_W }}>
                <div onPointerDown={startNodeDrag(clientId(svc.id, c))}
                  className={`flex cursor-grab items-center gap-1.5 rounded-full border border-emerald-300 bg-emerald-50 px-3 py-1.5 text-xs font-semibold text-emerald-800 shadow-sm active:cursor-grabbing ${selected === clientId(svc.id, c) ? "ring-2 ring-emerald-300" : ""}`}>
                  <Users className="h-3.5 w-3.5" /> <span className="truncate">{c}</span>
                </div>
              </div>
            );
          })))}

          {/* Tarjetas de Servicio */}
          {tree.lines.flatMap((line) => line.services.map((svc) => {
            const sp = pos[svc.id]; if (!sp) return null;
            return (
              <div key={svc.id} className={`absolute rounded-xl border bg-white shadow-sm ${selected === svc.id ? "border-violet-400 ring-2 ring-violet-200" : "border-slate-200"}`} style={{ left: sp.x, top: sp.y, width: SVC_W }}>
                <div onPointerDown={startNodeDrag(svc.id)} className="flex cursor-grab items-center justify-between gap-2 rounded-t-xl border-b border-slate-100 bg-slate-50 px-3 py-2 active:cursor-grabbing">
                  <div className="flex items-center gap-1.5 font-semibold text-slate-800"><GripVertical className="h-3.5 w-3.5 text-slate-300" /> {svc.name}</div>
                  <span className={`rounded-full px-2 py-0.5 text-[10px] font-semibold ${svc.kind === "external" ? "bg-blue-100 text-blue-700" : "bg-purple-100 text-purple-700"}`}>{svc.kind === "external" ? "SLA" : "OLA"}</span>
                </div>
                <div className="p-2.5">
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
