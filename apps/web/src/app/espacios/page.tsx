"use client";

import { PageHeader, Shell } from "@/components/Shell";
import { api } from "@/lib/api";
import { FolderKanban, Plus, Trash2 } from "lucide-react";
import Link from "next/link";
import { useEffect, useState } from "react";

type Space = { id: string; name: string; client: string; description: string; modules: { key: string; title: string }[] };

export default function EspaciosPage() {
  const [spaces, setSpaces] = useState<Space[]>([]);
  const [form, setForm] = useState({ name: "", client: "", description: "" });
  const [msg, setMsg] = useState("");
  const [creating, setCreating] = useState(false);

  function load() { api.spaces().then(setSpaces).catch(() => {}); }
  useEffect(() => { load(); }, []);

  async function create() {
    if (!form.name.trim()) { setMsg("Pon un nombre al espacio."); return; }
    try {
      await api.createSpace(form);
      setForm({ name: "", client: "", description: "" });
      setCreating(false); setMsg(""); load();
    } catch (e) { setMsg(e instanceof Error ? e.message : "Error"); }
  }
  async function remove(id: string) { await api.deleteSpace(id); load(); }

  return (
    <Shell>
      <PageHeader title="Espacios" subtitle="Proyectos del cliente: cada espacio agrupa sus tableros, fuentes y casos, aislados del resto." />
      <div className="p-8">
        <div className="mb-5">
          {!creating ? (
            <button onClick={() => setCreating(true)} className="flex items-center gap-1.5 rounded-lg bg-violet-600 px-4 py-2 text-sm font-semibold text-white">
              <Plus className="h-4 w-4" /> Nuevo espacio
            </button>
          ) : (
            <div className="rounded-2xl border border-slate-200 bg-white p-5">
              <h2 className="mb-3 font-semibold text-slate-800">Nuevo espacio (proyecto)</h2>
              <div className="grid grid-cols-1 gap-2 sm:grid-cols-2">
                <input value={form.name} onChange={(e) => setForm({ ...form, name: e.target.value })} placeholder="Nombre del proyecto (ej. Tablero Financiero S4B)" className="rounded-lg border border-slate-300 px-3 py-2 text-sm" />
                <input value={form.client} onChange={(e) => setForm({ ...form, client: e.target.value })} placeholder="Cliente (ej. Silent4Business)" className="rounded-lg border border-slate-300 px-3 py-2 text-sm" />
              </div>
              <textarea value={form.description} onChange={(e) => setForm({ ...form, description: e.target.value })} rows={2} placeholder="Descripción (opcional)" className="mt-2 w-full rounded-lg border border-slate-300 px-3 py-2 text-sm" />
              <div className="mt-3 flex gap-2">
                <button onClick={create} className="rounded-lg bg-violet-600 px-4 py-2 text-sm font-semibold text-white">Crear</button>
                <button onClick={() => { setCreating(false); setMsg(""); }} className="rounded-lg border border-slate-300 px-4 py-2 text-sm font-semibold text-slate-600">Cancelar</button>
              </div>
              {msg && <p className="mt-2 text-xs text-red-600">{msg}</p>}
            </div>
          )}
        </div>

        <div className="grid grid-cols-1 gap-4 md:grid-cols-2 lg:grid-cols-3">
          {spaces.length === 0 && <p className="text-sm text-slate-400">Aún no hay espacios. Crea el primero para tu cliente.</p>}
          {spaces.map((s) => (
            <div key={s.id} className="group relative rounded-2xl border border-slate-200 bg-white p-5 transition hover:border-violet-300 hover:shadow-sm">
              <Link href={`/espacios/${s.id}`} className="block">
                <div className="mb-2 flex items-center gap-2">
                  <span className="flex h-9 w-9 items-center justify-center rounded-lg bg-violet-100 text-violet-700"><FolderKanban className="h-5 w-5" /></span>
                  <div>
                    <div className="font-semibold text-slate-800">{s.name}</div>
                    {s.client && <div className="text-xs text-slate-400">{s.client}</div>}
                  </div>
                </div>
                {s.description && <p className="text-sm text-slate-500">{s.description}</p>}
                <div className="mt-3 flex flex-wrap gap-1.5">
                  {s.modules.map((m) => <span key={m.key} className="rounded-full bg-slate-100 px-2 py-0.5 text-[11px] font-medium text-slate-600">{m.title}</span>)}
                </div>
              </Link>
              <button onClick={() => remove(s.id)} title="Eliminar" className="absolute right-3 top-3 rounded-md p-1 text-slate-300 opacity-0 transition hover:bg-red-50 hover:text-red-500 group-hover:opacity-100">
                <Trash2 className="h-4 w-4" />
              </button>
            </div>
          ))}
        </div>
      </div>
    </Shell>
  );
}
