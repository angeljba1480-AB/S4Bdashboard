"use client";

import { PageHeader, Shell } from "@/components/Shell";
import { api } from "@/lib/api";
import type { Agent, AuditEvent, CompanyProfile, DocumentItem, UsageSummary } from "@shared/types";
import { Bot, Building2, Coins, FileText, Layers, ShieldAlert, Sparkles } from "lucide-react";
import Link from "next/link";
import { useEffect, useState } from "react";

const SENS_LABEL: Record<string, string> = { public: "Público", internal: "Interno", confidential: "Confidencial", restricted: "Restringido" };
const SENS_COLOR: Record<string, string> = { public: "bg-slate-400", internal: "bg-sky-500", confidential: "bg-amber-500", restricted: "bg-red-500" };

export default function DashboardPage() {
  const [agents, setAgents] = useState<Agent[]>([]);
  const [docs, setDocs] = useState<DocumentItem[]>([]);
  const [usage, setUsage] = useState<UsageSummary | null>(null);
  const [ops, setOps] = useState<Awaited<ReturnType<typeof api.operations>> | null>(null);
  const [stats, setStats] = useState<Awaited<ReturnType<typeof api.auditStats>> | null>(null);
  const [audit, setAudit] = useState<AuditEvent[]>([]);
  const [profile, setProfile] = useState<CompanyProfile | null>(null);

  useEffect(() => {
    api.agents().then(setAgents).catch(() => {});
    api.documents().then(setDocs).catch(() => {});
    api.usage().then(setUsage).catch(() => {});
    api.operations().then(setOps).catch(() => {});
    api.auditStats().then(setStats).catch(() => {});
    api.audit({ limit: 8 }).then(setAudit).catch(() => {});
    api.companyProfile().then(setProfile).catch(() => {});
  }, []);

  const sensCounts = docs.reduce<Record<string, number>>((acc, d) => {
    acc[d.sensitivity] = (acc[d.sensitivity] || 0) + 1; return acc;
  }, {});
  const maxEvent = Math.max(1, ...Object.values(stats?.by_event || {}));

  const cards = [
    { label: "Agentes", value: agents.length, icon: Bot, color: "text-violet-600" },
    { label: "Documentos", value: docs.length, icon: FileText, color: "text-blue-600" },
    { label: "Casos ejecutados", value: ops?.cases.total ?? 0, icon: Layers, color: "text-indigo-600" },
    { label: "Costo total", value: `$${(ops?.cost.total ?? usage?.total_cost ?? 0).toFixed(4)}`, icon: Coins, color: "text-emerald-600" },
    { label: "Riesgo alto", value: stats?.high_risk ?? 0, icon: ShieldAlert, color: "text-red-600" },
  ];

  return (
    <Shell>
      <PageHeader title="Resumen ejecutivo" subtitle="Uso, costo, privacidad, riesgos y documentos — en un vistazo." />
      <div className="space-y-6 p-8">
        {profile && profile.required_complete === false && (
          <Link href="/company" className="flex items-center gap-3 rounded-2xl border border-amber-300 bg-amber-50 p-4 hover:border-amber-400">
            <Building2 className="h-5 w-5 text-amber-600" />
            <div className="text-sm text-amber-800">
              <b>Completa la información base de tu empresa</b> para habilitar los casos de uso. Falta: {(profile.missing_required || []).join(", ")}. →
            </div>
          </Link>
        )}

        {/* KPI cards */}
        <div className="grid grid-cols-2 gap-4 lg:grid-cols-5">
          {cards.map((c) => {
            const Icon = c.icon;
            return (
              <div key={c.label} className="rounded-2xl border border-slate-200 bg-white p-5">
                <div className="flex items-center justify-between">
                  <span className="text-sm text-slate-500">{c.label}</span>
                  <Icon className={`h-5 w-5 ${c.color}`} />
                </div>
                <div className="mt-2 text-2xl font-bold text-slate-900">{c.value}</div>
              </div>
            );
          })}
        </div>

        <div className="grid grid-cols-1 gap-6 lg:grid-cols-3">
          {/* Cost by route */}
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
            ) : <p className="text-sm text-slate-400">Sin uso aún. Prueba el chat o un caso.</p>}
          </div>

          {/* Document sensitivity */}
          <div className="rounded-2xl border border-slate-200 bg-white p-5">
            <h2 className="mb-3 font-semibold text-slate-800">Sensibilidad de documentos</h2>
            {docs.length > 0 ? (
              <div className="space-y-2">
                {["restricted", "confidential", "internal", "public"].filter((s) => sensCounts[s]).map((s) => (
                  <div key={s}>
                    <div className="mb-0.5 flex justify-between text-xs text-slate-500">
                      <span>{SENS_LABEL[s]}</span><span>{sensCounts[s]}</span>
                    </div>
                    <div className="h-2 overflow-hidden rounded-full bg-slate-100">
                      <div className={`h-full ${SENS_COLOR[s]}`} style={{ width: `${(sensCounts[s] / docs.length) * 100}%` }} />
                    </div>
                  </div>
                ))}
              </div>
            ) : <p className="text-sm text-slate-400">Sin documentos.</p>}
          </div>

          {/* Audit events by type */}
          <div className="rounded-2xl border border-slate-200 bg-white p-5">
            <h2 className="mb-3 font-semibold text-slate-800">Eventos por tipo</h2>
            {stats && Object.keys(stats.by_event).length > 0 ? (
              <div className="space-y-2">
                {Object.entries(stats.by_event).slice(0, 6).map(([ev, n]) => (
                  <div key={ev}>
                    <div className="mb-0.5 flex justify-between text-xs text-slate-500"><span className="uppercase">{ev}</span><span>{n}</span></div>
                    <div className="h-2 overflow-hidden rounded-full bg-slate-100">
                      <div className="h-full bg-violet-500" style={{ width: `${(n / maxEvent) * 100}%` }} />
                    </div>
                  </div>
                ))}
              </div>
            ) : <p className="text-sm text-slate-400">Sin actividad registrada.</p>}
          </div>
        </div>

        <div className="grid grid-cols-1 gap-6 lg:grid-cols-2">
          {/* Recent cases */}
          <div className="rounded-2xl border border-slate-200 bg-white p-5">
            <div className="mb-3 flex items-center justify-between">
              <h2 className="font-semibold text-slate-800">Casos recientes</h2>
              <Link href="/recipes" className="flex items-center gap-1 text-xs font-semibold text-violet-700"><Sparkles className="h-3.5 w-3.5" /> Nuevo caso</Link>
            </div>
            <div className="space-y-2">
              {(ops?.recent_cases || []).slice(0, 6).map((r) => (
                <div key={r.id} className="flex items-center justify-between text-sm">
                  <span className="truncate text-slate-600">{r.recipe}</span>
                  <span className={`ml-2 shrink-0 rounded-full px-2 py-0.5 text-xs ${r.status === "completed" ? "bg-emerald-100 text-emerald-700" : "bg-slate-100 text-slate-500"}`}>{r.status}</span>
                </div>
              ))}
              {(!ops || ops.recent_cases.length === 0) && <p className="text-sm text-slate-400">Sin casos ejecutados.</p>}
            </div>
          </div>

          {/* Recent audit */}
          <div className="rounded-2xl border border-slate-200 bg-white p-5">
            <div className="mb-3 flex items-center justify-between">
              <h2 className="font-semibold text-slate-800">Actividad reciente</h2>
              <Link href="/audit" className="text-xs font-semibold text-violet-700">Ver auditoría →</Link>
            </div>
            <div className="space-y-2">
              {audit.slice(0, 6).map((a) => (
                <div key={a.id} className="flex items-center justify-between text-sm">
                  <span className="truncate text-slate-600"><span className="font-medium uppercase text-slate-400">{a.event_type}</span> · {a.reason}</span>
                  <span className={`ml-2 shrink-0 rounded-full px-2 py-0.5 text-xs ${a.risk_level === "high" ? "bg-red-100 text-red-700" : "bg-slate-100 text-slate-500"}`}>{a.risk_level}</span>
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
