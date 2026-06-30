"use client";

import { api } from "@/lib/api";
import { Download } from "lucide-react";
import { useState } from "react";

const FORMATS: { fmt: "pdf" | "docx" | "pptx" | "xlsx"; label: string }[] = [
  { fmt: "pdf", label: "PDF" },
  { fmt: "docx", label: "Word" },
  { fmt: "pptx", label: "PowerPoint" },
  { fmt: "xlsx", label: "Excel" },
];

/** Menú de exportación reusable: descarga (PDF/Word/PPT/Excel) o guarda en la
 * nube del cliente (Google Docs / OneDrive) vía el toolkit Google/Microsoft. */
export function ExportMenu({ title, content, compact = false }: { title: string; content: string; compact?: boolean }) {
  const [open, setOpen] = useState(false);
  const [msg, setMsg] = useState("");

  async function dl(fmt: "pdf" | "docx" | "pptx" | "xlsx") {
    setMsg("");
    try { await api.exportReport(title, content, fmt); setOpen(false); }
    catch (e) { setMsg(e instanceof Error ? e.message : "Error"); }
  }
  async function cloud(provider: "google" | "microsoft") {
    setMsg("Guardando…");
    try { const r = await api.exportToCloud(title, content, provider); setMsg(`✓ ${r.detail}`); }
    catch (e) { setMsg(e instanceof Error ? `✗ ${e.message}` : "Error"); }
  }

  return (
    <div className="relative inline-block">
      <button onClick={() => setOpen((v) => !v)}
        className={`inline-flex items-center gap-1 rounded-md border border-slate-300 font-semibold text-slate-600 hover:bg-slate-50 ${compact ? "px-2 py-1 text-[11px]" : "px-3 py-1.5 text-xs"}`}>
        <Download className="h-3.5 w-3.5" /> Exportar
      </button>
      {open && (
        <div className="absolute right-0 z-20 mt-1 w-52 rounded-lg border border-slate-200 bg-white p-2 shadow-lg">
          <div className="px-2 pb-1 text-[10px] font-bold uppercase tracking-wide text-slate-400">Descargar</div>
          <div className="grid grid-cols-2 gap-1">
            {FORMATS.map((f) => (
              <button key={f.fmt} onClick={() => dl(f.fmt)} className="rounded-md border border-slate-200 px-2 py-1 text-xs hover:bg-slate-50">{f.label}</button>
            ))}
          </div>
          <div className="mt-2 px-2 pb-1 text-[10px] font-bold uppercase tracking-wide text-slate-400">Guardar en la nube</div>
          <div className="grid grid-cols-2 gap-1">
            <button onClick={() => cloud("google")} className="rounded-md border border-slate-200 px-2 py-1 text-xs hover:bg-slate-50">Google Docs</button>
            <button onClick={() => cloud("microsoft")} className="rounded-md border border-slate-200 px-2 py-1 text-xs hover:bg-slate-50">OneDrive</button>
          </div>
          {msg && <div className="mt-2 px-1 text-[11px] text-slate-500">{msg}</div>}
        </div>
      )}
    </div>
  );
}
