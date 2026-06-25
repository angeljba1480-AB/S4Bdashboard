"use client";

import { PageHeader, Shell } from "@/components/Shell";
import { api } from "@/lib/api";
import type { AuditEvent } from "@shared/types";
import { AlertTriangle, Ban, Coins, Download, ListFilter, ScrollText } from "lucide-react";
import { Fragment, useCallback, useEffect, useState } from "react";

const PAGE = 50;
const EMPTY = { event_type: "", risk_level: "", classification: "", route: "", user_id: "", q: "" };

export default function AuditPage() {
  const [events, setEvents] = useState<AuditEvent[]>([]);
  const [stats, setStats] = useState<Awaited<ReturnType<typeof api.auditStats>> | null>(null);
  const [filters, setFilters] = useState({ ...EMPTY });
  const [offset, setOffset] = useState(0);
  const [more, setMore] = useState(false);
  const [open, setOpen] = useState<string | null>(null);

  const load = useCallback((reset: boolean) => {
    const off = reset ? 0 : offset;
    api.audit({ ...filters, limit: PAGE, offset: off }).then((rows) => {
      setEvents((prev) => (reset ? rows : [...prev, ...rows]));
      setMore(rows.length === PAGE);
      setOffset(off + rows.length);
    });
  }, [filters, offset]);

  useEffect(() => { load(true); /* eslint-disable-next-line */ }, [filters]);
  useEffect(() => { api.auditStats().then(setStats).catch(() => {}); }, []);

  const set = (k: keyof typeof EMPTY, v: string) => setFilters((f) => ({ ...f, [k]: v }));
  const sel = "rounded-lg border border-slate-300 px-2.5 py-1.5 text-sm";

  const cards = stats ? [
    { label: "Eventos", value: stats.total, icon: ScrollText, color: "text-slate-600" },
    { label: "Riesgo alto", value: stats.high_risk, icon: AlertTriangle, color: "text-red-600" },
    { label: "Bloqueados", value: stats.blocked, icon: Ban, color: "text-amber-600" },
    { label: "Costo total", value: `$${stats.total_cost.toFixed(4)}`, icon: Coins, color: "text-emerald-600" },
  ] : [];

  return (
    <Shell>
      <PageHeader title="Auditoría" subtitle="Cada llamada registra usuario, modelo, ruta, tokens, costo, sensibilidad y decisión." />
      <div className="space-y-5 p-8">
        {/* Stats */}
        <div className="grid grid-cols-2 gap-4 lg:grid-cols-4">
          {cards.map((c) => {
            const Icon = c.icon;
            return (
              <div key={c.label} className="rounded-2xl border border-slate-200 bg-white p-4">
                <div className="flex items-center justify-between">
                  <span className="text-sm text-slate-500">{c.label}</span>
                  <Icon className={`h-5 w-5 ${c.color}`} />
                </div>
                <div className="mt-1 text-2xl font-bold text-slate-900">{c.value}</div>
              </div>
            );
          })}
        </div>

        {/* Filters */}
        <div className="flex flex-wrap items-center gap-2 rounded-2xl border border-slate-200 bg-white p-3">
          <ListFilter className="h-4 w-4 text-slate-400" />
          <input value={filters.q} onChange={(e) => set("q", e.target.value)} placeholder="Buscar en la razón…"
            className={`${sel} min-w-48 flex-1`} />
          <select value={filters.event_type} onChange={(e) => set("event_type", e.target.value)} className={sel}>
            <option value="">Todo evento</option>
            {(stats?.event_types || []).map((t) => <option key={t} value={t}>{t}</option>)}
          </select>
          <select value={filters.risk_level} onChange={(e) => set("risk_level", e.target.value)} className={sel}>
            <option value="">Todo riesgo</option>
            <option value="low">low</option><option value="med">med</option><option value="high">high</option>
          </select>
          <select value={filters.classification} onChange={(e) => set("classification", e.target.value)} className={sel}>
            <option value="">Toda sensibilidad</option>
            {["public", "internal", "confidential", "restricted"].map((c) => <option key={c} value={c}>{c}</option>)}
          </select>
          <select value={filters.route} onChange={(e) => set("route", e.target.value)} className={sel}>
            <option value="">Toda ruta</option>
            {["local", "vpc", "open", "premium", "blocked"].map((r) => <option key={r} value={r}>{r}</option>)}
          </select>
          {(filters.q || filters.event_type || filters.risk_level || filters.classification || filters.route) && (
            <button onClick={() => setFilters({ ...EMPTY })} className="text-xs font-semibold text-violet-700">Limpiar</button>
          )}
          <button onClick={() => api.exportAudit()}
            className="ml-auto flex items-center gap-1.5 rounded-lg border border-slate-300 px-3 py-1.5 text-sm text-slate-600 hover:bg-slate-50">
            <Download className="h-4 w-4" /> Exportar SIEM
          </button>
        </div>

        {/* Table */}
        <div className="overflow-hidden rounded-2xl border border-slate-200 bg-white">
          <table className="w-full text-sm">
            <thead className="border-b border-slate-200 bg-slate-50 text-xs uppercase text-slate-400">
              <tr>
                <th className="px-4 py-2.5 text-left">Fecha</th>
                <th className="px-4 py-2.5 text-left">Evento</th>
                <th className="px-4 py-2.5 text-left">Sensibilidad</th>
                <th className="px-4 py-2.5 text-left">Ruta</th>
                <th className="px-4 py-2.5 text-right">Tokens</th>
                <th className="px-4 py-2.5 text-right">Costo</th>
                <th className="px-4 py-2.5 text-center">Riesgo</th>
              </tr>
            </thead>
            <tbody>
              {events.map((e) => (
                <Fragment key={e.id}>
                  <tr onClick={() => setOpen(open === e.id ? null : e.id)}
                    className="cursor-pointer border-b border-slate-100 hover:bg-slate-50">
                    <td className="px-4 py-2.5 text-xs text-slate-400">{new Date(e.created_at).toLocaleString()}</td>
                    <td className="px-4 py-2.5 font-medium uppercase text-slate-600">{e.event_type}</td>
                    <td className="px-4 py-2.5 text-slate-500">{e.classification ?? "—"}</td>
                    <td className="px-4 py-2.5 text-slate-500">{e.selected_route ?? "—"}</td>
                    <td className="px-4 py-2.5 text-right tabular-nums text-slate-500">{e.token_count}</td>
                    <td className="px-4 py-2.5 text-right tabular-nums text-slate-500">${e.cost_estimate.toFixed(5)}</td>
                    <td className="px-4 py-2.5 text-center">
                      <span className={`rounded-full px-2 py-0.5 text-xs ${e.risk_level === "high" ? "bg-red-100 text-red-700" : e.risk_level === "med" ? "bg-amber-100 text-amber-700" : "bg-slate-100 text-slate-500"}`}>
                        {e.risk_level}
                      </span>
                    </td>
                  </tr>
                  {open === e.id && (
                    <tr className="border-b border-slate-100 bg-slate-50">
                      <td colSpan={7} className="px-4 py-3 text-xs text-slate-600">
                        <div className="grid grid-cols-2 gap-x-6 gap-y-1 sm:grid-cols-3">
                          <div><span className="text-slate-400">Razón:</span> {e.reason || "—"}</div>
                          <div><span className="text-slate-400">Modelo:</span> {e.selected_model || "—"}</div>
                          <div><span className="text-slate-400">Objeto:</span> {e.object_type}/{e.object_id || "—"}</div>
                          <div><span className="text-slate-400">Usuario:</span> {e.user_id || "—"}</div>
                          <div><span className="text-slate-400">Request:</span> {e.request_id || "—"}</div>
                          {e.event_metadata && <div className="col-span-2 sm:col-span-3"><span className="text-slate-400">Metadata:</span> {e.event_metadata}</div>}
                        </div>
                      </td>
                    </tr>
                  )}
                </Fragment>
              ))}
              {events.length === 0 && (
                <tr><td colSpan={7} className="px-4 py-8 text-center text-slate-400">Sin eventos con esos filtros.</td></tr>
              )}
            </tbody>
          </table>
        </div>
        {more && (
          <div className="text-center">
            <button onClick={() => load(false)} className="rounded-lg border border-slate-300 px-4 py-2 text-sm font-semibold text-slate-600 hover:bg-slate-50">
              Cargar más
            </button>
          </div>
        )}
      </div>
    </Shell>
  );
}
