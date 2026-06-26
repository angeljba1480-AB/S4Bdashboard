"use client";

import { PageHeader, Shell } from "@/components/Shell";
import { GUIDES } from "@/lib/help";
import { ChevronDown, HelpCircle, Search } from "lucide-react";
import { useState } from "react";

export default function HelpPage() {
  const [q, setQ] = useState("");
  const [open, setOpen] = useState<string | null>("n8n");
  const ql = q.trim().toLowerCase();
  const list = ql
    ? GUIDES.filter((g) => (g.title + " " + g.tag + " " + g.steps.join(" ") + " " + (g.note ?? "")).toLowerCase().includes(ql))
    : GUIDES;

  return (
    <Shell>
      <PageHeader title="Ayuda" subtitle="Guías paso a paso en español para configurar y usar MaestroAI." />

      <div className="p-8">
        <div className="mb-4 flex items-center gap-2 rounded-lg border border-slate-300 bg-white px-3 py-2">
          <Search className="h-4 w-4 text-slate-400" />
          <input value={q} onChange={(e) => setQ(e.target.value)} placeholder="Buscar en la ayuda (ej. n8n, correo, rerank)…"
            className="w-full text-sm outline-none" />
        </div>

        <div className="space-y-2">
          {list.map((g) => (
            <div key={g.id} className="overflow-hidden rounded-2xl border border-slate-200 bg-white">
              <button onClick={() => setOpen(open === g.id ? null : g.id)}
                className="flex w-full items-center justify-between px-5 py-4 text-left">
                <span className="flex items-center gap-3">
                  <HelpCircle className="h-5 w-5 text-violet-600" />
                  <span className="font-semibold text-slate-800">{g.title}</span>
                  <span className="rounded-full bg-slate-100 px-2 py-0.5 text-[11px] font-medium text-slate-500">{g.tag}</span>
                </span>
                <ChevronDown className={`h-4 w-4 text-slate-400 transition ${open === g.id ? "rotate-180" : ""}`} />
              </button>
              {open === g.id && (
                <div className="border-t border-slate-100 px-5 py-4">
                  <ol className="list-decimal space-y-2 pl-5 text-sm text-slate-700">
                    {g.steps.map((s, i) => <li key={i}>{s}</li>)}
                  </ol>
                  {g.note && <p className="mt-3 rounded-lg bg-amber-50 px-3 py-2 text-xs text-amber-800">{g.note}</p>}
                </div>
              )}
            </div>
          ))}
          {list.length === 0 && <div className="rounded-xl border border-slate-200 bg-white p-6 text-center text-sm text-slate-400">Sin resultados para “{q}”.</div>}
        </div>
      </div>
    </Shell>
  );
}
