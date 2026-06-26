"use client";

import { guidesByIds } from "@/lib/help";
import { HelpCircle, X } from "lucide-react";
import Link from "next/link";
import { useState } from "react";

/** Botón "?" por sección que abre un popup con la(s) guía(s) relevantes. */
export function HelpButton({ topics, label = "Ayuda" }: { topics: string[]; label?: string }) {
  const [open, setOpen] = useState(false);
  const guides = guidesByIds(topics);
  if (guides.length === 0) return null;

  return (
    <>
      <button
        type="button"
        onClick={() => setOpen(true)}
        title="Ayuda de esta sección"
        className="inline-flex items-center gap-1.5 rounded-full border border-violet-200 bg-violet-50 px-3 py-1 text-xs font-semibold text-violet-700 hover:bg-violet-100"
      >
        <HelpCircle className="h-4 w-4" /> {label}
      </button>

      {open && (
        <div className="fixed inset-0 z-50 flex items-center justify-center bg-slate-900/40 p-4" onClick={() => setOpen(false)}>
          <div
            className="max-h-[80vh] w-full max-w-xl overflow-y-auto rounded-2xl bg-white shadow-xl"
            onClick={(e) => e.stopPropagation()}
          >
            <div className="flex items-center justify-between border-b border-slate-100 px-5 py-3">
              <span className="flex items-center gap-2 font-semibold text-slate-800">
                <HelpCircle className="h-5 w-5 text-violet-600" /> Ayuda
              </span>
              <button onClick={() => setOpen(false)} className="text-slate-400 hover:text-slate-700"><X className="h-5 w-5" /></button>
            </div>
            <div className="space-y-5 px-5 py-4">
              {guides.map((g) => (
                <div key={g.id}>
                  <div className="mb-1 font-semibold text-slate-800">{g.title}</div>
                  <ol className="list-decimal space-y-1.5 pl-5 text-sm text-slate-700">
                    {g.steps.map((s, i) => <li key={i}>{s}</li>)}
                  </ol>
                  {g.note && <p className="mt-2 rounded-lg bg-amber-50 px-3 py-2 text-xs text-amber-800">{g.note}</p>}
                </div>
              ))}
            </div>
            <div className="border-t border-slate-100 px-5 py-3 text-right">
              <Link href="/help" className="text-xs font-semibold text-violet-700 hover:underline" onClick={() => setOpen(false)}>
                Ver toda la Ayuda →
              </Link>
            </div>
          </div>
        </div>
      )}
    </>
  );
}
