"use client";

import { PageHeader, Shell } from "@/components/Shell";
import { api } from "@/lib/api";
import type { Agent, AuditEvent, DocumentItem, UsageSummary } from "@shared/types";
import { Bot, Coins, FileText, ShieldAlert } from "lucide-react";
import { useEffect, useState } from "react";

export default function DashboardPage() {
  const [agents, setAgents] = useState<Agent[]>([]);
  const [docs, setDocs] = useState<DocumentItem[]>([]);
  const [usage, setUsage] = useState<UsageSummary | null>(null);
  const [audit, setAudit] = useState<AuditEvent[]>([]);

  useEffect(() => {
    api.agents().then(setAgents).catch(() => {});
    api.documents().then(setDocs).catch(() => {});
    api.usage().then(setUsage).catch(() => {});
    api.audit().then(setAudit).catch(() => {});
  }, []);

  const highRisk = audit.filter((a) => a.risk_level === "high").length;

  const cards = [
    { label: "Agentes activos", value: agents.length, icon: Bot, color: "text-violet-600" },
    { label: "Documentos", value: docs.length, icon: FileText, color: "text-blue-600" },
    {
      label: "Costo estimado",
      value: `$${(usage?.total_cost ?? 0).toFixed(4)}`,
      icon: Coins,
      color: "text-amber-600",
    },
    { label: "Eventos de riesgo", value: highRisk, icon: ShieldAlert, color: "text-red-600" },
  ];

  return (
    <Shell>
      <PageHeader title="Resumen ejecutivo" subtitle="Uso, costo, riesgos y documentos procesados." />
      <div className="space-y-6 p-8">
        <div className="grid grid-cols-1 gap-4 sm:grid-cols-2 lg:grid-cols-4">
          {cards.map((c) => {
            const Icon = c.icon;
            return (
              <div key={c.label} className="rounded-2xl border border-slate-200 bg-white p-5">
                <div className="flex items-center justify-between">
                  <span className="text-sm text-slate-500">{c.label}</span>
                  <Icon className={`h-5 w-5 ${c.color}`} />
                </div>
                <div className="mt-2 text-3xl font-bold text-slate-900">{c.value}</div>
              </div>
            );
          })}
        </div>

        <div className="grid grid-cols-1 gap-6 lg:grid-cols-2">
          <div className="rounded-2xl border border-slate-200 bg-white p-5">
            <h2 className="mb-3 font-semibold text-slate-800">Costo por ruta de privacidad</h2>
            {usage && Object.keys(usage.by_route).length > 0 ? (
              <div className="space-y-2">
                {Object.entries(usage.by_route).map(([route, cost]) => (
                  <div key={route} className="flex items-center justify-between text-sm">
                    <span className="capitalize text-slate-600">{route}</span>
                    <span className="font-medium text-slate-800">${cost.toFixed(5)}</span>
                  </div>
                ))}
              </div>
            ) : (
              <p className="text-sm text-slate-400">Sin uso registrado todavía. Prueba el chat.</p>
            )}
          </div>

          <div className="rounded-2xl border border-slate-200 bg-white p-5">
            <h2 className="mb-3 font-semibold text-slate-800">Actividad reciente (auditoría)</h2>
            <div className="space-y-2">
              {audit.slice(0, 6).map((a) => (
                <div key={a.id} className="flex items-center justify-between text-sm">
                  <span className="truncate text-slate-600">
                    <span className="font-medium uppercase text-slate-400">{a.event_type}</span> · {a.reason}
                  </span>
                  <span
                    className={`ml-2 shrink-0 rounded-full px-2 py-0.5 text-xs ${
                      a.risk_level === "high"
                        ? "bg-red-100 text-red-700"
                        : "bg-slate-100 text-slate-500"
                    }`}
                  >
                    {a.risk_level}
                  </span>
                </div>
              ))}
              {audit.length === 0 && <p className="text-sm text-slate-400">Sin eventos.</p>}
            </div>
          </div>
        </div>
      </div>
    </Shell>
  );
}
