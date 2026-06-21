"use client";

import { PageHeader, Shell } from "@/components/Shell";
import { api } from "@/lib/api";
import type { DocumentItem, Recipe, RecipeRun } from "@shared/types";
import { CheckCircle2, ChevronLeft, Link2, Sparkles } from "lucide-react";
import { useEffect, useState } from "react";

export default function RecipesPage() {
  const [recipes, setRecipes] = useState<Recipe[]>([]);
  const [categories, setCategories] = useState<{ id: string; label: string; count: number }[]>([]);
  const [cat, setCat] = useState<string>("");
  const [q, setQ] = useState("");
  const [docs, setDocs] = useState<DocumentItem[]>([]);
  const [active, setActive] = useState<Recipe | null>(null);
  const [inputs, setInputs] = useState<Record<string, string>>({});
  const [run, setRun] = useState<RecipeRun | null>(null);
  const [busy, setBusy] = useState(false);
  const [error, setError] = useState("");
  const [propTitle, setPropTitle] = useState("");
  const [propMsg, setPropMsg] = useState("");

  useEffect(() => {
    api.recipeCategories().then(setCategories).catch(() => {});
    api.documents().then(setDocs).catch(() => {});
  }, []);

  useEffect(() => {
    api.recipes({ category: cat || undefined, q: q || undefined })
      .then(setRecipes)
      .catch((e) => setError(e.message));
  }, [cat, q]);

  async function propose() {
    if (!propTitle.trim()) return;
    await api.proposeRecipe({ title: propTitle, category: cat || "dia_a_dia" });
    setPropTitle("");
    setPropMsg("¡Gracias! Tu caso fue enviado y entrará a revisión para el catálogo.");
  }

  function open(r: Recipe) {
    setActive(r);
    setRun(null);
    setError("");
    setInputs({});
  }

  async function start() {
    if (!active) return;
    setBusy(true);
    setError("");
    try {
      setRun(await api.startRecipe(active.id, inputs));
    } catch (e) {
      setError(e instanceof Error ? e.message : "Error");
    } finally {
      setBusy(false);
    }
  }

  async function approveConnection(id: string) {
    await api.approveConnection(id);
    if (run) setRun(await api.recipeRun(run.id));
  }

  async function approveRun() {
    if (!run) return;
    setBusy(true);
    setError("");
    try {
      setRun(await api.approveRun(run.id));
    } catch (e) {
      setError(e instanceof Error ? e.message : "Aprueba primero la conexión.");
      setRun(await api.recipeRun(run.id));
    } finally {
      setBusy(false);
    }
  }

  return (
    <Shell>
      <PageHeader
        title="Casos de uso"
        subtitle="Elige qué quieres lograr, da lo mínimo y la plataforma hace el resto. Tú solo apruebas."
      />
      <div className="p-8">
        {error && <div className="mb-4 rounded-lg bg-red-50 px-4 py-2 text-sm text-red-700">{error}</div>}

        {!active && (
          <>
            <div className="mb-5 flex flex-wrap items-center gap-2">
              <input
                value={q}
                onChange={(e) => setQ(e.target.value)}
                placeholder="Busca lo que quieres lograr…"
                className="w-full max-w-sm rounded-lg border border-slate-300 px-3 py-2 text-sm"
              />
              <button
                onClick={() => setCat("")}
                className={`rounded-full px-3 py-1 text-xs font-medium ${cat === "" ? "bg-violet-600 text-white" : "bg-white text-slate-600 ring-1 ring-slate-200"}`}
              >
                Todos
              </button>
              {categories.map((c) => (
                <button
                  key={c.id}
                  onClick={() => setCat(c.id)}
                  className={`rounded-full px-3 py-1 text-xs font-medium ${cat === c.id ? "bg-violet-600 text-white" : "bg-white text-slate-600 ring-1 ring-slate-200"}`}
                >
                  {c.label} <span className="opacity-60">{c.count}</span>
                </button>
              ))}
            </div>

            <div className="grid gap-4 sm:grid-cols-2 lg:grid-cols-3">
              {recipes.map((r) => (
                <button
                  key={r.id}
                  onClick={() => open(r)}
                  className="rounded-2xl border border-slate-200 bg-white p-5 text-left transition hover:border-violet-400 hover:shadow-sm"
                >
                  <div className="mb-3 flex h-10 w-10 items-center justify-center rounded-lg bg-violet-50">
                    <Sparkles className="h-5 w-5 text-violet-600" />
                  </div>
                  <div className="font-semibold text-slate-800">{r.name}</div>
                  <p className="mt-1 text-sm text-slate-500">{r.description}</p>
                </button>
              ))}
            </div>

            <div className="mt-8 rounded-2xl border border-dashed border-slate-300 bg-white p-5">
              <div className="font-semibold text-slate-800">¿No encuentras tu caso? Propónlo</div>
              <p className="mt-1 text-sm text-slate-500">
                Tú nos dices qué necesitas y lo añadimos al catálogo. Construimos miles de casos para
                negocios de todos los tamaños.
              </p>
              <div className="mt-3 flex flex-wrap gap-2">
                <input
                  value={propTitle}
                  onChange={(e) => setPropTitle(e.target.value)}
                  placeholder="Ej. Recordatorio de pagos a proveedores"
                  className="w-full max-w-md rounded-lg border border-slate-300 px-3 py-2 text-sm"
                />
                <button
                  onClick={propose}
                  className="rounded-lg bg-slate-900 px-4 py-2 text-sm font-semibold text-white"
                >
                  Proponer caso
                </button>
              </div>
              {propMsg && <div className="mt-2 text-xs text-emerald-600">{propMsg}</div>}
            </div>
          </>
        )}

        {active && (
          <div className="mx-auto max-w-2xl">
            <button
              onClick={() => setActive(null)}
              className="mb-4 flex items-center gap-1 text-sm text-slate-500 hover:text-slate-700"
            >
              <ChevronLeft className="h-4 w-4" /> Volver a casos de uso
            </button>

            <div className="rounded-2xl border border-slate-200 bg-white p-6">
              <h2 className="font-semibold text-slate-800">{active.name}</h2>
              <p className="mt-1 text-sm text-slate-500">{active.description}</p>

              {/* Step 1: minimal inputs */}
              {!run && (
                <div className="mt-5 space-y-4">
                  {active.inputs.map((f) => (
                    <div key={f.key}>
                      <label className="mb-1 block text-sm font-medium text-slate-700">{f.label}</label>
                      {f.type === "document" ? (
                        <select
                          value={inputs[f.key] || ""}
                          onChange={(e) => setInputs((s) => ({ ...s, [f.key]: e.target.value }))}
                          className="w-full rounded-lg border border-slate-300 px-3 py-2 text-sm"
                        >
                          <option value="">Selecciona un documento…</option>
                          {docs.map((d) => (
                            <option key={d.id} value={d.id}>{d.filename}</option>
                          ))}
                        </select>
                      ) : f.type === "choice" ? (
                        <select
                          value={inputs[f.key] || ""}
                          onChange={(e) => setInputs((s) => ({ ...s, [f.key]: e.target.value }))}
                          className="w-full rounded-lg border border-slate-300 px-3 py-2 text-sm"
                        >
                          <option value="">Elige…</option>
                          {f.options?.map((o) => <option key={o} value={o}>{o}</option>)}
                        </select>
                      ) : (
                        <input
                          type={f.type === "email" ? "email" : "text"}
                          value={inputs[f.key] || ""}
                          onChange={(e) => setInputs((s) => ({ ...s, [f.key]: e.target.value }))}
                          className="w-full rounded-lg border border-slate-300 px-3 py-2 text-sm"
                        />
                      )}
                    </div>
                  ))}
                  <button
                    onClick={start}
                    disabled={busy}
                    className="rounded-lg bg-violet-600 px-4 py-2 text-sm font-semibold text-white disabled:opacity-50"
                  >
                    {busy ? "Pre-llenando…" : "Pre-llenar con IA"}
                  </button>
                </div>
              )}

              {/* Step 2: AI draft + approval gates */}
              {run && (
                <div className="mt-5 space-y-4">
                  {run.draft?.summary && (
                    <div className="rounded-lg border border-violet-200 bg-violet-50 px-4 py-3 text-sm text-violet-800">
                      {run.draft.summary as string}
                    </div>
                  )}

                  {Array.isArray(run.draft?.campos) && (
                    <div className="space-y-2">
                      <div className="text-xs font-semibold uppercase text-slate-400">Pre-llenado (revisa)</div>
                      {run.draft.campos!.map((c, i) => (
                        <div key={i} className="rounded-lg border border-slate-200 p-3 text-sm">
                          <div className="font-medium text-slate-700">{c.requisito}</div>
                          <div className="mt-1 text-slate-500">{c.respuesta_sugerida}</div>
                        </div>
                      ))}
                    </div>
                  )}

                  {run.connections.length > 0 && run.status !== "completed" && (
                    <div className="space-y-2">
                      <div className="text-xs font-semibold uppercase text-slate-400">Aprueba la conexión</div>
                      {run.connections.map((c) => (
                        <div key={c.id} className="flex items-center justify-between rounded-lg border border-slate-200 p-3 text-sm">
                          <span className="flex items-center gap-2 text-slate-700">
                            <Link2 className="h-4 w-4 text-slate-400" /> {c.label || c.provider}
                            {c.identifier && <span className="text-slate-400">· {c.identifier}</span>}
                          </span>
                          {c.status === "approved" ? (
                            <span className="flex items-center gap-1 text-emerald-600">
                              <CheckCircle2 className="h-4 w-4" /> Aprobada
                            </span>
                          ) : (
                            <button
                              onClick={() => approveConnection(c.id)}
                              className="rounded-md bg-slate-900 px-3 py-1 text-xs font-semibold text-white"
                            >
                              Aprobar conexión
                            </button>
                          )}
                        </div>
                      ))}
                    </div>
                  )}

                  {run.status === "completed" ? (
                    <div className="rounded-lg border border-emerald-200 bg-emerald-50 p-4">
                      <div className="flex items-center gap-2 font-semibold text-emerald-700">
                        <CheckCircle2 className="h-5 w-5" /> Listo
                      </div>
                      <p className="mt-1 text-sm text-emerald-700">{run.result?.message}</p>
                      {run.result?.documento && (
                        <pre className="mt-3 max-h-64 overflow-auto whitespace-pre-wrap rounded-lg bg-white p-3 text-xs text-slate-600">
                          {run.result.documento as string}
                        </pre>
                      )}
                    </div>
                  ) : (
                    <button
                      onClick={approveRun}
                      disabled={busy}
                      className="rounded-lg bg-emerald-600 px-4 py-2 text-sm font-semibold text-white disabled:opacity-50"
                    >
                      {busy ? "Ejecutando…" : run.approve_label}
                    </button>
                  )}
                </div>
              )}
            </div>
          </div>
        )}
      </div>
    </Shell>
  );
}
