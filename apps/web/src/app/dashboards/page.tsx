"use client";

import { PageHeader, Shell } from "@/components/Shell";
import { api } from "@/lib/api";
import { LayoutGrid, Plus, Trash2 } from "lucide-react";
import { useEffect, useState } from "react";
import { Bar, BarChart, Cell, ResponsiveContainer, Tooltip, XAxis, YAxis } from "recharts";

type DashData = Awaited<ReturnType<typeof api.dashboardData>>;
const COLORS = ["#7c3aed", "#0ea5e9", "#059669", "#d97706", "#db2777"];

export default function DashboardsPage() {
  const [list, setList] = useState<{ id: string; name: string; description: string }[]>([]);
  const [active, setActive] = useState<DashData | null>(null);
  const [name, setName] = useState("");
  const [description, setDescription] = useState("");
  const [busy, setBusy] = useState(false);

  function load() {
    api.dashboards().then(setList).catch(() => {});
  }
  useEffect(load, []);

  async function open(id: string) {
    setActive(await api.dashboardData(id));
  }

  async function create() {
    if (!name.trim()) return;
    setBusy(true);
    try {
      const d = await api.createDashboard({ name, description });
      setName("");
      setDescription("");
      load();
      await open(d.id);
    } finally {
      setBusy(false);
    }
  }

  async function remove(id: string) {
    await api.deleteDashboard(id);
    if (active?.id === id) setActive(null);
    load();
  }

  return (
    <Shell>
      <PageHeader
        title="Tableros"
        subtitle="Describe qué quieres medir y la plataforma arma tu tablero con datos reales."
      />
      <div className="space-y-6 p-8">
        {/* Builder */}
        <div className="rounded-2xl border border-slate-200 bg-white p-5">
          <h2 className="mb-3 font-semibold text-slate-800">Nuevo tablero</h2>
          <div className="flex flex-wrap gap-2">
            <input value={name} onChange={(e) => setName(e.target.value)}
              placeholder="Nombre (ej. Operación comercial)"
              className="w-56 rounded-lg border border-slate-300 px-3 py-2 text-sm" />
            <input value={description} onChange={(e) => setDescription(e.target.value)}
              placeholder="¿Qué quieres medir? (costos, casos, tokens, consultas…)"
              className="flex-1 rounded-lg border border-slate-300 px-3 py-2 text-sm" />
            <button onClick={create} disabled={busy}
              className="inline-flex items-center gap-1.5 rounded-lg bg-violet-600 px-4 py-2 text-sm font-semibold text-white disabled:opacity-50">
              <Plus className="h-4 w-4" /> {busy ? "Armando…" : "Armar tablero"}
            </button>
          </div>
        </div>

        {/* Saved list */}
        {list.length > 0 && (
          <div className="flex flex-wrap gap-2">
            {list.map((d) => (
              <div key={d.id} className={`flex items-center gap-2 rounded-full border px-3 py-1 text-sm ${active?.id === d.id ? "border-violet-400 bg-violet-50 text-violet-700" : "border-slate-200 bg-white text-slate-600"}`}>
                <button onClick={() => open(d.id)} className="flex items-center gap-1.5">
                  <LayoutGrid className="h-3.5 w-3.5" /> {d.name}
                </button>
                <button onClick={() => remove(d.id)} className="text-slate-400 hover:text-red-600">
                  <Trash2 className="h-3.5 w-3.5" />
                </button>
              </div>
            ))}
          </div>
        )}

        {/* Active dashboard */}
        {active && (
          <div>
            <h2 className="mb-3 text-lg font-bold text-slate-900">{active.name}</h2>
            <div className="grid grid-cols-1 gap-4 sm:grid-cols-2 lg:grid-cols-4">
              {active.widgets.filter((w) => w.type === "kpi").map((w) => (
                <div key={w.id} className="rounded-2xl border border-slate-200 bg-white p-5">
                  <div className="text-sm text-slate-500">{w.title}</div>
                  <div className="mt-2 text-3xl font-bold text-slate-900">
                    {typeof w.value === "number" && w.title.toLowerCase().includes("costo") ? `$${w.value.toFixed(4)}` : (w.value ?? 0).toLocaleString?.() ?? w.value}
                  </div>
                </div>
              ))}
            </div>

            <div className="mt-4 grid grid-cols-1 gap-4 lg:grid-cols-2">
              {active.widgets.filter((w) => w.type === "bar").map((w) => (
                <div key={w.id} className="rounded-2xl border border-slate-200 bg-white p-5">
                  <h3 className="mb-3 font-semibold text-slate-800">{w.title}</h3>
                  {(w.series ?? []).length === 0 ? (
                    <p className="text-sm text-slate-400">Sin datos aún.</p>
                  ) : (
                    <ResponsiveContainer width="100%" height={220}>
                      <BarChart data={w.series}>
                        <XAxis dataKey="name" tick={{ fontSize: 11 }} />
                        <YAxis tick={{ fontSize: 11 }} />
                        <Tooltip />
                        <Bar dataKey="value" radius={[6, 6, 0, 0]}>
                          {(w.series ?? []).map((_, i) => <Cell key={i} fill={COLORS[i % COLORS.length]} />)}
                        </Bar>
                      </BarChart>
                    </ResponsiveContainer>
                  )}
                </div>
              ))}
            </div>

            {active.widgets.filter((w) => w.type === "table").map((w) => (
              <div key={w.id} className="mt-4 rounded-2xl border border-slate-200 bg-white p-5">
                <h3 className="mb-3 font-semibold text-slate-800">{w.title}</h3>
                {(w.rows ?? []).length === 0 ? (
                  <p className="text-sm text-slate-400">Sin registros.</p>
                ) : (
                  <table className="w-full text-sm">
                    <thead className="border-b border-slate-200 text-xs uppercase text-slate-400">
                      <tr>{Object.keys((w.rows ?? [])[0] ?? {}).map((k) => <th key={k} className="py-2 text-left">{k}</th>)}</tr>
                    </thead>
                    <tbody>
                      {(w.rows ?? []).slice(0, 10).map((row, i) => (
                        <tr key={i} className="border-b border-slate-100">
                          {Object.values(row).map((v, j) => <td key={j} className="py-2 text-slate-600">{String(v)}</td>)}
                        </tr>
                      ))}
                    </tbody>
                  </table>
                )}
              </div>
            ))}
          </div>
        )}
      </div>
    </Shell>
  );
}
