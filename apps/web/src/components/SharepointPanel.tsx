"use client";

import { api } from "@/lib/api";
import { Download, FolderKanban, Plus, TestTube, Trash2 } from "lucide-react";
import { useEffect, useState } from "react";

type Sp = { id: string; name: string; site_url: string; folder: string; area: string; category: string };

export function SharepointPanel() {
  const [items, setItems] = useState<Sp[]>([]);
  const [form, setForm] = useState({ name: "", site_url: "", folder: "", area: "", category: "" });
  const [msg, setMsg] = useState("");
  const [confirmId, setConfirmId] = useState("");

  function load() { api.sharepointSources().then(setItems).catch(() => {}); }
  useEffect(load, []);

  async function create() {
    if (!form.name.trim() || !form.site_url.trim()) { setMsg("Nombre y URL del sitio son obligatorios."); return; }
    try { await api.createSharepoint(form); setForm({ name: "", site_url: "", folder: "", area: "", category: "" }); setMsg("Fuente creada."); load(); }
    catch (e) { setMsg(e instanceof Error ? e.message : "Error"); }
  }
  async function test(s: Sp) {
    setMsg(`Probando ${s.name}…`);
    try { const r = await api.testSharepoint(s.id); setMsg(`${s.name}: ${r.count} elemento(s) — ${r.files.slice(0, 5).map((f) => f.name).join(", ")}`); }
    catch (e) { setMsg(e instanceof Error ? e.message : "Error"); }
  }
  async function importNow(s: Sp) {
    setMsg(`Importando de ${s.name}…`);
    try { const r = await api.importSharepoint(s.id); setMsg(`${s.name}: ${r.imported} documento(s) importado(s) al RAG.`); }
    catch (e) { setMsg(e instanceof Error ? e.message : "Error"); }
  }
  async function remove(id: string) {
    if (confirmId !== id) { setConfirmId(id); return; }
    await api.deleteSharepoint(id); setConfirmId(""); load();
  }

  return (
    <div className="rounded-2xl border border-slate-200 bg-white p-5">
      <div className="mb-1 flex items-center gap-2">
        <FolderKanban className="h-5 w-5 text-violet-600" />
        <h2 className="font-semibold text-slate-800">Conector SharePoint (Microsoft 365)</h2>
      </div>
      <p className="mb-4 text-xs text-slate-500">
        Lee archivos de un <b>sitio/carpeta de SharePoint</b> (ej. “Proyectos Finanzas”) con tu cuenta
        Microsoft conectada y los importa al repositorio + RAG (clasificados y cifrados). Solo lectura.
      </p>

      <div className="mb-4 grid grid-cols-1 gap-2 rounded-xl border border-slate-100 bg-slate-50 p-3 sm:grid-cols-2">
        <input value={form.name} onChange={(e) => setForm({ ...form, name: e.target.value })}
          placeholder="Nombre (ej. Finanzas SP)" className="rounded-lg border border-slate-300 px-3 py-2 text-sm" />
        <input value={form.site_url} onChange={(e) => setForm({ ...form, site_url: e.target.value })}
          placeholder="URL del sitio (https://contoso.sharepoint.com/sites/Finanzas)" className="rounded-lg border border-slate-300 px-3 py-2 text-sm" />
        <input value={form.folder} onChange={(e) => setForm({ ...form, folder: e.target.value })}
          placeholder="Carpeta (ej. Proyectos Finanzas) — opcional" className="rounded-lg border border-slate-300 px-3 py-2 text-sm" />
        <input value={form.area} onChange={(e) => setForm({ ...form, area: e.target.value })}
          placeholder="Área (ej. Finanzas) — opcional" className="rounded-lg border border-slate-300 px-3 py-2 text-sm" />
        <button onClick={create} className="flex items-center justify-center gap-1.5 rounded-lg bg-violet-600 px-4 py-2 text-sm font-semibold text-white sm:col-span-2">
          <Plus className="h-4 w-4" /> Crear fuente SharePoint
        </button>
      </div>
      {msg && <div className="mb-3 rounded-lg border border-slate-200 bg-slate-50 px-3 py-2 text-xs text-slate-600">{msg}</div>}

      <div className="space-y-2">
        {items.length === 0 && <p className="text-xs text-slate-400">Aún no hay fuentes SharePoint.</p>}
        {items.map((s) => (
          <div key={s.id} className="flex items-center justify-between rounded-lg border border-slate-100 px-3 py-2 text-sm">
            <span className="min-w-0">
              <span className="font-medium text-slate-700">{s.name}</span>
              <span className="block truncate text-xs text-slate-400">{s.site_url}{s.folder ? ` · ${s.folder}` : ""}</span>
            </span>
            <span className="flex shrink-0 items-center gap-1.5">
              <button onClick={() => test(s)} title="Probar conexión" className="rounded-md border border-slate-300 p-1 text-slate-500"><TestTube className="h-3.5 w-3.5" /></button>
              <button onClick={() => importNow(s)} title="Importar al RAG" className="rounded-md bg-violet-600 p-1 text-white"><Download className="h-3.5 w-3.5" /></button>
              <button onClick={() => remove(s.id)} title={confirmId === s.id ? "Clic otra vez para confirmar" : "Eliminar"}
                className={`rounded-md border p-1 ${confirmId === s.id ? "border-red-400 bg-red-50 text-red-600" : "border-slate-300 text-red-500"}`}>
                <Trash2 className="h-3.5 w-3.5" />
              </button>
            </span>
          </div>
        ))}
      </div>
    </div>
  );
}
