"use client";

import { PageHeader, Shell } from "@/components/Shell";
import { api } from "@/lib/api";
import type { MemoryItem } from "@shared/types";
import { Brain, Plus, Search, Trash2 } from "lucide-react";
import { useEffect, useState } from "react";

export default function MemoryPage() {
  const [items, setItems] = useState<MemoryItem[]>([]);
  const [tags, setTags] = useState<string[]>([]);
  const [q, setQ] = useState("");
  const [tag, setTag] = useState("");
  const [draft, setDraft] = useState({ title: "", content: "", tags: "" });
  const [open, setOpen] = useState<string | null>(null);

  function load() {
    api.memory({ q: q || undefined, tag: tag || undefined }).then(setItems).catch(() => {});
    api.memoryTags().then(setTags).catch(() => {});
  }
  useEffect(load, [tag]); // eslint-disable-line

  async function add() {
    if (!draft.content.trim()) return;
    await api.createMemory({
      title: draft.title.trim() || draft.content.slice(0, 50),
      content: draft.content.trim(),
      tags: draft.tags.split(",").map((t) => t.trim()).filter(Boolean),
    });
    setDraft({ title: "", content: "", tags: "" });
    load();
  }

  async function remove(id: string) {
    if (!confirm("¿Borrar este recuerdo?")) return;
    await api.deleteMemory(id);
    load();
  }

  return (
    <Shell>
      <PageHeader title="Memoria" subtitle="Tus trabajos guardados. Búscalos, etiquétalos y recupéralos — '¿recuerdas el trabajo C?'." />
      <div className="grid grid-cols-1 gap-6 p-8 lg:grid-cols-3">
        {/* Add */}
        <div className="lg:col-span-1">
          <div className="rounded-2xl border border-slate-200 bg-white p-5">
            <h3 className="mb-3 flex items-center gap-1.5 font-semibold text-slate-800"><Plus className="h-4 w-4" /> Guardar un trabajo</h3>
            <input value={draft.title} onChange={(e) => setDraft({ ...draft, title: e.target.value })}
              placeholder="Título" className="mb-2 w-full rounded-lg border border-slate-300 px-3 py-2 text-sm" />
            <textarea value={draft.content} onChange={(e) => setDraft({ ...draft, content: e.target.value })} rows={5}
              placeholder="Contenido / resultado a recordar…" className="mb-2 w-full rounded-lg border border-slate-300 px-3 py-2 text-sm" />
            <input value={draft.tags} onChange={(e) => setDraft({ ...draft, tags: e.target.value })}
              placeholder="Tags separados por coma (ej. ventas, acme)" className="mb-2 w-full rounded-lg border border-slate-300 px-3 py-2 text-sm" />
            <button onClick={add} className="w-full rounded-lg bg-violet-600 py-2 text-sm font-semibold text-white">Guardar en memoria</button>
          </div>
        </div>

        {/* List */}
        <div className="space-y-4 lg:col-span-2">
          <div className="flex flex-wrap items-center gap-2">
            <div className="flex flex-1 items-center gap-2 rounded-lg border border-slate-300 px-3">
              <Search className="h-4 w-4 text-slate-400" />
              <input value={q} onChange={(e) => setQ(e.target.value)} onKeyDown={(e) => e.key === "Enter" && load()}
                placeholder="Busca en tu memoria…" className="flex-1 py-2 text-sm focus:outline-none" />
            </div>
            <button onClick={load} className="rounded-lg bg-slate-900 px-4 py-2 text-sm font-semibold text-white">Buscar</button>
          </div>
          {tags.length > 0 && (
            <div className="flex flex-wrap gap-1.5">
              <button onClick={() => setTag("")} className={`rounded-full px-3 py-1 text-xs font-medium ${tag === "" ? "bg-violet-600 text-white" : "bg-white text-slate-600 ring-1 ring-slate-200"}`}>Todos</button>
              {tags.map((t) => (
                <button key={t} onClick={() => setTag(t)} className={`rounded-full px-3 py-1 text-xs font-medium ${tag === t ? "bg-violet-600 text-white" : "bg-white text-slate-600 ring-1 ring-slate-200"}`}>{t}</button>
              ))}
            </div>
          )}

          {items.length === 0 && (
            <div className="rounded-2xl border border-dashed border-slate-300 bg-white p-10 text-center text-sm text-slate-400">
              <Brain className="mx-auto mb-2 h-6 w-6 text-slate-300" /> Sin recuerdos todavía. Guarda trabajos desde aquí, el chat o los casos de uso.
            </div>
          )}
          {items.map((m) => (
            <div key={m.id} className="rounded-2xl border border-slate-200 bg-white p-4">
              <div className="flex items-start justify-between">
                <button onClick={() => setOpen(open === m.id ? null : m.id)} className="flex-1 text-left">
                  <div className="font-semibold text-slate-800">{m.title}</div>
                  <div className="mt-0.5 text-xs text-slate-400">{m.source} · {new Date(m.created_at).toLocaleDateString()}</div>
                </button>
                <button onClick={() => remove(m.id)} className="text-slate-300 hover:text-red-600"><Trash2 className="h-4 w-4" /></button>
              </div>
              {m.tags.length > 0 && (
                <div className="mt-2 flex flex-wrap gap-1">
                  {m.tags.map((t) => <span key={t} className="rounded-full bg-violet-50 px-2 py-0.5 text-[11px] font-medium text-violet-700">{t}</span>)}
                </div>
              )}
              <p className={`mt-2 whitespace-pre-wrap text-sm text-slate-600 ${open === m.id ? "" : "line-clamp-2"}`}>{m.content}</p>
            </div>
          ))}
        </div>
      </div>
    </Shell>
  );
}
