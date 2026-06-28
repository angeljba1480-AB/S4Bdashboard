"use client";

import { PageHeader, Shell } from "@/components/Shell";
import { api } from "@/lib/api";
import { AlertTriangle, ChevronLeft, RefreshCw, Send, Sparkles } from "lucide-react";
import Link from "next/link";
import { useEffect, useState } from "react";

type Overview = Awaited<ReturnType<typeof api.financeOverview>>;
type Projects = Awaited<ReturnType<typeof api.financeProjects>>;
type Client = { name: string; sector: string; entity: string; revenue: number; margin: number; status: string };

const ENTITIES = [
  { id: "S4B", label: "S4B" },
  { id: "S4C", label: "S4C" },
  { id: "CONS", label: "Consolidado" },
];
const VIEWS = [
  { id: "resumen", label: "Resumen" },
  { id: "finanzas", label: "Finanzas (P&L)" },
  { id: "posicion", label: "Posición" },
  { id: "clientes", label: "Clientes" },
  { id: "proyectos", label: "Proyectos" },
  { id: "gobip", label: "Gobierno vs IP" },
  { id: "benchmark", label: "Benchmark" },
  { id: "alertas", label: "Alertas" },
];
const mxn = (n: number) => "$" + (n / 1_000_000).toFixed(1) + "M";
const pct = (n: number, d = 1) => (n * 100).toFixed(d) + "%";
const days = (n: number) => `${Math.round(n)}d`;

export default function TableroFinancieroPage() {
  const [entity, setEntity] = useState("CONS");
  const [view, setView] = useState("resumen");
  const [ov, setOv] = useState<Overview | null>(null);
  const [clients, setClients] = useState<Client[]>([]);
  const [projects, setProjects] = useState<Projects | null>(null);
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
    api.financeProjects().then(setProjects).catch(() => {});
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
        <div className="mb-4 flex flex-wrap items-center gap-3">
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

        {/* Navegación de vistas (como el mockup) */}
        <div className="mb-5 flex flex-wrap gap-1 border-b border-slate-200">
          {VIEWS.map((v) => (
            <button key={v.id} onClick={() => setView(v.id)}
              className={`-mb-px border-b-2 px-3 py-2 text-sm font-medium ${view === v.id ? "border-violet-600 text-violet-700" : "border-transparent text-slate-500 hover:text-slate-700"}`}>
              {v.label}
            </button>
          ))}
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

        {view === "resumen" && <Resumen ov={ov} />}
        {view === "finanzas" && <Finanzas k={k} />}
        {view === "posicion" && <Posicion k={k} />}
        {view === "clientes" && <Clientes clients={clients} />}
        {view === "proyectos" && <Proyectos projects={projects} />}
        {view === "gobip" && <GobIp ov={ov} />}
        {view === "benchmark" && <Benchmark ov={ov} />}
        {view === "alertas" && <Alertas ov={ov} />}
      </div>
    </Shell>
  );
}

