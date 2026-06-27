"use client";

import { PageHeader, Shell } from "@/components/Shell";
import { api } from "@/lib/api";
import { Brain, CheckCircle2, Cpu, Database, Play, ShieldCheck } from "lucide-react";
import { useEffect, useState } from "react";

type Dataset = Awaited<ReturnType<typeof api.ftDatasets>>[number];
type Job = Awaited<ReturnType<typeof api.ftJobs>>[number];
type Check = Awaited<ReturnType<typeof api.ftCheck>>;

const STEPS = [
  { icon: Database, t: "1 · Reúne ejemplos", b: "Enseñas el TONO y FORMATO de tu empresa con pares (instrucción → respuesta ideal). Beneficio: respuestas consistentes y con tu estilo, sin reentrenar conocimiento (eso va por RAG)." },
  { icon: Brain, t: "2 · Desde Memoria", b: "Reutiliza trabajos ya aprobados como ejemplos. Beneficio: aprovechas lo bueno que ya hiciste; cada ejemplo se anonimiza (la PII se redacta) antes de guardarse." },
  { icon: ShieldCheck, t: "3 · Revisa (gate)", b: "Valida calidad + red-team: mínimo de ejemplos, sin PII residual y sin patrones de inyección. Beneficio: no entrenas con datos peligrosos o de baja calidad." },
  { icon: Play, t: "4 · Entrena (LoRA)", b: "Genera un adapter LoRA barato y rápido en tu GPU. Beneficio: el modelo responde con tu estilo a una fracción del costo de un modelo grande." },
  { icon: Cpu, t: "5 · Sirve privado", b: "El adapter se sirve por Ollama/vLLM como ruta local/VPC. Beneficio: lo confidencial se procesa con tu modelo afinado sin salir a la nube." },
];

function badge(status: string) {
  const m: Record<string, string> = {
    ready: "bg-emerald-100 text-emerald-700", completed: "bg-emerald-100 text-emerald-700",
    draft: "bg-slate-100 text-slate-500", queued: "bg-amber-100 text-amber-700",
    running: "bg-blue-100 text-blue-700", simulado: "bg-violet-100 text-violet-700",
    failed: "bg-red-100 text-red-700",
  };
  return m[status] || "bg-slate-100 text-slate-500";
}

