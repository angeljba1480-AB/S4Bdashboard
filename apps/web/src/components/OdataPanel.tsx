"use client";

import { api } from "@/lib/api";
import { Database, Download, Plus, TestTube, Trash2 } from "lucide-react";
import { useEffect, useState } from "react";

type Odata = { id: string; name: string; base_url: string; auth_type: string; username: string; odata_filter: string; select: string; top: number; area: string; category: string };

export function OdataPanel() {
  const [items, setItems] = useState<Odata[]>([]);
  const [form, setForm] = useState({ name: "", base_url: "", auth_type: "basic", username: "", secret: "", odata_filter: "", select: "", area: "", category: "" });
  const [msg, setMsg] = useState("");
  const [confirmId, setConfirmId] = useState("");

  function load() { api.odataSources().then(setItems).catch(() => {}); }
  useEffect(load, []);

  async function create() {
    if (!form.name.trim() || !form.base_url.trim()) { setMsg("Nombre y URL del Entity Set son obligatorios."); return; }
    try {
      await api.createOdata(form);
      setForm({ name: "", base_url: "", auth_type: "basic", username: "", secret: "", odata_filter: "", select: "", area: "", category: "" });
      setMsg("Fuente OData creada."); load();
    } catch (e) { setMsg(e instanceof Error ? e.message : "Error"); }
  }

  async function test(o: Odata) {
    setMsg(`Probando ${o.name}…`);
    try {
      const r = await api.testOdata(o.id);
      setMsg(`${o.name}: OK — ${r.total_preview} fila(s) de muestra · columnas: ${r.columns.slice(0, 6).join(", ")}`);
    } catch (e) { setMsg(e instanceof Error ? e.message : "Error"); }
  }

  async function importNow(o: Odata) {
    setMsg(`Importando de ${o.name}…`);
    try {
      const r = await api.importOdata(o.id);
      setMsg(`${o.name}: ${r.rows} fila(s) importadas al RAG (${r.filename}).`);
    } catch (e) { setMsg(e instanceof Error ? e.message : "Error"); }
  }

  async function remove(id: string) {
    if (confirmId !== id) { setConfirmId(id); return; }
    await api.deleteOdata(id); setConfirmId(""); load();
  }

  return (
    <div className="rounded-2xl border border-slate-200 bg-white p-5">
      <div className="mb-1 flex items-center gap-2">
        <Database className="h-5 w-5 text-violet-600" />
        <h2 className="font-semibold text-slate-800">Conector OData (SAP S/4HANA)</h2>
      </div>
      <p className="mb-4 text-xs text-slate-500">
        Lee de un <b>Entity Set OData</b> de solo lectura (SAP S/4HANA y compatibles) y lo importa al
        repositorio + RAG (clasificado y cifrado). Soporta OData v2/v4, auth Basic o Bearer y paginación.
        Las lecturas no requieren X-CSRF-Token.
      </p>

      <div className="mb-4 grid grid-cols-1 gap-2 rounded-xl border border-slate-100 bg-slate-50 p-3 sm:grid-cols-2">
        <input value={form.name} onChange={(e) => setForm({ ...form, name: e.target.value })}
          placeholder="Nombre (ej. SAP Ventas)" className="rounded-lg border border-slate-300 px-3 py-2 text-sm" />
        <input value={form.base_url} onChange={(e) => setForm({ ...form, base_url: e.target.value })}
          placeholder="URL del Entity Set (…/sap/opu/odata/sap/SRV/Set)" className="rounded-lg border border-slate-300 px-3 py-2 text-sm" />
        <select value={form.auth_type} onChange={(e) => setForm({ ...form, auth_type: e.target.value })}
          className="rounded-lg border border-slate-300 px-3 py-2 text-sm">
          <option value="basic">Auth: Basic (usuario/clave)</option>
          <option value="bearer">Auth: Bearer (token)</option>
        </select>
        <input value={form.username} onChange={(e) => setForm({ ...form, username: e.target.value })}
          placeholder={form.auth_type === "bearer" ? "(no aplica)" : "Usuario SAP"} disabled={form.auth_type === "bearer"}
          className="rounded-lg border border-slate-300 px-3 py-2 text-sm disabled:bg-slate-100" />
        <input type="password" value={form.secret} onChange={(e) => setForm({ ...form, secret: e.target.value })}
          placeholder={form.auth_type === "bearer" ? "Token Bearer" : "Contraseña"} className="rounded-lg border border-slate-300 px-3 py-2 text-sm" />
        <input value={form.odata_filter} onChange={(e) => setForm({ ...form, odata_filter: e.target.value })}
          placeholder="$filter (ej. Anio eq 2025) — opcional" className="rounded-lg border border-slate-300 px-3 py-2 text-sm" />
        <input value={form.select} onChange={(e) => setForm({ ...form, select: e.target.value })}
          placeholder="$select (campos, opcional)" className="rounded-lg border border-slate-300 px-3 py-2 text-sm" />
        <input value={form.area} onChange={(e) => setForm({ ...form, area: e.target.value })}
          placeholder="Área (ej. Finanzas) — opcional" className="rounded-lg border border-slate-300 px-3 py-2 text-sm" />
        <button onClick={create} className="flex items-center justify-center gap-1.5 rounded-lg bg-violet-600 px-4 py-2 text-sm font-semibold text-white sm:col-span-2">
          <Plus className="h-4 w-4" /> Crear fuente OData
        </button>
      </div>
      {msg && <div className="mb-3 rounded-lg border border-slate-200 bg-slate-50 px-3 py-2 text-xs text-slate-600">{msg}</div>}

      <div className="space-y-2">
        {items.length === 0 && <p className="text-xs text-slate-400">Aún no hay fuentes OData.</p>}
        {items.map((o) => (
          <div key={o.id} className="flex items-center justify-between rounded-lg border border-slate-100 px-3 py-2 text-sm">
            <span className="min-w-0">
              <span className="font-medium text-slate-700">{o.name}</span>
              <span className="block truncate text-xs text-slate-400">{o.base_url} · {o.auth_type}{o.odata_filter ? ` · ${o.odata_filter}` : ""}</span>
            </span>
            <span className="flex shrink-0 items-center gap-1.5">
              <button onClick={() => test(o)} title="Probar conexión" className="rounded-md border border-slate-300 p-1 text-slate-500"><TestTube className="h-3.5 w-3.5" /></button>
              <button onClick={() => importNow(o)} title="Importar al RAG" className="rounded-md bg-violet-600 p-1 text-white"><Download className="h-3.5 w-3.5" /></button>
              <button onClick={() => remove(o.id)} title={confirmId === o.id ? "Clic otra vez para confirmar" : "Eliminar"}
                className={`rounded-md border p-1 ${confirmId === o.id ? "border-red-400 bg-red-50 text-red-600" : "border-slate-300 text-red-500"}`}>
                <Trash2 className="h-3.5 w-3.5" />
              </button>
            </span>
          </div>
        ))}
      </div>
    </div>
  );
}
