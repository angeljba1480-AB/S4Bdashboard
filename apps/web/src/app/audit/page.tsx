"use client";

import { PageHeader, Shell } from "@/components/Shell";
import { api } from "@/lib/api";
import type { AuditEvent } from "@shared/types";
import { useEffect, useState } from "react";

export default function AuditPage() {
  const [events, setEvents] = useState<AuditEvent[]>([]);
  const [risk, setRisk] = useState("");

  function load() {
    api.audit(risk ? { risk_level: risk } : undefined).then(setEvents);
  }
  useEffect(load, [risk]);

  return (
    <Shell>
      <PageHeader
        title="Auditoría"
        subtitle="Cada llamada registra usuario, tenant, modelo, ruta, tokens, costo, sensibilidad y decisión."
      />
      <div className="p-8">
        <div className="mb-4 flex items-center gap-2">
          {["", "low", "high"].map((r) => (
            <button
              key={r || "all"}
              onClick={() => setRisk(r)}
              className={`rounded-lg px-3 py-1.5 text-sm ${
                risk === r ? "bg-violet-600 text-white" : "border border-slate-300 text-slate-600"
              }`}
            >
              {r === "" ? "Todos" : r}
            </button>
          ))}
          <button
            onClick={() => api.exportAudit()}
            className="ml-auto rounded-lg border border-slate-300 px-3 py-1.5 text-sm text-slate-600 hover:bg-slate-50"
          >
            Exportar SIEM (JSONL)
          </button>
        </div>
        <div className="overflow-hidden rounded-2xl border border-slate-200 bg-white">
          <table className="w-full text-sm">
            <thead className="border-b border-slate-200 bg-slate-50 text-xs uppercase text-slate-400">
              <tr>
                <th className="px-4 py-2.5 text-left">Evento</th>
                <th className="px-4 py-2.5 text-left">Clasificación</th>
                <th className="px-4 py-2.5 text-left">Ruta</th>
                <th className="px-4 py-2.5 text-left">Modelo</th>
                <th className="px-4 py-2.5 text-right">Tokens</th>
                <th className="px-4 py-2.5 text-right">Costo</th>
                <th className="px-4 py-2.5 text-center">Riesgo</th>
                <th className="px-4 py-2.5 text-left">Razón</th>
              </tr>
            </thead>
            <tbody>
              {events.map((e) => (
                <tr key={e.id} className="border-b border-slate-100">
                  <td className="px-4 py-2.5 font-medium uppercase text-slate-600">{e.event_type}</td>
                  <td className="px-4 py-2.5 text-slate-500">{e.classification ?? "—"}</td>
                  <td className="px-4 py-2.5 text-slate-500">{e.selected_route ?? "—"}</td>
                  <td className="px-4 py-2.5 text-slate-500">{e.selected_model || "—"}</td>
                  <td className="px-4 py-2.5 text-right tabular-nums text-slate-500">{e.token_count}</td>
                  <td className="px-4 py-2.5 text-right tabular-nums text-slate-500">${e.cost_estimate.toFixed(5)}</td>
                  <td className="px-4 py-2.5 text-center">
                    <span
                      className={`rounded-full px-2 py-0.5 text-xs ${
                        e.risk_level === "high" ? "bg-red-100 text-red-700" : "bg-slate-100 text-slate-500"
                      }`}
                    >
                      {e.risk_level}
                    </span>
                  </td>
                  <td className="px-4 py-2.5 text-xs text-slate-500">{e.reason}</td>
                </tr>
              ))}
              {events.length === 0 && (
                <tr>
                  <td colSpan={8} className="px-4 py-8 text-center text-slate-400">Sin eventos.</td>
                </tr>
              )}
            </tbody>
          </table>
        </div>
      </div>
    </Shell>
  );
}