function Resumen({ ov }: { ov: Overview }) {
  const k = ov.kpis;
  const s = ov.summary;
  const maxMonth = Math.max(...ov.monthly.map((m) => m.ingresos), 1);
  return (
    <>
      {/* KPIs estilo mockup: delta + desglose S4B/S4C */}
      <div className="mb-6 grid grid-cols-1 gap-4 sm:grid-cols-2 lg:grid-cols-4">
        <KpiBig icon="↗" tone="emerald" label="Ingresos 2025" value={mxn(k.revenue)}
          delta={pct(k.growth)} deltaUp cmp={[["S4B", mxn(k.revenue_s4b)], ["S4C", mxn(k.revenue_s4c)]]} />
        <KpiBig icon="◑" tone="violet" label="EBITDA" value={mxn(k.ebitda)}
          delta={`${pct(k.margen_ebitda)} margen`} deltaUp cmp={[["S4B", mxn(k.ebitda_s4b)], ["S4C", mxn(k.ebitda_s4c)]]} />
        <KpiBig icon="◉" tone="blue" label="Headcount" value={String(k.headcount)}
          delta="grupo total" cmp={[["S4B", String(k.headcount_s4b)], ["S4C", String(k.headcount_s4c)]]} />
        <KpiBig icon="✓" tone="amber" label="Regla 40" value={(k.rule40 * 100).toFixed(0)}
          delta={`${pct(k.rule40)}`} deltaUp cmp={[["Crec.", pct(k.growth)], ["Mg EBITDA", pct(k.margen_ebitda)]]} />
      </div>

      {/* 3 tarjetas: Salud financiera · Operación · Alertas activas */}
      <div className="mb-6 grid grid-cols-1 gap-6 lg:grid-cols-3">
        <Card title="Salud financiera">
          <Line label="Caja" value={mxn(s.caja as number)} />
          <Line label="Cartera" value={mxn(s.cartera as number)} />
          <Line label="Capital de trabajo" value={mxn(s.capital_trabajo as number)} />
          <Line label="Regla 40" value={(k.rule40 * 100).toFixed(1)} />
        </Card>
        <Card title="Operación">
          <Line label="Proyectos en riesgo" value={String(s.proyectos_riesgo)} />
          <Line label="Top clientes" value={String(s.top_clientes)} />
          <Line label="Líneas de servicio" value={String(s.lineas_servicio)} />
          <Line label="Línea principal" value={String(s.linea_principal)} />
        </Card>
        <Card title={`Alertas activas`}>
          <div className="space-y-2">
            {ov.alerts.slice(0, 4).map((a, i) => (
              <div key={i} className="flex items-start gap-2">
                <span className={`mt-1 h-2 w-2 shrink-0 rounded-full ${a.level === "high" ? "bg-red-500" : a.level === "med" ? "bg-amber-500" : "bg-slate-300"}`} />
                <div><p className="text-xs text-slate-600">{a.msg}</p><span className="text-[11px] text-slate-400">{a.area}</span></div>
              </div>
            ))}
          </div>
        </Card>
      </div>

      {/* Evolución mensual */}
      <Card title="Ingresos y EBITDA · 12 meses">
        <div className="flex h-56 items-end gap-1.5">
          {ov.monthly.map((m) => (
            <div key={m.mes} className="flex flex-1 flex-col items-center gap-1">
              <div className="flex w-full items-end justify-center gap-0.5" style={{ height: "190px" }}>
                <div className="w-1/2 rounded-t bg-violet-500" style={{ height: `${(m.ingresos / maxMonth) * 100}%` }} title={`Ingresos ${m.mes}: ${m.ingresos}M`} />
                <div className="w-1/2 rounded-t bg-emerald-400" style={{ height: `${(m.ebitda / maxMonth) * 100}%` }} title={`EBITDA ${m.mes}: ${m.ebitda}M`} />
              </div>
              <span className="text-[10px] text-slate-400">{m.mes}</span>
            </div>
          ))}
        </div>
        <div className="mt-3 flex gap-4 text-xs"><span className="flex items-center gap-1"><span className="h-2 w-2 rounded-full bg-violet-500" /> Ingresos</span><span className="flex items-center gap-1"><span className="h-2 w-2 rounded-full bg-emerald-400" /> EBITDA</span></div>
      </Card>
    </>
  );
}

