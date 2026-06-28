"use client";

import { PageHeader, Shell } from "@/components/Shell";
import { api } from "@/lib/api";
import { AlertTriangle, ChevronLeft, RefreshCw, Send, Sparkles } from "lucide-react";
import Link from "next/link";
import { useEffect, useState } from "react";

type Overview = Awaited<ReturnType<typeof api.financeOverview>>;
type Client = { name: string; sector: string; entity: string; revenue: number; margin: number; status: string };

const ENTITIES = [
  { id: "S4B", label: "S4B" },
  { id: "S4C", label: "S4C" },
  { id: "CONS", label: "Consolidado" },
];
const mxn = (n: number) => "$" + (n / 1_000_000).toFixed(1) + "M";
const pct = (n: number, d = 1) => (n * 100).toFixed(d) + "%";

export default function TableroFinancieroPage() {
  const [entity, setEntity] = useState("CONS");
  const [ov, setOv] = useState<Overview | null>(null);
  const [clients, setClients] = useState<Client[]>([]);
  const [q, setQ] = useState("");
  const [answer, setAnswer] = useState("");
  const [asking, setAsking] = useState(false);
  const [spaceId, setSpaceId] = useState("");

  useEffect(() => {
    if (typeof window !== "undefined") setSpaceId(new URLSearchParams(window.location.search).get("space") || "");
  }, []);

  function load() {
    api.financeOverview(entity).then(setOv).catch(() => {});
    api.financeClients(entity).then(setClients).catch(() => {});
  }
  useEffect(() => { load(); /* eslint-disable-next-line react-hooks/exhaustive-deps */ }, [entity]);

  async function ask() {
    if (!q.trim()) return;
    setAsking(true); setAnswer("");
    try { const r = await api.financeAsk(q.trim(), entity); setAnswer(r.answer); }
    catch (e) { setAnswer(e instanceof Error ? e.message : "Error"); }
    finally { setAsking(false); }
  }

  if (!ov) return <Shell><div className="p-8 text-sm text-slate-400">Cargando tablero…</div></Shell>;
  const k = ov.kpis;
  const maxMonth = Math.max(...ov.monthly.map((m) => m.ingresos), 1);
  const maxSeg = Math.max(...ov.segments.map((s) => s.revenue), 1);
  const gi = ov.gob_ip["2025"];
  const giTot = gi.gob + gi.ip || 1;

  return (
    <Shell>
      <PageHeader title="Tablero Financiero" subtitle={`${ov.company.name} · ${ov.company.period} · ${ov.source}`} />
      <div className="p-8">
        {spaceId && (
          <Link href={`/espacios/${spaceId}`} className="mb-4 inline-flex items-center gap-1 text-sm text-slate-500 hover:text-slate-700">
            <ChevronLeft className="h-4 w-4" /> Volver al espacio
          </Link>
        )}
        {/* Entidad + actualizar */}
        <div className="mb-5 flex items-center gap-3">
          <div className="flex rounded-lg bg-slate-100 p-1">
            {ENTITIES.map((e) => (
              <button key={e.id} onClick={() => setEntity(e.id)}
                className={`rounded-md px-4 py-1.5 text-sm font-semibold ${entity === e.id ? "bg-white text-slate-900 shadow-sm" : "text-slate-500"}`}>
                {e.label}
              </button>
            ))}
          </div>
          <button onClick={load} className="flex items-center gap-1.5 rounded-lg border border-slate-300 px-3 py-1.5 text-sm font-semibold text-slate-600 hover:bg-slate-50">
            <RefreshCw className="h-4 w-4" /> Actualizar
          </button>
          <span className="ml-auto rounded-full bg-amber-50 px-3 py-1 text-xs font-medium text-amber-700">Datos curados (pilot) · fuente en vivo = conector (Paso 1)</span>
        </div>

        {/* Preguntar (RAG) */}
        <div className="mb-6 rounded-2xl border border-violet-200 bg-violet-50/40 p-4">
          <div className="mb-2 flex items-center gap-1.5 text-sm font-semibold text-slate-800"><Sparkles className="h-4 w-4 text-violet-600" /> Pregúntale a tus finanzas</div>
          <div className="flex gap-2">
            <input value={q} onChange={(e) => setQ(e.target.value)} onKeyDown={(e) => e.key === "Enter" && ask()}
              placeholder="Ej. ¿Por qué el margen bruto está bajo? ¿Qué cliente concentra más ingreso?"
              className="flex-1 rounded-lg border border-slate-300 px-3 py-2 text-sm" />
            <button onClick={ask} disabled={asking} className="flex items-center gap-1.5 rounded-lg bg-violet-600 px-4 py-2 text-sm font-semibold text-white disabled:opacity-50">
              <Send className="h-4 w-4" /> {asking ? "Pensando…" : "Preguntar"}
            </button>
          </div>
          {answer && <div className="mt-3 whitespace-pre-wrap rounded-lg border border-slate-200 bg-white px-3 py-2 text-sm text-slate-700">{answer}</div>}
        </div>

        {/* KPIs */}
        <div className="mb-6 grid grid-cols-2 gap-4 lg:grid-cols-4">
          <Kpi label="Ingresos 2025" value={mxn(k.revenue)} sub={`Crecimiento YoY ${pct(k.growth)}`} tone="emerald" />
          <Kpi label="EBITDA" value={mxn(k.ebitda)} sub={`Margen ${pct(k.margen_ebitda)}`} tone="violet" />
          <Kpi label="Margen bruto" value={pct(k.margen_bruto)} sub={`Utilidad neta ${mxn(k.neta)}`} tone="blue" />
          <Kpi label="Ciclo de efectivo (CCC)" value={`${k.ccc}d`} sub={`DSO ${k.dso}d · DPO ${k.dpo}d`} tone={k.ccc <= 0 ? "emerald" : "amber"} />
        </div>

        <div className="grid grid-cols-1 gap-6 lg:grid-cols-2">
          {/* Evolución mensual */}
          <Card title="Evolución mensual (ingresos)">
            <div className="flex h-48 items-end gap-1.5">
              {ov.monthly.map((m) => (
                <div key={m.mes} className="flex flex-1 flex-col items-center gap-1">
                  <div className="flex w-full items-end justify-center" style={{ height: "150px" }}>
                    <div className="w-full rounded-t bg-violet-500" style={{ height: `${(m.ingresos / maxMonth) * 100}%` }} title={`${m.mes}: ${m.ingresos}M`} />
                  </div>
                  <span className="text-[10px] text-slate-400">{m.mes}</span>
                </div>
              ))}
            </div>
          </Card>

          {/* Segmentos */}
          <Card title="Líneas de servicio (ingreso y margen)">
            <div className="space-y-2">
              {ov.segments.map((s) => (
                <div key={s.name}>
                  <div className="flex justify-between text-xs"><span className="text-slate-600">{s.name}</span><span className="tabular-nums text-slate-500">{mxn(s.revenue)} · {pct(s.margin, 0)}</span></div>
                  <div className="mt-1 h-2 w-full rounded-full bg-slate-100"><div className="h-2 rounded-full bg-violet-500" style={{ width: `${(s.revenue / maxSeg) * 100}%` }} /></div>
                </div>
              ))}
            </div>
          </Card>

          {/* Gobierno vs IP */}
          <Card title="Gobierno vs IP (2025)">
            <div className="mb-2 flex h-4 overflow-hidden rounded-full">
              <div className="bg-blue-600" style={{ width: `${(gi.gob / giTot) * 100}%` }} />
              <div className="bg-emerald-500" style={{ width: `${(gi.ip / giTot) * 100}%` }} />
            </div>
            <div className="flex justify-between text-sm">
              <span className="text-blue-700">Gobierno {mxn(gi.gob)} ({pct(gi.gob / giTot, 0)})</span>
              <span className="text-emerald-700">IP {mxn(gi.ip)} ({pct(gi.ip / giTot, 0)})</span>
            </div>
          </Card>

          {/* Alertas */}
          <Card title="Alertas directivas">
            <div className="space-y-2">
              {ov.alerts.map((a, i) => (
                <div key={i} className="flex items-start gap-2 rounded-lg border border-slate-100 p-2">
                  <AlertTriangle className={`mt-0.5 h-4 w-4 shrink-0 ${a.level === "high" ? "text-red-500" : a.level === "med" ? "text-amber-500" : "text-slate-400"}`} />
                  <div>
                    <span className="text-xs font-semibold text-slate-700">{a.area}{a.impact ? ` · impacto ${mxn(a.impact)}` : ""}</span>
                    <p className="text-xs text-slate-500">{a.msg}</p>
                  </div>
                </div>
              ))}
            </div>
          </Card>
        </div>

        {/* Clientes */}
        <Card title="Top clientes" className="mt-6">
          <table className="w-full text-sm">
            <thead><tr className="text-left text-[10px] uppercase tracking-wide text-slate-400">
              <th className="py-2">Cliente</th><th>Sector</th><th>Entidad</th><th className="text-right">Ingreso</th><th className="text-right">Margen</th>
            </tr></thead>
            <tbody>
              {clients.map((c) => (
                <tr key={c.name} className="border-t border-slate-100">
                  <td className="py-2">
                    <span className={`mr-2 inline-block h-2 w-2 rounded-full ${c.status === "green" ? "bg-emerald-500" : c.status === "amber" ? "bg-amber-500" : "bg-red-500"}`} />
                    {c.name}
                  </td>
                  <td><span className={`rounded-full px-2 py-0.5 text-[11px] ${c.sector === "Gobierno" ? "bg-blue-50 text-blue-700" : "bg-emerald-50 text-emerald-700"}`}>{c.sector}</span></td>
                  <td className="text-slate-500">{c.entity}</td>
                  <td className="text-right tabular-nums">{mxn(c.revenue)}</td>
                  <td className="text-right tabular-nums text-slate-500">{pct(c.margin, 0)}</td>
                </tr>
              ))}
            </tbody>
          </table>
        </Card>
      </div>
    </Shell>
  );
}

function Kpi({ label, value, sub, tone }: { label: string; value: string; sub: string; tone: string }) {
  const bg: Record<string, string> = { emerald: "bg-emerald-100 text-emerald-700", violet: "bg-violet-100 text-violet-700", blue: "bg-blue-100 text-blue-700", amber: "bg-amber-100 text-amber-700" };
  return (
    <div className="rounded-2xl border border-slate-200 bg-white p-4">
      <div className={`mb-3 inline-flex h-8 items-center rounded-lg px-2 text-xs font-bold ${bg[tone] || bg.violet}`}>$</div>
      <div className="text-xs text-slate-500">{label}</div>
      <div className="mt-0.5 text-2xl font-extrabold tabular-nums text-slate-900">{value}</div>
      <div className="mt-1 text-xs text-slate-400">{sub}</div>
    </div>
  );
}

function Card({ title, children, className = "" }: { title: string; children: React.ReactNode; className?: string }) {
  return (
    <div className={`rounded-2xl border border-slate-200 bg-white ${className}`}>
      <div className="border-b border-slate-100 px-5 py-3 text-sm font-bold text-slate-800">{title}</div>
      <div className="p-5">{children}</div>
    </div>
  );
}
