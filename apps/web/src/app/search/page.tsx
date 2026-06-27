"use client";

import { PageHeader, Shell } from "@/components/Shell";
import { api } from "@/lib/api";
import { FileText, Search as SearchIcon } from "lucide-react";
import Link from "next/link";
import { useSearchParams } from "next/navigation";
import { Suspense, useEffect, useState } from "react";

type Hit = { type: string; id: string; title: string; snippet: string; href: string; area?: string };

const TYPE_LABEL: Record<string, string> = {
  document: "Documento", memory: "Memoria", notebook: "Notebook", playbook: "Receta del agente",
  recipe: "Automatización", image: "Imagen", automation: "Automatización",
};

function SearchInner() {
  const initial = useSearchParams().get("q") || "";
  const [q, setQ] = useState(initial);
  const [hits, setHits] = useState<Hit[]>([]);
  const [loading, setLoading] = useState(false);
  const [searched, setSearched] = useState(false);

  async function run(term: string) {
    if (term.trim().length < 2) { setHits([]); setSearched(false); return; }
    setLoading(true);
    try {
      const r = await api.search(term);
      setHits(r.results);
      setSearched(true);
    } finally { setLoading(false); }
  }

  useEffect(() => { if (initial) run(initial); /* eslint-disable-next-line react-hooks/exhaustive-deps */ }, []);

  return (
    <Shell>
      <PageHeader title="Búsqueda global" subtitle="Encuentra documentos, memoria, notebooks, recetas, automatizaciones e imágenes en un solo lugar." />
      <div className="p-8">
        <form onSubmit={(e) => { e.preventDefault(); run(q); }} className="mb-6 flex gap-2">
          <div className="relative flex-1">
            <SearchIcon className="absolute left-3 top-1/2 h-4 w-4 -translate-y-1/2 text-slate-400" />
            <input value={q} onChange={(e) => setQ(e.target.value)} autoFocus
              placeholder="Busca en toda la plataforma…"
              className="w-full rounded-lg border border-slate-300 py-2.5 pl-9 pr-3 text-sm" />
          </div>
          <button className="rounded-lg bg-violet-600 px-5 py-2.5 text-sm font-semibold text-white">Buscar</button>
        </form>

        {loading && <p className="text-sm text-slate-400">Buscando…</p>}
        {!loading && searched && hits.length === 0 && (
          <p className="text-sm text-slate-400">Sin resultados para «{q}».</p>
        )}
        <div className="space-y-2">
          {hits.map((h) => (
            <Link key={`${h.type}-${h.id}`} href={h.href}
              className="flex items-start gap-3 rounded-xl border border-slate-200 bg-white p-4 transition hover:border-violet-300 hover:bg-violet-50/30">
              <FileText className="mt-0.5 h-4 w-4 shrink-0 text-violet-500" />
              <div className="min-w-0">
                <div className="flex items-center gap-2">
                  <span className="font-medium text-slate-800">{h.title}</span>
                  <span className="rounded-full bg-slate-100 px-2 py-0.5 text-[10px] font-semibold uppercase tracking-wide text-slate-500">{TYPE_LABEL[h.type] || h.type}</span>
                  {h.area && <span className="text-[10px] text-slate-400">{h.area}</span>}
                </div>
                {h.snippet && <p className="mt-0.5 truncate text-xs text-slate-500">{h.snippet}</p>}
              </div>
            </Link>
          ))}
        </div>
      </div>
    </Shell>
  );
}

export default function SearchPage() {
  return (
    <Suspense fallback={<Shell><div className="p-8 text-sm text-slate-400">Cargando…</div></Shell>}>
      <SearchInner />
    </Suspense>
  );
}