function KpiBig({ icon, tone, label, value, delta, deltaUp = false, cmp }:
  { icon: string; tone: string; label: string; value: string; delta: string; deltaUp?: boolean; cmp: [string, string][] }) {
  const bg: Record<string, string> = { emerald: "bg-emerald-100 text-emerald-700", violet: "bg-violet-100 text-violet-700", blue: "bg-blue-100 text-blue-700", amber: "bg-amber-100 text-amber-700" };
  return (
    <div className="rounded-2xl border border-slate-200 bg-white p-4">
      <div className={`mb-3 inline-flex h-9 w-9 items-center justify-center rounded-lg text-base font-bold ${bg[tone] || bg.violet}`}>{icon}</div>
      <div className="text-xs text-slate-500">{label}</div>
      <div className="mt-0.5 text-3xl font-extrabold tabular-nums text-slate-900">{value}</div>
      <div className="mt-2">
        <span className={`rounded px-2 py-0.5 text-[11px] font-bold ${deltaUp ? "bg-emerald-100 text-emerald-700" : "bg-slate-100 text-slate-500"}`}>{deltaUp ? "▲ " : ""}{delta}</span>
      </div>
      <div className="mt-3 flex flex-wrap gap-x-4 gap-y-1 border-t border-dashed border-slate-200 pt-2 text-[10px] text-slate-400">
        {cmp.map(([kk, vv]) => <span key={kk}>{kk}: <b className="tabular-nums text-slate-700">{vv}</b></span>)}
      </div>
    </div>
  );
}

function Finanzas({ k }: { k: Record<string, number> }) {
  const rows = [
    ["Ventas", k.revenue, ""],
    ["Costos", -k.costos, ""],
    ["Utilidad bruta", k.ub, pct(k.margen_bruto)],
    ["EBITDA", k.ebitda, pct(k.margen_ebitda)],
    ["Utilidad neta", k.neta, pct(k.margen_neto)],
  ] as const;
  return (
    <Card title="Estado de resultados (P&L)">
      <table className="w-full text-sm">
        <tbody>
          {rows.map(([label, val, m]) => (
            <tr key={label} className="border-b border-slate-100">
              <td className="py-2.5 font-medium text-slate-700">{label}</td>
              <td className={`py-2.5 text-right tabular-nums ${val < 0 ? "text-red-600" : "text-slate-800"}`}>{mxn(val)}</td>
              <td className="w-20 py-2.5 text-right text-xs text-slate-400">{m}</td>
            </tr>
          ))}
        </tbody>
      </table>
    </Card>
  );
}

function Posicion({ k }: { k: Record<string, number> }) {
  return (
    <div className="grid grid-cols-1 gap-6 lg:grid-cols-2">
      <Card title="Balance">
        <Line label="Activo total" value={mxn(k.activo)} />
        <Line label="Pasivo total" value={mxn(k.pasivo)} />
        <Line label="Capital contable" value={mxn(k.capital)} />
        <Line label="Endeudamiento" value={pct(k.endeudamiento)} />
        <Line label="ROE" value={pct(k.roe)} />
      </Card>
      <Card title="Liquidez y ciclo de efectivo">
        <Line label="Caja" value={mxn(k.cash)} />
        <Line label="Cuentas por cobrar" value={mxn(k.ar)} />
        <Line label="Cuentas por pagar" value={mxn(k.ap)} />
        <Line label="DSO (cobranza)" value={days(k.dso)} />
        <Line label="DPO (pago)" value={days(k.dpo)} />
        <Line label="CCC (ciclo)" value={days(k.ccc)} />
      </Card>
    </div>
  );
}

function Clientes({ clients }: { clients: Client[] }) {
  return (
    <Card title="Top clientes">
      <table className="w-full text-sm">
        <thead><tr className="text-left text-[10px] uppercase tracking-wide text-slate-400">
          <th className="py-2">Cliente</th><th>Sector</th><th>Entidad</th><th className="text-right">Ingreso</th><th className="text-right">Margen</th>
        </tr></thead>
        <tbody>
          {clients.map((c) => (
            <tr key={c.name} className="border-t border-slate-100">
              <td className="py-2"><span className={`mr-2 inline-block h-2 w-2 rounded-full ${c.status === "green" ? "bg-emerald-500" : c.status === "amber" ? "bg-amber-500" : "bg-red-500"}`} />{c.name}</td>
              <td><span className={`rounded-full px-2 py-0.5 text-[11px] ${c.sector === "Gobierno" ? "bg-blue-50 text-blue-700" : "bg-emerald-50 text-emerald-700"}`}>{c.sector}</span></td>
              <td className="text-slate-500">{c.entity}</td>
              <td className="text-right tabular-nums">{mxn(c.revenue)}</td>
              <td className="text-right tabular-nums text-slate-500">{pct(c.margin, 0)}</td>
            </tr>
          ))}
        </tbody>
      </table>
    </Card>
  );
}

