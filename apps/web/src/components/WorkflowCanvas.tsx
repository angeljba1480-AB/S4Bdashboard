"use client";

import { Bell, Cpu, Database, Mail, Play, Send, Webhook, Zap } from "lucide-react";

type Step = { label: string; status: "ok" | "missing"; detail: string; link?: string | null; optional?: boolean };

// Ícono por tipo de paso (heurística por la etiqueta que devuelve /validate).
function iconFor(label: string) {
  const l = label.toLowerCase();
  if (l.includes("disparador")) return Play;
  if (l.includes("entrada")) return Database;
  if (l.includes("correo") || l.includes("caso")) return Mail;
  if (l.includes("n8n")) return Webhook;
  if (l.includes("indexado")) return Database;
  if (l.includes("modelo")) return Cpu;
  if (l.includes("salida")) return Send;
  if (l.includes("destino")) return Bell;
  return Zap;
}

function tone(s: Step): { dot: string; ring: string; text: string } {
  if (s.status === "ok") return { dot: "bg-emerald-500", ring: "border-emerald-200", text: "text-emerald-600" };
  if (s.optional) return { dot: "bg-amber-400", ring: "border-amber-200", text: "text-amber-600" };
  return { dot: "bg-red-500", ring: "border-red-200", text: "text-red-600" };
}

/** Canvas visual (read-only) del flujo de una automatización: dibuja los pasos
 * como nodos conectados. Reusa los pasos de /validate (Disparador → … → Salida). */
export function WorkflowCanvas({ steps, ready }: { steps: Step[]; ready: boolean }) {
  if (!steps?.length) return null;
  return (
    <div className="rounded-xl border border-slate-200 bg-gradient-to-br from-slate-50 to-white p-4">
      <div className="mb-3 flex items-center justify-between">
        <span className="text-xs font-semibold uppercase tracking-wide text-slate-400">Diagrama del flujo</span>
        <span className={`rounded-full px-2 py-0.5 text-xs font-semibold ${ready ? "bg-emerald-100 text-emerald-700" : "bg-amber-100 text-amber-700"}`}>
          {ready ? "Listo para ejecutar" : "Requiere atención"}
        </span>
      </div>
      <div className="flex items-stretch gap-1 overflow-x-auto pb-2">
        {steps.map((s, i) => {
          const Icon = iconFor(s.label);
          const t = tone(s);
          return (
            <div key={i} className="flex items-stretch gap-1">
              <div className={`flex w-40 shrink-0 flex-col rounded-xl border-2 ${t.ring} bg-white p-3 shadow-sm`}>
                <div className="mb-1 flex items-center gap-2">
                  <div className="flex h-7 w-7 items-center justify-center rounded-lg bg-slate-100">
                    <Icon className="h-4 w-4 text-slate-600" />
                  </div>
                  <span className={`h-2 w-2 rounded-full ${t.dot}`} />
                </div>
                <div className="text-xs font-semibold text-slate-700">{s.label}</div>
                <div className="mt-0.5 line-clamp-3 text-[11px] leading-tight text-slate-400">{s.detail}</div>
                {s.status !== "ok" && s.link && (
                  <a href={s.link} className={`mt-1 text-[11px] underline ${t.text}`}>configurar</a>
                )}
              </div>
              {i < steps.length - 1 && (
                <div className="flex items-center px-0.5 text-slate-300" aria-hidden>
                  <svg width="18" height="12" viewBox="0 0 18 12" fill="none">
                    <path d="M0 6h14M14 6l-4-4M14 6l-4 4" stroke="currentColor" strokeWidth="1.5" strokeLinecap="round" strokeLinejoin="round" />
                  </svg>
                </div>
              )}
            </div>
          );
        })}
      </div>
    </div>
  );
}