export default function FineTunePage() {
  const [datasets, setDatasets] = useState<Dataset[]>([]);
  const [jobs, setJobs] = useState<Job[]>([]);
  const [sel, setSel] = useState<string>("");
  const [nd, setNd] = useState({ name: "", base_model: "llama3.1" });
  const [ex, setEx] = useState({ prompt: "", completion: "" });
  const [check, setCheck] = useState<Check | null>(null);
  const [msg, setMsg] = useState("");

  function load() {
    api.ftDatasets().then(setDatasets).catch(() => {});
    api.ftJobs().then(setJobs).catch(() => {});
  }
  useEffect(() => { load(); }, []);
  const current = datasets.find((d) => d.id === sel) || null;

  async function createDs() {
    if (!nd.name.trim()) { setMsg("Pon un nombre."); return; }
    const d = await api.ftCreateDataset(nd);
    setNd({ name: "", base_model: "llama3.1" }); setSel(d.id); setCheck(null); load();
  }
  async function addEx() {
    if (!sel || !ex.prompt.trim() || !ex.completion.trim()) { setMsg("Completa prompt y respuesta."); return; }
    await api.ftAddExample(sel, ex); setEx({ prompt: "", completion: "" }); setCheck(null); load(); setMsg("Ejemplo agregado (anonimizado).");
  }
  async function fromMemory() {
    if (!sel) return;
    const r = await api.ftFromMemory(sel, { limit: 50 }); setCheck(null); load(); setMsg(`Importados ${r.added} de Memoria.`);
  }
  async function runCheck() {
    if (!sel) return;
    try { setCheck(await api.ftCheck(sel)); load(); } catch (e) { setMsg(e instanceof Error ? e.message : "Error"); }
  }
  async function train() {
    if (!sel) return;
    try { const j = await api.ftCreateJob({ dataset_id: sel }); setMsg(`Job ${j.status}: ${j.reason || ""}`); load(); }
    catch (e) { setMsg(e instanceof Error ? e.message : "El dataset no pasa el gate."); }
  }

  return (
    <Shell>
      <PageHeader title="Fine-tuning (LoRA)" subtitle="Enseña a la IA tu tono y formato con ejemplos — privado y de bajo costo." help="finetune" />
      <div className="space-y-6 p-8">
        {/* Beneficios por paso */}
        <div className="grid grid-cols-1 gap-3 md:grid-cols-5">
          {STEPS.map((s) => (
            <div key={s.t} className="rounded-2xl border border-slate-200 bg-white p-4">
              <s.icon className="mb-2 h-5 w-5 text-violet-600" />
              <div className="mb-1 text-sm font-semibold text-slate-800">{s.t}</div>
              <div className="text-xs leading-relaxed text-slate-500">{s.b}</div>
            </div>
          ))}
        </div>

        <div className="grid grid-cols-1 gap-6 lg:grid-cols-[360px_1fr]">
          {/* Gestión del dataset */}
          <div className="space-y-4">
            <div className="rounded-2xl border border-slate-200 bg-white p-5">
              <h2 className="mb-2 font-semibold text-slate-800">Nuevo dataset</h2>
              <input value={nd.name} onChange={(e) => setNd({ ...nd, name: e.target.value })} placeholder="Nombre (ej. Tono comercial)" className="mb-2 w-full rounded-lg border border-slate-300 px-3 py-2 text-sm" />
              <input value={nd.base_model} onChange={(e) => setNd({ ...nd, base_model: e.target.value })} placeholder="Modelo base (ej. llama3.1)" className="mb-2 w-full rounded-lg border border-slate-300 px-3 py-2 text-sm" />
              <button onClick={createDs} className="rounded-lg bg-slate-900 px-4 py-2 text-sm font-semibold text-white">Crear dataset</button>
            </div>

            <div className="rounded-2xl border border-slate-200 bg-white p-5">
              <h2 className="mb-2 font-semibold text-slate-800">Tus datasets</h2>
              <div className="space-y-1">
                {datasets.length === 0 && <div className="text-sm text-slate-400">Aún no hay datasets.</div>}
                {datasets.map((d) => (
                  <button key={d.id} onClick={() => { setSel(d.id); setCheck(null); }}
                    className={`flex w-full items-center justify-between rounded-lg border px-3 py-2 text-left text-sm ${sel === d.id ? "border-violet-400 bg-violet-50" : "border-slate-200"}`}>
                    <span className="truncate text-slate-700">{d.name} <span className="text-xs text-slate-400">· {d.examples} ej.</span></span>
                    <span className={`rounded-full px-2 py-0.5 text-[11px] ${badge(d.status)}`}>{d.status}</span>
                  </button>
                ))}
              </div>
            </div>
          </div>

          {/* Editor del dataset seleccionado */}
          <div className="space-y-4">
            {!current ? (
              <div className="rounded-2xl border border-dashed border-slate-300 bg-white p-10 text-center text-sm text-slate-400">
                Selecciona o crea un dataset para empezar.
              </div>
            ) : (
              <>
                <div className="rounded-2xl border border-slate-200 bg-white p-5">
                  <div className="mb-2 flex items-center justify-between">
                    <h2 className="font-semibold text-slate-800">{current.name}</h2>
                    <span className="text-xs text-slate-400">{current.examples} ejemplos · base {current.base_model}</span>
                  </div>
                  <label className="text-xs font-semibold uppercase tracking-wide text-slate-500">Instrucción (prompt)</label>
                  <textarea value={ex.prompt} onChange={(e) => setEx({ ...ex, prompt: e.target.value })} rows={2} className="mb-2 mt-1 w-full rounded-lg border border-slate-300 px-3 py-2 text-sm" />
                  <label className="text-xs font-semibold uppercase tracking-wide text-slate-500">Respuesta ideal (completion)</label>
                  <textarea value={ex.completion} onChange={(e) => setEx({ ...ex, completion: e.target.value })} rows={3} className="mb-2 mt-1 w-full rounded-lg border border-slate-300 px-3 py-2 text-sm" />
                  <div className="flex flex-wrap gap-2">
                    <button onClick={addEx} className="rounded-lg bg-slate-900 px-4 py-2 text-sm font-semibold text-white">Agregar ejemplo</button>
                    <button onClick={fromMemory} className="rounded-lg border border-slate-300 px-4 py-2 text-sm font-semibold text-slate-700 hover:bg-slate-50">Importar de Memoria</button>
                    <a href={api.ftExportUrl(current.id)} target="_blank" rel="noreferrer" className="rounded-lg border border-slate-300 px-4 py-2 text-sm font-semibold text-slate-700 hover:bg-slate-50">Exportar JSONL</a>
                  </div>
                </div>

                <div className="rounded-2xl border border-slate-200 bg-white p-5">
                  <h2 className="mb-2 font-semibold text-slate-800">Revisar y entrenar</h2>
                  <div className="flex flex-wrap gap-2">
                    <button onClick={runCheck} className="rounded-lg border border-violet-300 px-4 py-2 text-sm font-semibold text-violet-700 hover:bg-violet-50">Revisar (gate)</button>
                    <button onClick={train} className="flex items-center gap-1.5 rounded-lg bg-violet-600 px-4 py-2 text-sm font-semibold text-white"><Play className="h-4 w-4" /> Entrenar</button>
                  </div>
                  {check && (
                    <div className={`mt-3 rounded-xl p-3 text-sm ${check.ok ? "bg-emerald-50 text-emerald-800" : "bg-amber-50 text-amber-800"}`}>
                      <div className="flex items-center gap-1.5 font-semibold">
                        {check.ok ? <CheckCircle2 className="h-4 w-4" /> : <ShieldCheck className="h-4 w-4" />}
                        {check.ok ? "Listo para entrenar" : "Aún no pasa el gate"}
                      </div>
                      <div className="mt-1 text-xs">Ejemplos: {check.n} · PII residual: {check.pii_leaks} · inyecciones: {check.injection_flags}</div>
                      {check.issues.map((i) => <div key={i} className="text-xs">• {i}</div>)}
                    </div>
                  )}
                </div>
              </>
            )}
            {msg && <div className="text-xs text-slate-500">{msg}</div>}

            {/* Jobs */}
            <div className="rounded-2xl border border-slate-200 bg-white p-5">
              <h2 className="mb-2 font-semibold text-slate-800">Entrenamientos</h2>
              {jobs.length === 0 ? <div className="text-sm text-slate-400">Sin entrenamientos aún.</div> : (
                <div className="space-y-1">
                  {jobs.map((j) => (
                    <div key={j.id} className="flex items-center justify-between rounded-lg border border-slate-200 px-3 py-2 text-sm">
                      <span className="truncate text-slate-700">{j.base_model} <span className="text-xs text-slate-400">{j.reason}</span></span>
                      <span className={`rounded-full px-2 py-0.5 text-[11px] ${badge(j.status)}`}>{j.status}</span>
                    </div>
                  ))}
                </div>
              )}
              <p className="mt-2 text-xs text-slate-400">Si no hay trainer con GPU configurado, los jobs quedan en modo «simulado» (laboratorio). Ver Ayuda → Fine-tuning.</p>
            </div>
          </div>
        </div>
      </div>
    </Shell>
  );
}