function Proyectos({ projects }: { projects: Projects | null }) {
  if (!projects) return <div className="text-sm text-slate-400">Cargando proyectos…</div>;
  const t = projects.totals;
  const years = Object.keys(projects.trend).sort();
  const maxYear = Math.max(...years.map((y) => projects.trend[y].venta), 1);
  return (
    <div className="space-y-6">
      {/* KPIs del portafolio real */}
      <div className="grid grid-cols-2 gap-4 lg:grid-cols-4">
        <Kpi label="Venta total" value={mxn(t.venta)} sub={`${t.proyectos} proyectos`} tone="emerald" />
        <Kpi label="Margen" value={mxn(t.margen)} sub={pct(t.pct_margen)} tone="violet" />
        <Kpi label="EBITDA" value={mxn(t.ebitda)} sub={pct(t.ebitda / t.venta)} tone="blue" />
        <Kpi label="Costos" value={mxn(t.costos)} sub="directo + asignado" tone="amber" />
      </div>

      {/* Tendencia de venta por año */}
      <Card title="Venta por año (cartera de proyectos)">
        <div className="space-y-3">
          {years.map((y) => {
            const d = projects.trend[y]; const tot = d.venta || 1;
            return (
              <div key={y}>
                <div className="mb-1 flex justify-between text-xs text-slate-500"><span>{y}</span><span className="tabular-nums">{mxn(d.venta)}</span></div>
                <div className="flex h-5 overflow-hidden rounded bg-slate-50" style={{ width: `${(d.venta / maxYear) * 100}%`, minWidth: "30%" }}>
                  <div className="bg-blue-600" style={{ width: `${(d.gob / tot) * 100}%` }} title={`Gobierno ${mxn(d.gob)}`} />
                  <div className="bg-emerald-500" style={{ width: `${(d.ip / tot) * 100}%` }} title={`IP ${mxn(d.ip)}`} />
                </div>
              </div>
            );
          })}
        </div>
        <div className="mt-4 flex gap-4 text-xs"><span className="flex items-center gap-1"><span className="h-2 w-2 rounded-full bg-blue-600" /> Gobierno</span><span className="flex items-center gap-1"><span className="h-2 w-2 rounded-full bg-emerald-500" /> IP</span></div>
      </Card>

      {/* Detalle de proyectos */}
      <Card title={`Proyectos (${projects.projects.length} principales de ${t.proyectos})`}>
        <div className="max-h-[480px] overflow-auto">
          <table className="w-full text-sm">
            <thead className="sticky top-0 bg-white"><tr className="text-left text-[10px] uppercase tracking-wide text-slate-400">
              <th className="py-2">Cliente / Proyecto</th><th>Tipo</th><th className="text-right">Venta</th><th className="text-right">Margen</th><th className="text-right">EBITDA</th>
            </tr></thead>
            <tbody>
              {projects.projects.map((p, i) => (
                <tr key={i} className="border-t border-slate-100">
                  <td className="py-2"><div className="font-medium text-slate-700">{p.cliente}</div><div className="text-[11px] text-slate-400">{p.nombre}</div></td>
                  <td><span className={`rounded-full px-2 py-0.5 text-[11px] ${p.tipo === "Gobierno" ? "bg-blue-50 text-blue-700" : "bg-emerald-50 text-emerald-700"}`}>{p.tipo}</span></td>
                  <td className="text-right tabular-nums">{mxn(p.venta)}</td>
                  <td className={`text-right tabular-nums ${p.pct_margen < 0 ? "text-red-600" : "text-slate-500"}`}>{pct(p.pct_margen, 0)}</td>
                  <td className={`text-right tabular-nums ${p.ebitda < 0 ? "text-red-600" : "text-slate-600"}`}>{mxn(p.ebitda)}</td>
                </tr>
              ))}
            </tbody>
          </table>
        </div>
      </Card>
    </div>
  );
}

