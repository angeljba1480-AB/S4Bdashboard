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
  const [catalog, setCatalog] = useState<{ key: string; type: string; title: string }[]>([]);
  const [addKey, setAddKey] = useState("");
  const [manual, setManual] = useState({ title: "", value: "" });
  const [workflows, setWorkflows] = useState<{ id: string; name: string }[]>([]);
  const [autoMsg, setAutoMsg] = useState("");

  function load() {
    api.dashboards().then(setList).catch(() => {});
  }
  useEffect(() => {
    load();
    api.dashboardCatalog().then(setCatalog).catch(() => {});
    api.workflows().then(setWorkflows).catch(() => {});
  }, []);

  async function linkWorkflow(id: string) {
    if (!active) return;
    await api.updateDashboard(active.id, { name: active.name, description: "", spec: currentSpec(), workflow_id: id });
    await open(active.id);
  }

  async function runAutomation() {
    if (!active?.workflow_id) return;
    setAutoMsg("Ejecutando…");
    const res = await api.runWorkflow(active.workflow_id);
    setAutoMsg(`Automatización: ${res.status} · ${res.engine}`);
  }

  function currentSpec() {
    return (active?.widgets ?? []).map((w) => {
      const base: Record<string, unknown> = { id: w.id, type: w.type, title: w.title, source: w.source ?? "platform", key: w.key };
      if (w.source === "manual") {
        if (w.value !== undefined) base.value = w.value;
        if (w.rows) base.rows = w.rows;
      }
      return base;
    });
  }

  async function addWidget() {
    if (!active || !addKey) return;
    const c = catalog.find((w) => w.key === addKey);
    if (!c) return;
    const spec = [...currentSpec(), { id: `w${Date.now()}`, type: c.type, title: c.title, source: "platform", key: c.key }];
    await api.updateDashboard(active.id, { name: active.name, description: "", spec });
    setAddKey("");
    await open(active.id);
  }

  async function addManual() {
    if (!active || !manual.title.trim()) return;
    const spec = [...currentSpec(), { id: `m${Date.now()}`, type: "kpi", title: manual.title, source: "manual", value: Number(manual.value) || 0 }];
    await api.updateDashboard(active.id, { name: active.name, description: "", spec });
    setManual({ title: "", value: "" });
    await open(active.id);
  }

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
            <div className="mb-3 flex flex-wrap items-center justify-between gap-2">
              <h2 className="text-lg font-bold text-slate-900">{active.name}</h2>
              <div className="flex flex-wrap items-center gap-2">
                <select value={addKey} onChange={(e) => setAddKey(e.target.value)}
                  className="rounded-lg border border-slate-300 px-2 py-1.5 text-xs">
                  <option value="">+ Widget de datos…</option>
                  {catalog.map((c) => <option key={c.key} value={c.key}>{c.title}</option>)}
                </select>
                <button onClick={addWidget} disabled={!addKey}
                  className="rounded-lg bg-slate-900 px-3 py-1.5 text-xs font-semibold text-white disabled:opacity-40">Agregar</button>
                <span className="text-slate-300">|</span>
                <input value={manual.title} onChange={(e) => setManual((m) => ({ ...m, title: e.target.value }))}
                  placeholder="KPI propio" className="w-28 rounded-lg border border-slate-300 px-2 py-1.5 text-xs" />
                <input value={manual.value} onChange={(e) => setManual((m) => ({ ...m, value: e.target.value }))}
                  placeholder="valor" className="w-20 rounded-lg border border-slate-300 px-2 py-1.5 text-xs" />
                <button onClick={addManual} className="rounded-lg border border-slate-300 px-3 py-1.5 text-xs font-semibold text-slate-700">+ Manual</button>
              </div>
            </div>

            <div className="mb-4 flex flex-wrap items-center gap-2 rounded-xl border border-slate-200 bg-white p-3">
              <span className="text-sm font-medium text-slate-600">Automatización:</span>
              <select value={active.workflow_id ?? ""} onChange={(e) => linkWorkflow(e.target.value)}
                className="rounded-lg border border-slate-300 px-2 py-1.5 text-xs">
                <option value="">Sin workflow</option>
                {workflows.map((w) => <option key={w.id} value={w.id}>{w.name}</option>)}
              </select>
              <button onClick={runAutomation} disabled={!active.workflow_id}
                className="rounded-lg bg-emerald-600 px-3 py-1.5 text-xs font-semibold text-white disabled:opacity-40">
                Ejecutar automatización
              </button>
              {autoMsg && <span className="text-xs text-slate-500">{autoMsg}</span>}
            </div>
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
