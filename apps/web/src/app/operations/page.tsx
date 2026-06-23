"use client";

import { PageHeader, Shell } from "@/components/Shell";
import { api } from "@/lib/api";
import { Coins, Cpu, PlayCircle, Search } from "lucide-react";
import { useEffect, useState } from "react";
import { Bar, BarChart, Cell, ResponsiveContainer, Tooltip, XAxis, YAxis } from "recharts";

type Ops = Awaited<ReturnType<typeof api.operations>>;
const COLORS = ["#7c3aed", "#0ea5e9", "#059669", "#d97706"];

export default function OperationsPage() {
  const [ops, setOps] = useState<Ops | null>(null);

  useEffect(() => {
    api.operations().then(setOps).catch(() => {});
  }, []);

  if (!ops) {
    return (
      <Shell>
        <PageHeader title="Operación" subtitle="Casos, búsquedas y tokens." />
        <div className="p-8 text-sm text-slate-400">Cargando…</div>
      </Shell>
    );
  }

  const cards = [
    { label: "Casos corriendo", value: ops.cases.total, sub: `${ops.cases.completed} completados · ${ops.cases.in_progress} en curso`, icon: PlayCircle, color: "text-violet-600" },
    { label: "Búsquedas / consultas", value: ops.searches, sub: "respuestas con fuentes", icon: Search, color: "text-blue-600" },
    { label: "Tokens quemados", value: ops.tokens.total.toLocaleString(), sub: "chat + casos + apps", icon: Cpu, color: "text-emerald-600" },
    { label: "Costo estimado (USD)", value: `$${ops.cost.total.toFixed(4)}`, sub: `${ops.apps.deployed} apps en prod`, icon: Coins, color: "text-amber-600" },
  ];

  const tokenData = Object.entries(ops.tokens.by_source).map(([name, value]) => ({ name, value }));
  const statusBadge: Record<string, string> = {
    completed: "bg-emerald-100 text-emerald-700",
    draft: "bg-amber-100 text-amber-700",
    needs_connection: "bg-blue-100 text-blue-700",
    failed: "bg-red-100 text-red-700",
  };

  return (
    <Shell>
      <PageHeader title="Operación" subtitle="Casos corriendo, búsquedas, tokens quemados y costo." />
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
                <div className="mt-1 text-xs text-slate-400">{c.sub}</div>
              </div>
            );
          })}
        </div>

        <div className="grid grid-cols-1 gap-6 lg:grid-cols-2">
          <div className="rounded-2xl border border-slate-200 bg-white p-5">
            <h2 className="mb-3 font-semibold text-slate-800">Tokens por fuente</h2>
            <ResponsiveContainer width="100%" height={220}>
              <BarChart data={tokenData}>
                <XAxis dataKey="name" tick={{ fontSize: 12 }} />
                <YAxis tick={{ fontSize: 12 }} />
                <Tooltip />
                <Bar dataKey="value" radius={[6, 6, 0, 0]}>
                  {tokenData.map((_, i) => <Cell key={i} fill={COLORS[i % COLORS.length]} />)}
                </Bar>
              </BarChart>
            </ResponsiveContainer>
          </div>

          <div className="rounded-2xl border border-slate-200 bg-white p-5">
            <h2 className="mb-3 font-semibold text-slate-800">Casos por tipo</h2>
            {Object.keys(ops.cases.by_recipe).length === 0 ? (
              <p className="text-sm text-slate-400">Aún no hay casos.</p>
            ) : (
              <div className="space-y-2">
                {Object.entries(ops.cases.by_recipe).map(([name, n]) => (
                  <div key={name} className="flex items-center justify-between text-sm">
                    <span className="text-slate-600">{name}</span>
                    <span className="font-semibold text-slate-800">{n}</span>
                  </div>
                ))}
              </div>
            )}
          </div>
        </div>

        <div className="rounded-2xl border border-slate-200 bg-white p-5">
          <h2 className="mb-3 font-semibold text-slate-800">Casos recientes</h2>
          {ops.recent_cases.length === 0 ? (
            <p className="text-sm text-slate-400">Sin casos todavía.</p>
          ) : (
            <table className="w-full text-sm">
              <thead className="border-b border-slate-200 text-xs uppercase text-slate-400">
                <tr><th className="py-2 text-left">Caso</th><th className="text-left">Estado</th><th className="text-right">Tokens</th><th className="text-right">Costo</th></tr>
              </thead>
              <tbody>
                {ops.recent_cases.map((c) => (
                  <tr key={c.id} className="border-b border-slate-100">
                    <td className="py-2 text-slate-700">{c.recipe}</td>
                    <td><span className={`rounded-full px-2 py-0.5 text-xs ${statusBadge[c.status] ?? "bg-slate-100 text-slate-500"}`}>{c.status}</span></td>
                    <td className="text-right text-slate-600">{c.tokens.toLocaleString()}</td>
                    <td className="text-right text-slate-600">${c.cost.toFixed(4)}</td>
                  </tr>
                ))}
              </tbody>
            </table>
          )}
        </div>
      </div>
    </Shell>
  );
}