function GobIp({ ov }: { ov: Overview }) {
  const years = Object.keys(ov.gob_ip).sort();
  const max = Math.max(...years.map((y) => ov.gob_ip[y].gob + ov.gob_ip[y].ip), 1);
  return (
    <Card title="Gobierno vs IP (tendencia)">
      <div className="space-y-4">
        {years.map((y) => {
          const g = ov.gob_ip[y]; const tot = g.gob + g.ip || 1;
          return (
            <div key={y}>
              <div className="mb-1 flex justify-between text-xs text-slate-500"><span>{y}</span><span className="tabular-nums">{mxn(tot)}</span></div>
              <div className="flex h-5 overflow-hidden rounded" style={{ width: `${(tot / max) * 100}%`, minWidth: "40%" }}>
                <div className="bg-blue-600" style={{ width: `${(g.gob / tot) * 100}%` }} title={`Gobierno ${mxn(g.gob)}`} />
                <div className="bg-emerald-500" style={{ width: `${(g.ip / tot) * 100}%` }} title={`IP ${mxn(g.ip)}`} />
              </div>
            </div>
          );
        })}
      </div>
      <div className="mt-4 flex gap-4 text-xs"><span className="flex items-center gap-1"><span className="h-2 w-2 rounded-full bg-blue-600" /> Gobierno</span><span className="flex items-center gap-1"><span className="h-2 w-2 rounded-full bg-emerald-500" /> IP</span></div>
    </Card>
  );
}

function Benchmark({ ov }: { ov: Overview }) {
  const f = (v: number, fmt: string) => fmt === "pct" ? pct(v) : fmt === "days" ? days(v) : String(v);
  return (
    <Card title="Benchmark vs sector LATAM">
      <table className="w-full text-sm">
        <thead><tr className="text-left text-[10px] uppercase tracking-wide text-slate-400">
          <th className="py-2">Métrica</th><th className="text-right">S4B</th><th className="text-right">Industria</th><th className="text-right">Top cuartil</th>
        </tr></thead>
        <tbody>
          {ov.benchmarks.map((b) => {
            const good = b.higherBetter ? b.s4b >= b.industry : b.s4b <= b.industry;
            return (
              <tr key={b.metric} className="border-t border-slate-100">
                <td className="py-2 text-slate-700">{b.metric}</td>
                <td className={`text-right font-semibold tabular-nums ${good ? "text-emerald-600" : "text-red-600"}`}>{f(b.s4b, b.format)}</td>
                <td className="text-right tabular-nums text-slate-500">{f(b.industry, b.format)}</td>
                <td className="text-right tabular-nums text-slate-400">{f(b.topQ, b.format)}</td>
              </tr>
            );
          })}
        </tbody>
      </table>
    </Card>
  );
}

function Alertas({ ov }: { ov: Overview }) {
  return (
    <Card title="Alertas directivas">
      <div className="space-y-2">
        {ov.alerts.map((a, i) => (
          <div key={i} className="flex items-start gap-2 rounded-lg border border-slate-100 p-3">
            <AlertTriangle className={`mt-0.5 h-4 w-4 shrink-0 ${a.level === "high" ? "text-red-500" : a.level === "med" ? "text-amber-500" : "text-slate-400"}`} />
            <div>
              <span className="text-xs font-semibold text-slate-700">{a.area}{a.impact ? ` · impacto ${mxn(a.impact)}` : ""}</span>
              <p className="text-sm text-slate-500">{a.msg}</p>
            </div>
          </div>
        ))}
      </div>
    </Card>
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

function Line({ label, value }: { label: string; value: string }) {
  return (
    <div className="flex justify-between border-b border-slate-50 py-2 text-sm">
      <span className="text-slate-600">{label}</span><span className="font-semibold tabular-nums text-slate-800">{value}</span>
    </div>
  );
}
