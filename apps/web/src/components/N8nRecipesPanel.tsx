"use client";

import { api } from "@/lib/api";
import { Play, Plus, Trash2, Workflow } from "lucide-react";
import { useEffect, useState } from "react";

type Recipe = { id: string; name: string; description: string; category: string; webhook_path: string; params: string[]; enabled: boolean; created_at: string };

const CATEGORIES = [
  { value: "db", label: "Base de datos" },
  { value: "soap", label: "SOAP / SOAP-XML" },
  { value: "app", label: "App propia / API" },
  { value: "custom", label: "Otra" },
];

export function N8nRecipesPanel() {
  const [recipes, setRecipes] = useState<Recipe[]>([]);
  const [form, setForm] = useState({ name: "", category: "db", webhook_path: "", description: "", params: "" });
  const [msg, setMsg] = useState("");

  function load() { api.n8nRecipes().then(setRecipes).catch(() => {}); }
  useEffect(load, []);

  async function create() {
    if (!form.name.trim() || !form.webhook_path.trim()) { setMsg("Nombre y webhook son obligatorios."); return; }
    try {
      await api.createN8nRecipe({
        name: form.name, category: form.category, webhook_path: form.webhook_path,
        description: form.description,
        params: form.params.split(",").map((p) => p.trim()).filter(Boolean),
      });
      setForm({ name: "", category: "db", webhook_path: "", description: "", params: "" });
      setMsg("Receta creada."); load();
    } catch (e) { setMsg(e instanceof Error ? e.message : "Error"); }
  }

  async function run(r: Recipe) {
    const payload: Record<string, string> = {};
    for (const p of r.params) {
      const v = window.prompt(`Valor para «${p}»:`, "");
      if (v !== null) payload[p] = v;
    }
    try {
      const res = await api.runN8nRecipe(r.id, payload);
      setMsg(`«${r.name}»: ${res.status} (${res.engine}).`);
    } catch (e) { setMsg(e instanceof Error ? e.message : "Error"); }
  }

  async function remove(id: string) {
    if (!window.confirm("¿Eliminar la receta?")) return;
    await api.deleteN8nRecipe(id); load();
  }

  return (
    <div className="rounded-2xl border border-slate-200 bg-white p-5">
      <div className="mb-1 flex items-center gap-2">
        <Workflow className="h-5 w-5 text-violet-600" />
        <h2 className="font-semibold text-slate-800">Recetas n8n a la medida</h2>
      </div>
      <p className="mb-4 text-xs text-slate-500">
        Conecta tus propios flujos de n8n (DB, SOAP, apps internas) como webhooks.
        MaestroAI los dispara con un payload y el <b>agente</b> los puede usar como herramienta.
        Apunta al webhook configurado en <b>tu</b> n8n (Integraciones → n8n).
      </p>

      {/* Crear */}
      <div className="mb-4 grid grid-cols-1 gap-2 rounded-xl border border-slate-100 bg-slate-50 p-3 sm:grid-cols-2">
        <input value={form.name} onChange={(e) => setForm({ ...form, name: e.target.value })}
          placeholder="Nombre (ej. ERP — saldo cliente)" className="rounded-lg border border-slate-300 px-3 py-2 text-sm" />
        <select value={form.category} onChange={(e) => setForm({ ...form, category: e.target.value })}
          className="rounded-lg border border-slate-300 px-3 py-2 text-sm">
          {CATEGORIES.map((c) => <option key={c.value} value={c.value}>{c.label}</option>)}
        </select>
        <input value={form.webhook_path} onChange={(e) => setForm({ ...form, webhook_path: e.target.value })}
          placeholder="Ruta del webhook (ej. erp-saldo)" className="rounded-lg border border-slate-300 px-3 py-2 text-sm" />
        <input value={form.params} onChange={(e) => setForm({ ...form, params: e.target.value })}
          placeholder="Parámetros separados por coma (ej. cliente_id)" className="rounded-lg border border-slate-300 px-3 py-2 text-sm" />
        <input value={form.description} onChange={(e) => setForm({ ...form, description: e.target.value })}
          placeholder="Descripción (la usa el agente para decidir)" className="rounded-lg border border-slate-300 px-3 py-2 text-sm sm:col-span-2" />
        <button onClick={create} className="flex items-center justify-center gap-1.5 rounded-lg bg-violet-600 px-4 py-2 text-sm font-semibold text-white sm:col-span-2">
          <Plus className="h-4 w-4" /> Crear receta
        </button>
      </div>
      {msg && <div className="mb-3 rounded-lg border border-slate-200 bg-slate-50 px-3 py-2 text-xs text-slate-600">{msg}</div>}

      {/* Lista */}
      <div className="space-y-2">
        {recipes.length === 0 && <p className="text-xs text-slate-400">Aún no hay recetas. Crea la primera arriba.</p>}
        {recipes.map((r) => (
          <div key={r.id} className="flex items-center justify-between rounded-lg border border-slate-100 px-3 py-2 text-sm">
            <span className="min-w-0">
              <span className="flex items-center gap-2">
                <span className="font-medium text-slate-700">{r.name}</span>
                <span className="rounded-full bg-slate-100 px-1.5 py-0.5 text-[10px] font-semibold text-slate-600">{r.category}</span>
              </span>
              <span className="block truncate text-xs text-slate-400">/{r.webhook_path}{r.params.length ? ` · ${r.params.join(", ")}` : ""}</span>
            </span>
            <span className="flex shrink-0 items-center gap-1.5">
              <button onClick={() => run(r)} title="Ejecutar" className="rounded-md bg-violet-600 p-1 text-white"><Play className="h-3.5 w-3.5" /></button>
              <button onClick={() => remove(r.id)} title="Eliminar" className="rounded-md border border-slate-300 p-1 text-red-500"><Trash2 className="h-3.5 w-3.5" /></button>
            </span>
          </div>
        ))}
      </div>
    </div>
  );
}
