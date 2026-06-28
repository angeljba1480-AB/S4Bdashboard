"use client";

import { PageHeader, Shell } from "@/components/Shell";
import { api } from "@/lib/api";
import { ArrowRight, ChevronLeft, LineChart } from "lucide-react";
import Link from "next/link";
import { useParams } from "next/navigation";
import { useEffect, useState } from "react";

type Space = { id: string; name: string; client: string; description: string; modules: { key: string; title: string; href: string; desc: string }[] };

export default function SpaceDetailPage() {
  const id = String(useParams().id || "");
  const [space, setSpace] = useState<Space | null>(null);
  const [err, setErr] = useState("");

  useEffect(() => { api.space(id).then(setSpace).catch((e) => setErr(e instanceof Error ? e.message : "Error")); }, [id]);

  if (err) return <Shell><div className="p-8 text-sm text-red-600">{err}</div></Shell>;
  if (!space) return <Shell><div className="p-8 text-sm text-slate-400">Cargando…</div></Shell>;

  return (
    <Shell>
      <PageHeader title={space.name} subtitle={space.client ? `Cliente: ${space.client}` : "Proyecto del cliente"} />
      <div className="p-8">
        <Link href="/espacios" className="mb-4 inline-flex items-center gap-1 text-sm text-slate-500 hover:text-slate-700">
          <ChevronLeft className="h-4 w-4" /> Espacios
        </Link>
        {space.description && <p className="mb-5 max-w-2xl text-sm text-slate-500">{space.description}</p>}

        <h2 className="mb-3 text-sm font-semibold uppercase tracking-wide text-slate-500">Módulos del proyecto</h2>
        <div className="grid grid-cols-1 gap-4 md:grid-cols-2 lg:grid-cols-3">
          {space.modules.map((m) => (
            <Link key={m.key} href={`${m.href}?space=${space.id}`}
              className="flex flex-col rounded-2xl border border-slate-200 bg-white p-5 transition hover:border-violet-300 hover:shadow-sm">
              <span className="mb-2 flex h-9 w-9 items-center justify-center rounded-lg bg-violet-100 text-violet-700"><LineChart className="h-5 w-5" /></span>
              <div className="font-semibold text-slate-800">{m.title}</div>
              <p className="mt-1 flex-1 text-sm text-slate-500">{m.desc}</p>
              <span className="mt-3 inline-flex items-center gap-1 text-sm font-semibold text-violet-700">Abrir <ArrowRight className="h-3.5 w-3.5" /></span>
            </Link>
          ))}
        </div>
        <p className="mt-6 text-xs text-slate-400">
          Más módulos (documentos, chat con fuentes, runbooks, alertas) se irán sumando a este espacio,
          aislados por proyecto/cliente.
        </p>
      </div>
    </Shell>
  );
}
