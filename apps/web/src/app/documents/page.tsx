"use client";

import { SensitivityBadge } from "@/components/PrivacyBadge";
import { PageHeader, Shell } from "@/components/Shell";
import { api } from "@/lib/api";
import type { DocumentItem } from "@shared/types";
import { Upload } from "lucide-react";
import { useEffect, useState } from "react";

export default function DocumentsPage() {
  const [docs, setDocs] = useState<DocumentItem[]>([]);
  const [filename, setFilename] = useState("nota.txt");
  const [text, setText] = useState("");
  const [busy, setBusy] = useState(false);

  function load() {
    api.documents().then(setDocs);
  }
  useEffect(load, []);

  async function uploadText(e: React.FormEvent) {
    e.preventDefault();
    if (!text.trim()) return;
    setBusy(true);
    try {
      await api.uploadText(filename, text);
      setText("");
      load();
    } finally {
      setBusy(false);
    }
  }

  async function uploadFile(e: React.ChangeEvent<HTMLInputElement>) {
    const file = e.target.files?.[0];
    if (!file) return;
    setBusy(true);
    try {
      await api.uploadFile(file);
      load();
    } finally {
      setBusy(false);
      e.target.value = "";
    }
  }

  return (
    <Shell>
      <PageHeader title="Documentos" subtitle="Carga segura → clasificación → detección PII → índice RAG cifrado." />
      <div className="grid grid-cols-1 gap-6 p-8 lg:grid-cols-3">
        <div className="lg:col-span-1">
          <form onSubmit={uploadText} className="rounded-2xl border border-slate-200 bg-white p-5">
            <h3 className="mb-3 font-semibold text-slate-800">Cargar documento</h3>
            <input
              value={filename}
              onChange={(e) => setFilename(e.target.value)}
              className="mb-3 w-full rounded-lg border border-slate-300 px-3 py-2 text-sm"
              placeholder="nombre.txt"
            />
            <textarea
              value={text}
              onChange={(e) => setText(e.target.value)}
              rows={6}
              className="mb-3 w-full rounded-lg border border-slate-300 px-3 py-2 text-sm"
              placeholder="Pega texto (prueba con RFC, CURP o 'contrato confidencial')…"
            />
            <button
              disabled={busy}
              className="mb-3 w-full rounded-lg bg-violet-600 py-2 text-sm font-semibold text-white hover:bg-violet-700 disabled:opacity-50"
            >
              Clasificar y cargar
            </button>
            <label className="flex cursor-pointer items-center justify-center gap-2 rounded-lg border border-dashed border-slate-300 py-2 text-sm text-slate-500 hover:bg-slate-50">
              <Upload className="h-4 w-4" /> Subir archivo
              <input type="file" className="hidden" onChange={uploadFile} accept=".txt,.md,.csv,.json" />
            </label>
          </form>
        </div>

        <div className="lg:col-span-2">
          <div className="overflow-hidden rounded-2xl border border-slate-200 bg-white">
            <table className="w-full text-sm">
              <thead className="border-b border-slate-200 bg-slate-50 text-xs uppercase text-slate-400">
                <tr>
                  <th className="px-4 py-2.5 text-left">Documento</th>
                  <th className="px-4 py-2.5 text-left">Sensibilidad</th>
                  <th className="px-4 py-2.5 text-left">PII</th>
                  <th className="px-4 py-2.5 text-right">Score</th>
                  <th className="px-4 py-2.5 text-center">Indexado</th>
                </tr>
              </thead>
              <tbody>
                {docs.map((d) => (
                  <tr key={d.id} className="border-b border-slate-100">
                    <td className="px-4 py-2.5 font-medium text-slate-700">{d.filename}</td>
                    <td className="px-4 py-2.5"><SensitivityBadge level={d.sensitivity} /></td>
                    <td className="px-4 py-2.5 text-xs text-slate-500">
                      {d.pii_types.length ? d.pii_types.join(", ") : "—"}
                    </td>
                    <td className="px-4 py-2.5 text-right tabular-nums text-slate-600">{d.pii_score.toFixed(2)}</td>
                    <td className="px-4 py-2.5 text-center">{d.indexed ? "✓" : "—"}</td>
                  </tr>
                ))}
                {docs.length === 0 && (
                  <tr>
                    <td colSpan={5} className="px-4 py-8 text-center text-slate-400">Sin documentos.</td>
                  </tr>
                )}
              </tbody>
            </table>
          </div>
        </div>
      </div>
    </Shell>
  );
}
