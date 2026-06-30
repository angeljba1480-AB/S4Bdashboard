"use client";

import { ExportMenu } from "@/components/ExportMenu";
import { PageHeader, Shell } from "@/components/Shell";
import { api } from "@/lib/api";
import { Search, ShieldAlert, Trash2 } from "lucide-react";
import { useEffect, useState } from "react";

type KErr = Awaited<ReturnType<typeof api.kedb>>[number];
const SEV: Record<string, string> = { low: "bg-slate-100 text-slate-600", medium: "bg-amber-100 text-amber-700", high: "bg-orange-100 text-orange-700", critical: "bg-red-100 text-red-700" };

export default function KedbPage() {
  const [enabled, setEnabled] = useState<boolean | null>(null);
  const [items, setItems] = useState<KErr[]>([]);
  const [q, setQ] = useState("");
  const [form, setForm] = useState({ title: "", symptom: "", cause: "", resolution: "", product: "", severity: "medium", tags: "" });
  const [analysis, setAnalysis] = useState<Awaited<ReturnType<typeof api.analyzeKedb>> | null>(null);
  const [symptom, setSymptom] = useState("");
  const [msg, setMsg] = useState("");
  const [proposals, setProposals] = useState<Awaited<ReturnType<typeof api.kedbProposals>>>([]);
  const [isOperator, setIsOperator] = useState(false);
  const [extractText, setExtractText] = useState("");

  function load() { api.kedb(q ? { q } : undefined).then(setItems).catch(() => {}); }
  function loadProposals() { api.kedbProposals().then((p) => { setProposals(p); setIsOperator(true); }).catch(() => setIsOperator(false)); }
  useEffect(() => { api.kedbStatus().then((s) => setEnabled(s.enabled)).catch(() => setEnabled(false)); }, []);
  useEffect(() => { if (enabled) { load(); loadProposals(); } /* eslint-disable-next-line */ }, [enabled, q]);

  async function promote(id: string) {
    setMsg("Sanitizando y proponiendo…");
    try { await api.promoteKnownError(id); setMsg("✓ Propuesta enviada al operador para aprobación cross-cliente."); }
    catch (e) { setMsg(e instanceof Error ? e.message : "Error"); }
  }
  async function approveProp(id: string) { await api.approveKedbProposal(id); loadProposals(); load(); }
  async function rejectProp(id: string) { await api.rejectKedbProposal(id); loadProposals(); }
  async function doExtract() {
    if (!extractText.trim()) return;
    setMsg("Extrayendo…");
    try {
      const r = await api.extractKedb(extractText);
      setForm({ ...form, ...r.draft, tags: r.draft.tags || "" });
      setMsg("✓ Borrador extraído — revísalo en 'Agregar error conocido' y guarda.");
    } catch (e) { setMsg(e instanceof Error ? e.message : "Error"); }
  }

  async function create() {
    if (!form.title.trim()) { setMsg("El título es obligatorio."); return; }
    try {
      await api.createKnownError({ ...form, tags: form.tags.split(",").map((t) => t.trim()).filter(Boolean) });
      setForm({ title: "", symptom: "", cause: "", resolution: "", product: "", severity: "medium", tags: "" });
      setMsg("✓ Error conocido agregado."); load();
    } catch (e) { setMsg(e instanceof Error ? e.message : "Error"); }
  }
  async function analyze() {
    if (!symptom.trim()) return;
    setAnalysis(null);
    try { setAnalysis(await api.analyzeKedb(symptom)); } catch (e) { setMsg(e instanceof Error ? e.message : "Error"); }
  }
  async function remove(id: string) { await api.deleteKnownError(id); load(); }

  if (enabled === false) return (
    <Shell>
      <PageHeader title="Errores conocidos (KEDB)" subtitle="Módulo de operación de ciberseguridad" />
      <div className="p-8">
        <div className="rounded-2xl border border-amber-200 bg-amber-50 p-6 text-sm text-amber-800">
          <ShieldAlert className="mb-2 h-6 w-6" />
          Este módulo está disponible solo para empresas con <b>perfil de ciberseguridad</b>.
          Define el giro de tu empresa (industria) en <b>Configuración → Empresa</b> con un valor como
          “Ciberseguridad / SOC” para habilitarlo.
        </div>
      </div>
    </Shell>
  );

  return (
    <Shell>
      <PageHeader title="Errores conocidos (KEDB)" subtitle="Base de errores conocidos del SOC: diagnostica más rápido reusando casos previos." />
      <div className="space-y-6 p-8">
        {msg && <div className="rounded-lg bg-slate-100 px-4 py-2 text-sm text-slate-600">{msg}</div>}

        {/* Analizar síntoma */}
        <div className="rounded-2xl border border-slate-200 bg-white p-5">
          <h2 className="mb-3 flex items-center gap-2 font-semibold text-slate-800"><Search className="h-4 w-4 text-violet-600" /> Analizar un síntoma</h2>
          <div className="flex gap-2">
            <input value={symptom} onChange={(e) => setSymptom(e.target.value)} placeholder="Describe el síntoma observado…" className="flex-1 rounded-lg border border-slate-300 px-3 py-2 text-sm" />
            <button onClick={analyze} className="rounded-lg bg-violet-600 px-4 py-2 text-sm font-semibold text-white">Analizar</button>
          </div>
          {analysis && (
            <div className="mt-3 rounded-lg border border-slate-100 bg-slate-50 p-3 text-sm">
              <div className="mb-1 flex items-center justify-between font-semibold text-slate-700">
                <span>{analysis.is_known ? "✓ Coincide con error(es) conocido(s)" : "Sin coincidencia clara"}</span>
                {(analysis.suggestion || analysis.matches.length > 0) && (
                  <ExportMenu compact title={`Diagnóstico — ${symptom.slice(0, 40)}`}
                    content={`Síntoma: ${symptom}\n\n${analysis.suggestion}\n\nErrores conocidos relacionados:\n` + analysis.matches.map((m) => `• ${m.title}: ${m.resolution}`).join("\n")} />
                )}
              </div>
              {analysis.suggestion && <p className="mb-2 whitespace-pre-wrap text-xs text-slate-600">{analysis.suggestion}</p>}
              {analysis.matches.map((m) => (
                <div key={m.id} className="mt-1 border-t border-slate-200 pt-1 text-xs text-slate-500">
                  <b>{m.title}</b> — {m.resolution}
                </div>
              ))}
            </div>
          )}
        </div>

        {/* Extraer desde texto/log */}
        <details className="rounded-2xl border border-slate-200 bg-white p-5">
          <summary className="cursor-pointer font-semibold text-slate-800">Extraer error desde un texto/log (IA)</summary>
          <div className="mt-3 space-y-2">
            <textarea value={extractText} onChange={(e) => setExtractText(e.target.value)} rows={4}
              placeholder="Pega el texto del incidente / log…" className="w-full rounded-lg border border-slate-300 px-3 py-2 text-sm" />
            <button onClick={doExtract} className="rounded-lg bg-violet-600 px-4 py-2 text-sm font-semibold text-white">Extraer borrador</button>
          </div>
        </details>

        {/* Propuestas cross-cliente (solo operador / super admin) */}
        {isOperator && proposals.length > 0 && (
          <div className="rounded-2xl border border-violet-200 bg-violet-50/40 p-5">
            <h2 className="mb-3 font-semibold text-slate-800">Propuestas cross-cliente (aprobar como operador)</h2>
            <div className="space-y-2">
              {proposals.map((p) => (
                <div key={p.id} className="rounded-xl border border-slate-200 bg-white p-3">
                  <div className="flex items-start justify-between gap-2">
                    <div className="min-w-0">
                      <div className="font-medium text-slate-800">{p.title}</div>
                      <p className="text-xs text-slate-500"><b>Síntoma:</b> {p.symptom} · <b>Resolución:</b> {p.resolution}</p>
                      <p className="mt-0.5 text-[11px] text-slate-400">{p.source}</p>
                    </div>
                    <div className="flex shrink-0 gap-1">
                      <button onClick={() => approveProp(p.id)} className="rounded-md bg-emerald-600 px-2 py-1 text-xs font-semibold text-white">Aprobar</button>
                      <button onClick={() => rejectProp(p.id)} className="rounded-md border border-slate-300 px-2 py-1 text-xs text-slate-600">Rechazar</button>
                    </div>
                  </div>
                </div>
              ))}
            </div>
            <p className="mt-2 text-[11px] text-slate-400">Revisa que esté sanitizado (sin datos del cliente origen) antes de aprobar. Al aprobar, queda visible para todos los clientes con perfil cyber.</p>
          </div>
        )}

        {/* Alta */}
        <details className="rounded-2xl border border-slate-200 bg-white p-5">
          <summary className="cursor-pointer font-semibold text-slate-800">Agregar error conocido</summary>
          <div className="mt-4 grid grid-cols-1 gap-2 sm:grid-cols-2">
            <input value={form.title} onChange={(e) => setForm({ ...form, title: e.target.value })} placeholder="Título" className="rounded-lg border border-slate-300 px-3 py-2 text-sm sm:col-span-2" />
            <input value={form.product} onChange={(e) => setForm({ ...form, product: e.target.value })} placeholder="Producto/sistema (EDR, SIEM, firewall…)" className="rounded-lg border border-slate-300 px-3 py-2 text-sm" />
            <select value={form.severity} onChange={(e) => setForm({ ...form, severity: e.target.value })} className="rounded-lg border border-slate-300 px-3 py-2 text-sm">
              <option value="low">Severidad: baja</option><option value="medium">Severidad: media</option><option value="high">Severidad: alta</option><option value="critical">Severidad: crítica</option>
            </select>
            <input value={form.symptom} onChange={(e) => setForm({ ...form, symptom: e.target.value })} placeholder="Síntoma" className="rounded-lg border border-slate-300 px-3 py-2 text-sm sm:col-span-2" />
            <input value={form.cause} onChange={(e) => setForm({ ...form, cause: e.target.value })} placeholder="Causa raíz" className="rounded-lg border border-slate-300 px-3 py-2 text-sm sm:col-span-2" />
            <input value={form.resolution} onChange={(e) => setForm({ ...form, resolution: e.target.value })} placeholder="Resolución / workaround" className="rounded-lg border border-slate-300 px-3 py-2 text-sm sm:col-span-2" />
            <input value={form.tags} onChange={(e) => setForm({ ...form, tags: e.target.value })} placeholder="Tags (coma)" className="rounded-lg border border-slate-300 px-3 py-2 text-sm sm:col-span-2" />
            <button onClick={create} className="rounded-lg bg-violet-600 px-4 py-2 text-sm font-semibold text-white sm:col-span-2">Guardar</button>
          </div>
        </details>

        {/* Lista */}
        <div>
          <div className="mb-3 flex items-center gap-2">
            <input value={q} onChange={(e) => setQ(e.target.value)} placeholder="Buscar en la KEDB…" className="w-full max-w-sm rounded-lg border border-slate-300 px-3 py-2 text-sm" />
          </div>
          <div className="space-y-2">
            {items.length === 0 && <p className="text-sm text-slate-400">Aún no hay errores conocidos.</p>}
            {items.map((k) => (
              <div key={k.id} className="rounded-xl border border-slate-200 bg-white p-4">
                <div className="flex items-start justify-between">
                  <div className="min-w-0">
                    <div className="flex items-center gap-2">
                      <span className="font-medium text-slate-800">{k.title}</span>
                      <span className={`rounded-full px-2 py-0.5 text-[10px] font-semibold ${SEV[k.severity] || SEV.medium}`}>{k.severity}</span>
                      {k.scope === "shared" && <span className="rounded-full bg-violet-100 px-2 py-0.5 text-[10px] font-semibold text-violet-700">compartido</span>}
                      {k.product && <span className="text-xs text-slate-400">· {k.product}</span>}
                    </div>
                    {k.symptom && <p className="mt-0.5 text-xs text-slate-500"><b>Síntoma:</b> {k.symptom}</p>}
                    {k.resolution && <p className="mt-0.5 text-xs text-slate-500"><b>Resolución:</b> {k.resolution}</p>}
                    {k.tags.length > 0 && <div className="mt-1 flex flex-wrap gap-1">{k.tags.map((t) => <span key={t} className="rounded bg-slate-100 px-1.5 py-0.5 text-[10px] text-slate-500">{t}</span>)}</div>}
                  </div>
                  {k.scope !== "shared" && (
                    <div className="flex shrink-0 items-center gap-1.5">
                      <button onClick={() => promote(k.id)} title="Proponer como error cross-cliente (sanitizado)"
                        className="rounded-md border border-violet-300 px-2 py-1 text-[11px] font-semibold text-violet-600 hover:bg-violet-50">Compartir</button>
                      <button onClick={() => remove(k.id)} className="text-slate-400 hover:text-red-600"><Trash2 className="h-4 w-4" /></button>
                    </div>
                  )}
                </div>
              </div>
            ))}
          </div>
        </div>
      </div>
    </Shell>
  );
}
