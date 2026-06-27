"use client";

import { PageHeader, Shell } from "@/components/Shell";
import { api } from "@/lib/api";
import { cleanMarkdown } from "@/lib/format";
import type { CompanyProfile, DocumentItem, Recipe, RecipeRun } from "@shared/types";
import { Building2, CheckCircle2, ChevronLeft, Download, FileText, Link2, MessageCircle, Sparkles } from "lucide-react";
import Link from "next/link";
import { useEffect, useState } from "react";

export default function RecipesPage() {
  const [recipes, setRecipes] = useState<Recipe[]>([]);
  const [categories, setCategories] = useState<{ id: string; label: string; count: number }[]>([]);
  const [cat, setCat] = useState<string>("");
  const [q, setQ] = useState("");
  const [docs, setDocs] = useState<DocumentItem[]>([]);
  const [docCats, setDocCats] = useState<{ key: string; label: string }[]>([]);
  const [mailboxes, setMailboxes] = useState<{ id: string; provider: string; label: string; identifier: string }[]>([]);
  const [profile, setProfile] = useState<CompanyProfile | null>(null);
  const [active, setActive] = useState<Recipe | null>(null);
  const [inputs, setInputs] = useState<Record<string, string>>({});
  const [run, setRun] = useState<RecipeRun | null>(null);
  const [busy, setBusy] = useState(false);
  const [error, setError] = useState("");
  const [propTitle, setPropTitle] = useState("");
  const [propMsg, setPropMsg] = useState("");
  const [waMsg, setWaMsg] = useState("");

  async function sendResultToWhatsapp() {
    if (!run) return;
    const text = (run.result?.documento as string) || (run.result?.message as string) || "";
    setWaMsg("Enviando…");
    try {
      await api.sendWhatsapp(cleanMarkdown(text).slice(0, 900));
      setWaMsg("Enviado a tu WhatsApp ✅");
    } catch (e) {
      const m = e instanceof Error ? e.message : "Error";
      setWaMsg(m.includes("Configura") ? "Configura WhatsApp en Alertas → WhatsApp y vuelve a intentar." : m);
    }
  }

  useEffect(() => {
    api.recipeCategories().then(setCategories).catch(() => {});
    api.documents().then(setDocs).catch(() => {});
    api.documentCategories().then((cs) => setDocCats(cs.map((c) => ({ key: c.key, label: c.label })))).catch(() => {});
    api.companyProfile().then(setProfile).catch(() => {});
    api.oauthProviders()
      .then((r) => setMailboxes(r.connections))
      .catch(() => {});
  }, []);

  useEffect(() => {
    api.recipes({ category: cat || undefined, q: q || undefined })
      .then(setRecipes)
      .catch((e) => setError(e.message));
  }, [cat, q]);

  // Default the mailbox field to the first connected account so there's always a
  // visible, explicit selection the user can change (instead of a silent fallback).
  useEffect(() => {
    if (!active || mailboxes.length === 0) return;
    const mf = active.inputs.find((f) => f.type === "mailbox");
    if (mf && !inputs[mf.key]) setInputs((s) => ({ ...s, [mf.key]: mailboxes[0].id }));
  }, [active, mailboxes]);

  async function propose() {
    if (!propTitle.trim()) return;
    await api.proposeRecipe({ title: propTitle, category: cat || "dia_a_dia" });
    setPropTitle("");
    setPropMsg("¡Gracias! Tu caso fue enviado y entrará a revisión para el catálogo.");
  }

  const locked = profile?.required_complete === false;

  function open(r: Recipe) {
    if (locked) return; // onboarding baseline required first
    setActive(r);
    setRun(null);
    setError("");
    setInputs({});
  }

  async function start(extra?: Record<string, string>) {
    if (!active) return;
    setBusy(true);
    setError("");
    try {
      setRun(await api.startRecipe(active.id, { ...inputs, ...(extra || {}) }));
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

        {/* Mandatory onboarding gate: block the use cases until the baseline is set. */}
        {!active && locked && (
          <Link
            href="/company"
            className="mb-5 flex items-center gap-3 rounded-2xl border border-amber-300 bg-amber-50 p-4 transition hover:border-amber-400"
          >
            <div className="flex h-10 w-10 flex-shrink-0 items-center justify-center rounded-lg bg-white">
              <Building2 className="h-5 w-5 text-amber-600" />
            </div>
            <div className="flex-1">
              <div className="text-sm font-semibold text-amber-900">
                Completa la información base de tu empresa para habilitar los casos de uso
              </div>
              <p className="text-xs text-amber-700">
                Es obligatoria para obtener resultados confiables. Falta:{" "}
                <b>{(profile?.missing_required || []).join(", ")}</b>. Toca aquí para completarla →
              </p>
            </div>
          </Link>
        )}

        {!active && !locked && profile && profile.completion < 100 && (
          <Link
            href="/company"
            className="mb-5 flex items-center gap-3 rounded-2xl border border-violet-200 bg-violet-50 p-4 transition hover:border-violet-400"
          >
            <div className="flex h-10 w-10 flex-shrink-0 items-center justify-center rounded-lg bg-white">
              <Building2 className="h-5 w-5 text-violet-600" />
            </div>
            <div className="flex-1">
              <div className="text-sm font-semibold text-violet-900">
                Configura tu empresa para mejores resultados ({profile.completion}%)
              </div>
              <p className="text-xs text-violet-700">
                Con el contexto de tu empresa (giro, áreas, tecnología) los casos de uso quedan
                preconfigurados y los documentos salen más completos. →
              </p>
            </div>
          </Link>
        )}

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
                  disabled={locked}
                  title={locked ? "Completa la información base de tu empresa para habilitar este caso" : undefined}
                  className={`rounded-2xl border border-slate-200 bg-white p-5 text-left transition hover:border-violet-400 hover:shadow-sm ${locked ? "cursor-not-allowed opacity-50 hover:border-slate-200 hover:shadow-none" : ""}`}
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

              {active.rag_category && (
                <div className="mt-3 flex items-center gap-2 rounded-lg border border-violet-200 bg-violet-50 px-3 py-2 text-xs text-violet-800">
                  <FileText className="h-4 w-4 flex-shrink-0" />
                  <span>
                    Se apoya en tus documentos de categoría{" "}
                    <b>{docCats.find((c) => c.key === active.rag_category)?.label || active.rag_category}</b>.{" "}
                    <Link href="/documents" className="font-semibold underline">Súbelos en Documentos</Link> para mejores resultados.
                  </span>
                </div>
              )}

              {/* Step 1: minimal inputs */}
              {!run && (
                <div className="mt-5 space-y-4">
                  {/* Universal intent step: goal + notes + output format (shapes every case). */}
                  <div className="rounded-xl border border-slate-200 bg-slate-50 p-4 space-y-3">
                    <div>
                      <label className="mb-1 block text-sm font-medium text-slate-700">¿Qué quieres lograr? (objetivo)</label>
                      <textarea rows={2} value={inputs.objetivo || ""} placeholder="Ej. Cerrar al cliente con una propuesta clara y persuasiva…"
                        onChange={(e) => setInputs((s) => ({ ...s, objetivo: e.target.value }))}
                        className="w-full rounded-lg border border-slate-300 px-3 py-2 text-sm" />
                    </div>
                    <div>
                      <label className="mb-1 block text-sm font-medium text-slate-700">Notas / lo que te interesa incluir</label>
                      <textarea rows={2} value={inputs.notas || ""} placeholder="Datos, tono, puntos a destacar, lo que NO quieres…"
                        onChange={(e) => setInputs((s) => ({ ...s, notas: e.target.value }))}
                        className="w-full rounded-lg border border-slate-300 px-3 py-2 text-sm" />
                    </div>
                    <div>
                      <label className="mb-1 block text-sm font-medium text-slate-700">Formato de salida</label>
                      <select value={inputs.formato || ""} onChange={(e) => setInputs((s) => ({ ...s, formato: e.target.value }))}
                        className="w-full rounded-lg border border-slate-300 px-3 py-2 text-sm">
                        <option value="">Predeterminado</option>
                        <option value="documento_formal">Documento formal</option>
                        <option value="resumen_ejecutivo">Resumen ejecutivo (bullets)</option>
                        <option value="tabla">Tabla</option>
                        <option value="presentacion">Presentación (esquema)</option>
                        <option value="carta">Carta / comunicado</option>
                        <option value="personalizado">Diseñar con AI (describe abajo)</option>
                      </select>
                      {inputs.formato === "personalizado" && (
                        <textarea rows={2} value={inputs.formato_notas || ""} placeholder="Describe el formato que quieres y lo armo…"
                          onChange={(e) => setInputs((s) => ({ ...s, formato_notas: e.target.value }))}
                          className="mt-2 w-full rounded-lg border border-slate-300 px-3 py-2 text-sm" />
                      )}
                    </div>
                    <label className="flex cursor-pointer items-center gap-2 text-sm text-slate-700">
                      <input type="checkbox" checked={inputs.precision === "1"}
                        onChange={(e) => setInputs((s) => ({ ...s, precision: e.target.checked ? "1" : "" }))} />
                      <FileText className="h-4 w-4 text-violet-600" /> Máxima precisión (refina con modelo premium)
                      {active.rag_category && active.advanced && <span className="text-xs text-violet-500">· este caso ya usa premium</span>}
                    </label>
                  </div>
                  {active.inputs.map((f) => {
                    const cls = "w-full rounded-lg border border-slate-300 px-3 py-2 text-sm";
                    const val = inputs[f.key] || "";
                    const onChange = (v: string) => setInputs((s) => ({ ...s, [f.key]: v }));
                    const areaOptions = (profile?.areas || []).map((a) => a.name).filter(Boolean);
                    return (
                      <div key={f.key}>
                        <label className="mb-1 block text-sm font-medium text-slate-700">
                          {f.label}
                          {f.required && <span className="text-red-500"> *</span>}
                        </label>
                        {f.type === "mailbox" ? (
                          mailboxes.length > 0 ? (
                            <select value={val} onChange={(e) => onChange(e.target.value)} className={cls}>
                              <option value="">Elige una cuenta…</option>
                              {mailboxes.map((m) => (
                                <option key={m.id} value={m.id}>
                                  {m.identifier} — {m.label}
                                </option>
                              ))}
                            </select>
                          ) : (
                            <div className="rounded-lg border border-amber-200 bg-amber-50 px-3 py-2 text-sm text-amber-700">
                              No tienes cuentas conectadas.{" "}
                              <Link href="/integrations" className="font-semibold underline">
                                Conecta tu correo
                              </Link>{" "}
                              (Outlook, Gmail o IMAP) para usar este caso.
                            </div>
                          )
                        ) : f.type === "document" ? (
                          <select value={val} onChange={(e) => onChange(e.target.value)} className={cls}>
                            <option value="">Selecciona un documento…</option>
                            {docs.map((d) => <option key={d.id} value={d.id}>{d.filename}</option>)}
                          </select>
                        ) : f.type === "choice" ? (
                          <select value={val} onChange={(e) => onChange(e.target.value)} className={cls}>
                            <option value="">Elige…</option>
                            {f.options?.map((o) => <option key={o} value={o}>{o}</option>)}
                          </select>
                        ) : f.type === "area" ? (
                          areaOptions.length > 0 ? (
                            <select value={val} onChange={(e) => onChange(e.target.value)} className={cls}>
                              <option value="">Selecciona un área…</option>
                              {areaOptions.map((o) => <option key={o} value={o}>{o}</option>)}
                            </select>
                          ) : (
                            <input value={val} placeholder={f.placeholder} onChange={(e) => onChange(e.target.value)} className={cls} />
                          )
                        ) : f.type === "textarea" ? (
                          <textarea rows={3} value={val} placeholder={f.placeholder}
                            onChange={(e) => onChange(e.target.value)} className={cls} />
                        ) : (
                          <input
                            type={f.type === "email" ? "email" : f.type === "number" ? "number" : f.type === "date" ? "date" : "text"}
                            value={val}
                            placeholder={f.placeholder}
                            onChange={(e) => onChange(e.target.value)}
                            className={cls}
                          />
                        )}
                        {f.help && <p className="mt-1 text-xs text-slate-400">{f.help}</p>}
                      </div>
                    );
                  })}
                  <button
                    onClick={() => start()}
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

                  {run.draft?.escalation_pending === true && (
                    <div className="rounded-lg border border-amber-200 bg-amber-50 px-4 py-3 text-sm text-amber-800">
                      Para máxima precisión puedo refinarlo con un modelo premium, pero el contenido es sensible.
                      <button onClick={() => start({ precision: "1", approve_external: "1" })} disabled={busy}
                        className="ml-2 rounded-md bg-amber-600 px-3 py-1 text-xs font-semibold text-white disabled:opacity-50">
                        Aprobar y refinar
                      </button>
                    </div>
                  )}

                  {Array.isArray(run.draft?.fuentes) && (run.draft.fuentes as { title: string; authority: string; source?: string }[]).length > 0 && (
                    <div className="rounded-lg border border-slate-200 bg-slate-50 px-3 py-2 text-xs text-slate-500">
                      <span className="font-semibold text-slate-600">Fuentes (MCP de trámites): </span>
                      {(run.draft.fuentes as { title: string; authority: string; source?: string }[])
                        .map((f) => `${f.title}${f.source?.startsWith("empresa") ? (f.source === "empresa-rag" ? " (empresa·RAG)" : " (empresa)") : ""}`)
                        .join(" · ")}
                    </div>
                  )}

                  {typeof run.draft?.contenido === "string" && run.draft.contenido && (
                    <div>
                      <div className="mb-1 text-xs font-semibold uppercase text-slate-400">Borrador generado (revisa)</div>
                      <pre className="max-h-72 overflow-auto whitespace-pre-wrap rounded-lg border border-slate-200 bg-slate-50 p-3 text-sm text-slate-700">
                        {cleanMarkdown(run.draft.contenido as string)}
                      </pre>
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
                          {cleanMarkdown(run.result.documento as string)}
                        </pre>
                      )}
                      <div className="mt-3 flex flex-wrap gap-2">
                        <button
                          onClick={() => api.downloadRun(run.id, "docx")}
                          className="flex items-center gap-1.5 rounded-lg bg-violet-600 px-3 py-1.5 text-xs font-semibold text-white hover:bg-violet-700"
                        >
                          <Download className="h-4 w-4" /> Descargar Word
                        </button>
                        <button
                          onClick={() => api.downloadRun(run.id, "pdf")}
                          className="flex items-center gap-1.5 rounded-lg bg-slate-900 px-3 py-1.5 text-xs font-semibold text-white"
                        >
                          <Download className="h-4 w-4" /> PDF
                        </button>
                        <button
                          onClick={() => api.downloadRun(run.id, "pptx")}
                          className="flex items-center gap-1.5 rounded-lg bg-orange-600 px-3 py-1.5 text-xs font-semibold text-white hover:bg-orange-700"
                        >
                          <Download className="h-4 w-4" /> PowerPoint
                        </button>
                        <button
                          onClick={() => api.downloadRun(run.id, "xlsx")}
                          className="flex items-center gap-1.5 rounded-lg bg-green-700 px-3 py-1.5 text-xs font-semibold text-white hover:bg-green-800"
                        >
                          <Download className="h-4 w-4" /> Excel
                        </button>
                        <button
                          onClick={() => api.downloadRun(run.id, "md")}
                          className="rounded-lg border border-slate-300 px-3 py-1.5 text-xs font-semibold text-slate-600"
                        >
                          Markdown
                        </button>
                        <button
                          onClick={sendResultToWhatsapp}
                          className="flex items-center gap-1.5 rounded-lg bg-[#25D366] px-3 py-1.5 text-xs font-semibold text-white hover:brightness-95"
                        >
                          <MessageCircle className="h-4 w-4" /> Enviar a WhatsApp
                        </button>
                      </div>
                      {waMsg && <p className="mt-2 text-xs text-slate-500">{waMsg}</p>}
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
