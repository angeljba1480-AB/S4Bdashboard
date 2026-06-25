"use client";

import { PageHeader, Shell } from "@/components/Shell";
import { api } from "@/lib/api";
import type { DocumentItem, Notebook, NotebookAnswer } from "@shared/types";
import { BookOpen, Plus, Send, Sparkles, Trash2 } from "lucide-react";
import { useEffect, useState } from "react";

const ARTIFACTS = [
  { kind: "resumen", label: "Resumen" },
  { kind: "faq", label: "FAQ" },
  { kind: "guia", label: "Guía de estudio" },
  { kind: "brief", label: "Briefing" },
  { kind: "cronologia", label: "Cronología" },
];

export default function NotebooksPage() {
  const [notebooks, setNotebooks] = useState<Notebook[]>([]);
  const [docs, setDocs] = useState<DocumentItem[]>([]);
  const [active, setActive] = useState<Notebook | null>(null);
  const [newName, setNewName] = useState("");
  const [picker, setPicker] = useState<Set<string>>(new Set());
  const [question, setQuestion] = useState("");
  const [answer, setAnswer] = useState<NotebookAnswer | null>(null);
  const [busy, setBusy] = useState(false);
  const [precision, setPrecision] = useState(false);
  const [lastAction, setLastAction] = useState<{ type: "ask"; q: string } | { type: "gen"; kind: string } | null>(null);

  function loadNotebooks() { api.notebooks().then(setNotebooks).catch(() => {}); }
  useEffect(() => { loadNotebooks(); api.documents().then(setDocs).catch(() => {}); }, []);

  function openNb(nb: Notebook) {
    setActive(nb);
    setAnswer(null);
    setQuestion("");
    setPicker(new Set(nb.document_ids));
  }

  async function createNb() {
    const nb = await api.createNotebook({ name: newName.trim() || "Nuevo notebook", document_ids: [] });
    setNewName("");
    loadNotebooks();
    openNb(nb);
  }

  async function saveSources() {
    if (!active) return;
    const nb = await api.updateNotebook(active.id, { name: active.name, document_ids: [...picker] });
    setActive(nb);
    loadNotebooks();
  }

  async function removeNb(id: string) {
    if (!confirm("¿Borrar este notebook? (no borra los documentos)")) return;
    await api.deleteNotebook(id);
    if (active?.id === id) setActive(null);
    loadNotebooks();
  }

  async function ask(approve = false) {
    if (!active || !question.trim()) return;
    setBusy(true); setAnswer(null);
    setLastAction({ type: "ask", q: question.trim() });
    try { setAnswer(await api.notebookAsk(active.id, question.trim(), { precision, approve_external: approve })); }
    finally { setBusy(false); }
  }

  async function generate(kind: string, approve = false) {
    if (!active) return;
    setBusy(true); setAnswer(null);
    setLastAction({ type: "gen", kind });
    try { setAnswer(await api.notebookGenerate(active.id, kind, { precision, approve_external: approve })); }
    finally { setBusy(false); }
  }

  async function approveEscalation() {
    if (!lastAction) return;
    if (lastAction.type === "ask") await ask(true);
    else await generate(lastAction.kind, true);
  }

  function toggle(id: string) {
    setPicker((s) => { const n = new Set(s); n.has(id) ? n.delete(id) : n.add(id); return n; });
  }

  return (
    <Shell>
      <PageHeader title="Notebooks" subtitle="Tu NotebookLM privado: elige fuentes y pregunta o genera artefactos, solo sobre esos documentos." />
      <div className="grid grid-cols-1 gap-6 p-8 lg:grid-cols-4">
        {/* Notebook list */}
        <aside className="space-y-2 lg:col-span-1">
          <div className="flex gap-2">
            <input value={newName} onChange={(e) => setNewName(e.target.value)} placeholder="Nuevo notebook…"
              className="flex-1 rounded-lg border border-slate-300 px-3 py-2 text-sm" />
            <button onClick={createNb} className="rounded-lg bg-violet-600 px-3 text-sm font-semibold text-white"><Plus className="h-4 w-4" /></button>
          </div>
          {notebooks.map((nb) => (
            <div key={nb.id} className={`flex items-center justify-between rounded-xl border p-3 ${active?.id === nb.id ? "border-violet-400 bg-violet-50" : "border-slate-200 bg-white"}`}>
              <button onClick={() => openNb(nb)} className="flex-1 text-left">
                <div className="text-sm font-semibold text-slate-800">{nb.name}</div>
                <div className="text-xs text-slate-400">{nb.document_ids.length} fuente(s)</div>
              </button>
              <button onClick={() => removeNb(nb.id)} className="text-slate-300 hover:text-red-600"><Trash2 className="h-4 w-4" /></button>
            </div>
          ))}
          {notebooks.length === 0 && <p className="text-xs text-slate-400">Crea tu primer notebook.</p>}
        </aside>

        {/* Active notebook */}
        <section className="lg:col-span-3">
          {!active ? (
            <div className="rounded-2xl border border-dashed border-slate-300 bg-white p-10 text-center text-sm text-slate-400">
              <BookOpen className="mx-auto mb-2 h-6 w-6 text-slate-300" />
              Selecciona o crea un notebook para empezar.
            </div>
          ) : (
            <div className="space-y-5">
              {/* Sources */}
              <div className="rounded-2xl border border-slate-200 bg-white p-5">
                <h2 className="mb-2 font-semibold text-slate-800">Fuentes de «{active.name}»</h2>
                <div className="grid max-h-44 grid-cols-1 gap-1 overflow-auto sm:grid-cols-2">
                  {docs.map((d) => (
                    <label key={d.id} className="flex cursor-pointer items-center gap-2 rounded-md px-2 py-1 text-sm hover:bg-slate-50">
                      <input type="checkbox" checked={picker.has(d.id)} onChange={() => toggle(d.id)} />
                      <span className="truncate text-slate-700">{d.filename}</span>
                    </label>
                  ))}
                  {docs.length === 0 && <p className="text-xs text-slate-400">Sube documentos en «Documentos» primero.</p>}
                </div>
                <button onClick={saveSources} className="mt-3 rounded-lg bg-slate-900 px-4 py-2 text-sm font-semibold text-white">
                  Guardar fuentes ({picker.size})
                </button>
              </div>

              {/* Artifacts + ask */}
              <div className="rounded-2xl border border-slate-200 bg-white p-5">
                <div className="mb-3 flex flex-wrap gap-2">
                  {ARTIFACTS.map((a) => (
                    <button key={a.kind} onClick={() => generate(a.kind)} disabled={busy || active.document_ids.length === 0}
                      className="flex items-center gap-1.5 rounded-lg border border-violet-200 bg-violet-50 px-3 py-1.5 text-xs font-semibold text-violet-700 disabled:opacity-50">
                      <Sparkles className="h-3.5 w-3.5" /> {a.label}
                    </button>
                  ))}
                </div>
                <label className="mb-2 flex w-fit cursor-pointer items-center gap-1.5 text-xs text-slate-600">
                  <input type="checkbox" checked={precision} onChange={(e) => setPrecision(e.target.checked)} />
                  <Sparkles className="h-3.5 w-3.5 text-violet-600" /> Máxima precisión (refina con modelo premium)
                </label>
                <div className="flex gap-2">
                  <input value={question} onChange={(e) => setQuestion(e.target.value)}
                    onKeyDown={(e) => e.key === "Enter" && ask()}
                    placeholder="Pregunta sobre tus fuentes…" className="flex-1 rounded-lg border border-slate-300 px-3 py-2 text-sm" />
                  <button onClick={() => ask()} disabled={busy || !question.trim()}
                    className="flex items-center gap-1.5 rounded-lg bg-violet-600 px-4 py-2 text-sm font-semibold text-white disabled:opacity-50">
                    <Send className="h-4 w-4" /> Preguntar
                  </button>
                </div>
                {busy && <p className="mt-3 text-sm text-slate-400">Procesando con el router de privacidad…</p>}

                {answer && (
                  <div className="mt-4">
                    {answer.empty ? (
                      <p className="text-sm text-amber-600">{answer.message}</p>
                    ) : (
                      <>
                        {answer.escalation_pending && (
                          <div className="mb-2 rounded-lg border border-amber-200 bg-amber-50 px-3 py-2 text-xs text-amber-800">
                            Contenido sensible. ¿Refinar con el modelo premium (envío externo con PII redactada)?
                            <button onClick={approveEscalation} disabled={busy}
                              className="ml-2 rounded-md bg-amber-600 px-2 py-1 font-semibold text-white disabled:opacity-50">Aprobar y refinar</button>
                          </div>
                        )}
                        {answer.escalated && (
                          <div className="mb-2 inline-flex items-center gap-1 rounded-full bg-violet-100 px-2 py-0.5 text-xs font-semibold text-violet-700">
                            <Sparkles className="h-3 w-3" /> Refinado con premium
                          </div>
                        )}
                        <div className="whitespace-pre-wrap rounded-lg border border-slate-200 bg-slate-50 p-4 text-sm text-slate-700">{answer.content}</div>
                        {answer.citations.length > 0 && (
                          <div className="mt-3">
                            <div className="mb-1 text-xs font-semibold uppercase text-slate-400">Fuentes citadas</div>
                            <div className="space-y-1">
                              {answer.citations.map((c, i) => (
                                <div key={i} className="rounded-lg border border-slate-100 bg-white px-3 py-2 text-xs text-slate-500">
                                  <span className="font-medium text-slate-600">{c.filename}</span> · {c.text.slice(0, 160)}…
                                </div>
                              ))}
                            </div>
                          </div>
                        )}
                      </>
                    )}
                  </div>
                )}
              </div>
            </div>
          )}
        </section>
      </div>
    </Shell>
  );
}
