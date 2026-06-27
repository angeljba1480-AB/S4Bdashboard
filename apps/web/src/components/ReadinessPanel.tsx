"use client";

import { api } from "@/lib/api";
import { AlertTriangle, CheckCircle2, ChevronDown, RefreshCw, XCircle } from "lucide-react";
import Link from "next/link";
import { useEffect, useState } from "react";

type Check = {
  key: string; label: string; status: "ok" | "warn" | "missing"; detail: string;
  fix: { steps: string[]; help?: string | null; link?: string | null } | null;
};

const STYLE = {
  ok: { icon: CheckCircle2, color: "text-emerald-600", chip: "bg-emerald-100 text-emerald-700", word: "Listo" },
  warn: { icon: AlertTriangle, color: "text-amber-600", chip: "bg-amber-100 text-amber-700", word: "Por configurar" },
  missing: { icon: XCircle, color: "text-red-600", chip: "bg-red-100 text-red-700", word: "Falta" },
};

export function ReadinessPanel() {
  const [checks, setChecks] = useState<Check[] | null>(null);
  const [summary, setSummary] = useState<Record<string, number>>({});
  const [open, setOpen] = useState<string | null>(null);
  const [loading, setLoading] = useState(false);

  function load() {
    setLoading(true);
    api.readiness().then((r) => { setChecks(r.checks); setSummary(r.summary); }).catch(() => setChecks([])).finally(() => setLoading(false));
  }
  useEffect(load, []);

  return (
    <div className="rounded-2xl border border-slate-200 bg-white p-5">
      <div className="mb-3 flex items-center justify-between">
        <div>
          <h2 className="font-semibold text-slate-800">Autochequeo del sistema</h2>
          <p className="text-xs text-slate-500">Qué está listo y, si falta algo, cómo resolverlo aquí mismo.</p>
        </div>
        <div className="flex items-center gap-2">
          {summary.ok != null && (
            <span className="hidden gap-1 text-xs sm:flex">
              <span className="rounded-full bg-emerald-100 px-2 py-0.5 font-semibold text-emerald-700">{summary.ok || 0} listo</span>
              <span className="rounded-full bg-amber-100 px-2 py-0.5 font-semibold text-amber-700">{summary.warn || 0} por configurar</span>
              {(summary.missing || 0) > 0 && <span className="rounded-full bg-red-100 px-2 py-0.5 font-semibold text-red-700">{summary.missing} falta</span>}
            </span>
          )}
          <button onClick={load} className="flex items-center gap-1 rounded-md border border-slate-300 px-2 py-1 text-xs font-semibold text-slate-600">
            <RefreshCw className={`h-3.5 w-3.5 ${loading ? "animate-spin" : ""}`} /> Revisar
          </button>
        </div>
      </div>

      <div className="space-y-2">
        {checks?.map((c) => {
          const s = STYLE[c.status];
          const Icon = s.icon;
          const isOpen = open === c.key;
          return (
            <div key={c.key} className="rounded-lg border border-slate-100">
              <button onClick={() => setOpen(isOpen ? null : c.key)}
                className="flex w-full items-center justify-between gap-2 px-3 py-2 text-left">
                <span className="flex items-center gap-2 text-sm text-slate-700">
                  <Icon className={`h-4 w-4 shrink-0 ${s.color}`} /> {c.label}
                </span>
                <span className="flex items-center gap-2">
                  <span className={`rounded-full px-2 py-0.5 text-[10px] font-semibold ${s.chip}`}>{s.word}</span>
                  {c.fix && <ChevronDown className={`h-4 w-4 text-slate-400 transition ${isOpen ? "rotate-180" : ""}`} />}
                </span>
              </button>
              {isOpen && (
                <div className="border-t border-slate-100 px-3 py-2 text-sm">
                  <p className="mb-2 text-slate-600">{c.detail}</p>
                  {c.fix && (
                    <>
                      <p className="mb-1 text-xs font-semibold uppercase tracking-wide text-slate-400">Cómo resolverlo</p>
                      <ol className="list-decimal space-y-1 pl-5 text-slate-700">
                        {c.fix.steps.map((st, i) => <li key={i}>{st}</li>)}
                      </ol>
                      {c.fix.link && (
                        <Link href={c.fix.link} className="mt-2 inline-block rounded-md bg-violet-600 px-3 py-1 text-xs font-semibold text-white">
                          Ir a configurarlo
                        </Link>
                      )}
                    </>
                  )}
                </div>
              )}
            </div>
          );
        })}
        {checks?.length === 0 && <p className="text-xs text-slate-400">No se pudo cargar el autochequeo.</p>}
      </div>
    </div>
  );
}
