"use client";

import { PageHeader, Shell } from "@/components/Shell";
import { api } from "@/lib/api";
import type { DocumentCategory, DocumentItem } from "@shared/types";
import { FolderOpen, Trash2, Upload } from "lucide-react";
import { useEffect, useState } from "react";

const SENS_OPTIONS = [
  { value: "public", label: "Público" },
  { value: "internal", label: "Interno" },
  { value: "confidential", label: "Confidencial" },
  { value: "restricted", label: "Restringido" },
];
const NO_AREA = "Sin área / General";

export default function DocumentsPage() {
  const [docs, setDocs] = useState<DocumentItem[]>([]);
  const [cats, setCats] = useState<DocumentCategory[]>([]);
  const [areas, setAreas] = useState<string[]>([]);
  // upload form
  const [filename, setFilename] = useState("nota.txt");
  const [text, setText] = useState("");
  const [upArea, setUpArea] = useState("");
  const [upCat, setUpCat] = useState("");
  const [upSens, setUpSens] = useState("auto");
  const [busy, setBusy] = useState(false);
  // new category
  const [newCat, setNewCat] = useState("");
  // filters
  const [fArea, setFArea] = useState("");
  const [fCat, setFCat] = useState("");

  function load() {
    api.documents().then(setDocs).catch(() => {});
    api.documentCategories().then(setCats).catch(() => {});
    api.companyProfile()
      .then((p) => setAreas((p.areas || []).map((a) => a.name).filter(Boolean)))
      .catch(() => {});
  }
  useEffect(load, []);

  const meta = () => ({ area: upArea, category: upCat, sensitivity: upSens });

  async function uploadText(e: React.FormEvent) {
    e.preventDefault();
    if (!text.trim()) return;
    setBusy(true);
    try {
      await api.uploadText(filename, text, meta());
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
      await api.uploadFile(file, meta());
      load();
    } finally {
      setBusy(false);
      e.target.value = "";
    }
  }

  async function addCategory() {
    if (!newCat.trim()) return;
    const c = await api.createDocumentCategory({ label: newCat.trim() });
    setNewCat("");
    setUpCat(c.key);
    api.documentCategories().then(setCats).catch(() => {});
  }

  async function retag(id: string, body: { area?: string; category?: string; sensitivity?: string }) {
    await api.updateDocument(id, body);
    load();
  }

  async function remove(id: string, name: string) {
    if (!confirm(`¿Borrar "${name}"? También se elimina del índice RAG.`)) return;
    await api.deleteDocument(id);
    load();
  }

  const catLabel = (key: string) => cats.find((c) => c.key === key)?.label || "";

  // Apply filters, then group by area into containers.
  const filtered = docs.filter((d) =>
    (!fArea || (d.area || "") === fArea) && (!fCat || d.category === fCat));
  const groups = Array.from(new Set(filtered.map((d) => d.area || "")))
    .sort((a, b) => (a === "" ? 1 : b === "" ? -1 : a.localeCompare(b)))
    .map((area) => ({ area, items: filtered.filter((d) => (d.area || "") === area) }));

  const inputCls = "rounded-lg border border-slate-300 px-3 py-2 text-sm";

  return (
    <Shell>
      <PageHeader
        title="Documentos"
        subtitle="Contenedor de documentos por área → categoría → tratamiento (público/privado) → índice RAG cifrado."
      />
      <div className="grid grid-cols-1 gap-6 p-8 lg:grid-cols-3">
        {/* Upload */}
        <div className="lg:col-span-1">
          <form onSubmit={uploadText} className="rounded-2xl border border-slate-200 bg-white p-5">
            <h3 className="mb-3 font-semibold text-slate-800">Cargar documento</h3>

            <label className="mb-1 block text-xs font-medium text-slate-500">Nombre</label>
            <input value={filename} onChange={(e) => setFilename(e.target.value)} className={`mb-3 w-full ${inputCls}`} placeholder="nombre.txt" />

            <label className="mb-1 block text-xs font-medium text-slate-500">Área</label>
            <select value={upArea} onChange={(e) => setUpArea(e.target.value)} className={`mb-3 w-full ${inputCls}`}>
              <option value="">Sin área / General</option>
              {areas.map((a) => <option key={a} value={a}>{a}</option>)}
            </select>

            <label className="mb-1 block text-xs font-medium text-slate-500">Categoría</label>
            <select value={upCat} onChange={(e) => setUpCat(e.target.value)} className={`mb-2 w-full ${inputCls}`}>
              <option value="">Sin categoría</option>
              {cats.map((c) => <option key={c.key} value={c.key}>{c.label}</option>)}
            </select>
            <div className="mb-3 flex gap-2">
              <input value={newCat} onChange={(e) => setNewCat(e.target.value)} placeholder="➕ Nueva categoría…" className={`flex-1 ${inputCls}`} />
              <button type="button" onClick={addCategory} className="rounded-lg bg-slate-900 px-3 text-sm font-semibold text-white">Crear</button>
            </div>

            <label className="mb-1 block text-xs font-medium text-slate-500">Tratamiento</label>
            <select value={upSens} onChange={(e) => setUpSens(e.target.value)} className={`mb-1 w-full ${inputCls}`}>
              <option value="auto">Detectar automáticamente</option>
              {SENS_OPTIONS.map((s) => <option key={s.value} value={s.value}>{s.label}</option>)}
            </select>
            <p className="mb-3 text-xs text-slate-400">El sistema detecta público/privado y PII; aquí puedes forzarlo.</p>

            <textarea value={text} onChange={(e) => setText(e.target.value)} rows={5} className={`mb-3 w-full ${inputCls}`}
              placeholder="Pega texto (prueba con RFC, CURP o 'contrato confidencial')…" />
            <button disabled={busy} className="mb-3 w-full rounded-lg bg-violet-600 py-2 text-sm font-semibold text-white hover:bg-violet-700 disabled:opacity-50">
              Clasificar y cargar
            </button>
            <label className="flex cursor-pointer items-center justify-center gap-2 rounded-lg border border-dashed border-slate-300 py-2 text-sm text-slate-500 hover:bg-slate-50">
              <Upload className="h-4 w-4" /> Subir archivo
              <input type="file" className="hidden" onChange={uploadFile} accept=".txt,.md,.csv,.json" />
            </label>
          </form>
        </div>

        {/* Containers by area */}
        <div className="space-y-5 lg:col-span-2">
          {/* Filters */}
          <div className="flex flex-wrap items-center gap-2">
            <select value={fArea} onChange={(e) => setFArea(e.target.value)} className={inputCls}>
              <option value="">Todas las áreas</option>
              {Array.from(new Set(docs.map((d) => d.area || ""))).filter(Boolean).map((a) => <option key={a} value={a}>{a}</option>)}
            </select>
            <select value={fCat} onChange={(e) => setFCat(e.target.value)} className={inputCls}>
              <option value="">Todas las categorías</option>
              {cats.map((c) => <option key={c.key} value={c.key}>{c.label}</option>)}
            </select>
            <span className="text-xs text-slate-400">{filtered.length} documento(s)</span>
          </div>

          {groups.length === 0 && (
            <div className="rounded-2xl border border-dashed border-slate-300 bg-white p-8 text-center text-sm text-slate-400">
              Sin documentos. Carga el primero a la izquierda.
            </div>
          )}

          {groups.map((g) => (
            <div key={g.area || "_none"} className="overflow-hidden rounded-2xl border border-slate-200 bg-white">
              <div className="flex items-center gap-2 border-b border-slate-200 bg-slate-50 px-4 py-2.5">
                <FolderOpen className="h-4 w-4 text-violet-600" />
                <span className="text-sm font-semibold text-slate-700">{g.area || NO_AREA}</span>
                <span className="text-xs text-slate-400">· {g.items.length}</span>
              </div>
              <table className="w-full text-sm">
                <thead className="border-b border-slate-200 text-xs uppercase text-slate-400">
                  <tr>
                    <th className="px-4 py-2 text-left">Documento</th>
                    <th className="px-4 py-2 text-left">Categoría</th>
                    <th className="px-4 py-2 text-left">Tratamiento</th>
                    <th className="px-4 py-2 text-left">PII</th>
                    <th className="px-4 py-2 text-center">RAG</th>
                    <th className="px-4 py-2 text-right">Acción</th>
                  </tr>
                </thead>
                <tbody>
                  {g.items.map((d) => (
                    <tr key={d.id} className="border-b border-slate-100">
                      <td className="px-4 py-2 font-medium text-slate-700">{d.filename}</td>
                      <td className="px-4 py-2">
                        <select value={d.category} onChange={(e) => retag(d.id, { category: e.target.value })}
                          className="rounded-md border border-slate-200 bg-white px-2 py-1 text-xs">
                          <option value="">Sin categoría</option>
                          {cats.map((c) => <option key={c.key} value={c.key}>{c.label}</option>)}
                        </select>
                      </td>
                      <td className="px-4 py-2">
                        <select value={d.sensitivity} onChange={(e) => retag(d.id, { sensitivity: e.target.value })}
                          className="rounded-md border border-slate-200 bg-white px-2 py-1 text-xs">
                          {SENS_OPTIONS.map((s) => <option key={s.value} value={s.value}>{s.label}</option>)}
                        </select>
                      </td>
                      <td className="px-4 py-2 text-xs text-slate-500">{d.pii_types.length ? d.pii_types.join(", ") : "—"}</td>
                      <td className="px-4 py-2 text-center">{d.indexed ? "✓" : "—"}</td>
                      <td className="px-4 py-2 text-right">
                        <button onClick={() => remove(d.id, d.filename)} className="text-slate-400 hover:text-red-600">
                          <Trash2 className="h-4 w-4" />
                        </button>
                      </td>
                    </tr>
                  ))}
                </tbody>
              </table>
            </div>
          ))}
        </div>
      </div>
    </Shell>
  );
}
