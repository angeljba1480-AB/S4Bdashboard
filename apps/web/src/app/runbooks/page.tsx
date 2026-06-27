"use client";

import { PageHeader, Shell } from "@/components/Shell";
import { api } from "@/lib/api";
import { CheckCircle2, Download, Factory, Workflow } from "lucide-react";
import { useEffect, useState } from "react";

type Runbook = { id: string; title: string; description: string; segment: string; sector: string; area: string; benefit: string; steps: string[] };
type Facets = { segments: { key: string; label: string }[]; sectors: { key: string; label: string; count: number }[]; total: number };

const SEG_LABEL: Record<string, string> = { pyme: "PyME", enterprise: "Enterprise", ambos: "PyME y Enterprise" };

export default function RunbooksPage() {
  const [facets, setFacets] = useState<Facets | null>(null);
  const [items, setItems] = useState<Runbook[]>([]);
  const [segment, setSegment] = useState("");
  const [sector, setSector] = useState("");
  const [q, setQ] = useState("");
  const [installed, setInstalled] = useState<Record<string, string>>({});
  const [msg, setMsg] = useState("");

  function load() { api.runbooks(segment, sector, q).then(setItems).catch(() => {}); }
  useEffect(() => { api.runbookFacets().then(setFacets).catch(() => {}); }, []);
  useEffect(() => { load(); /* eslint-disable-next-line react-hooks/exhaustive-deps */ }, [segment, sector]);

  async function install(rb: Runbook) {
    try {
      const r = await api.installRunbook(rb.id);
      setInstalled((s) => ({ ...s, [rb.id]: r.id }));
      setMsg(r.already_installed
        ? `«${rb.title}» ya estaba instalado. Búscalo en Acciones → recetas del agente.`
        : `«${rb.title}» instalado. Ejecútalo desde Acciones (lecturas al momento; escrituras con tu aprobación).`);
    } catch (e) { setMsg(e instanceof Error ? e.message : "Error"); }
  }

  return (
    <Shell>
      <PageHeader title="Runbooks" subtitle="Automatizaciones multi-paso listas para tu sector — de áreas de servicio hasta planta de producción. Instálalas y el agente las ejecuta." />
      <div className="p-8">
        {/* Filtros */}
        <div className="mb-5 space-y-3">
          <div className="flex flex-wrap items-center gap-2">
            <span className="text-xs font-semibold uppercase tracking-wide text-slate-500">Segmento:</span>
            <Chip active={segment === ""} onClick={() => setSegment("")}>Todos</Chip>
            {facets?.segments.map((s) => (
              <Chip key={s.key} active={segment === s.key} onClick={() => setSegment(s.key)}>{s.label}</Chip>
            ))}
          </div>
          <div className="flex flex-wrap items-center gap-2">
            <span className="text-xs font-semibold uppercase tracking-wide text-slate-500">Sector:</span>
            <Chip active={sector === ""} onClick={() => setSector("")}>Todos</Chip>
            {facets?.sectors.map((s) => (
              <Chip key={s.key} active={sector === s.key} onClick={() => setSector(s.key)}>{s.label} ({s.count})</Chip>
            ))}
          </div>
          <form onSubmit={(e) => { e.preventDefault(); load(); }} className="flex gap-2">
            <input value={q} onChange={(e) => setQ(e.target.value)} placeholder="Buscar runbook…"
              className="w-full max-w-sm rounded-lg border border-slate-300 px-3 py-2 text-sm" />
            <button className="rounded-lg border border-slate-300 px-4 py-2 text-sm font-semibold text-slate-600">Buscar</button>
          </form>
        </div>

        {msg && <div className="mb-4 rounded-lg border border-emerald-200 bg-emerald-50 px-3 py-2 text-sm text-emerald-700">{msg}</div>}

        {/* Tarjetas */}
        <div className="grid grid-cols-1 gap-4 md:grid-cols-2 xl:grid-cols-3">
          {items.length === 0 && <p className="text-sm text-slate-400">No hay runbooks para ese filtro.</p>}
          {items.map((rb) => (
            <div key={rb.id} className="flex flex-col rounded-2xl border border-slate-200 bg-white p-5">
              <div className="mb-2 flex items-center gap-2">
                {rb.sector === "manufactura" ? <Factory className="h-4 w-4 text-violet-600" /> : <Workflow className="h-4 w-4 text-violet-600" />}
                <h3 className="font-semibold text-slate-800">{rb.title}</h3>
              </div>
              <div className="mb-2 flex flex-wrap gap-1.5">
                <Tag>{rb.area}</Tag>
                <Tag>{SEG_LABEL[rb.segment] || rb.segment}</Tag>
              </div>
              <p className="text-sm text-slate-600">{rb.description}</p>
              {rb.benefit && <p className="mt-1.5 text-xs text-emerald-700">✓ {rb.benefit}</p>}
              <ol className="mt-3 space-y-1 text-xs text-slate-500">
                {rb.steps.map((s, i) => <li key={i}>{i + 1}. {s}</li>)}
              </ol>
              <div className="mt-4 flex-1" />
              <button onClick={() => install(rb)}
                className={`flex items-center justify-center gap-1.5 rounded-lg px-4 py-2 text-sm font-semibold ${installed[rb.id] ? "border border-emerald-300 text-emerald-700" : "bg-violet-600 text-white"}`}>
                {installed[rb.id] ? <><CheckCircle2 className="h-4 w-4" /> Instalado</> : <><Download className="h-4 w-4" /> Instalar</>}
              </button>
            </div>
          ))}
        </div>
      </div>
    </Shell>
  );
}

function Chip({ active, onClick, children }: { active: boolean; onClick: () => void; children: React.ReactNode }) {
  return (
    <button onClick={onClick}
      className={`rounded-full px-3 py-1 text-sm font-medium ${active ? "bg-violet-600 text-white" : "border border-slate-200 text-slate-600 hover:bg-slate-100"}`}>
      {children}
    </button>
  );
}
function Tag({ children }: { children: React.ReactNode }) {
  return <span className="rounded-full bg-slate-100 px-2 py-0.5 text-[10px] font-semibold uppercase tracking-wide text-slate-500">{children}</span>;
}
