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
const VIEWS = [
  { id: "resumen", label: "Resumen" },
  { id: "finanzas", label: "Finanzas (P&L)" },
  { id: "posicion", label: "Posición" },
  { id: "clientes", label: "Clientes" },
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
        {view === "gobip" && <GobIp ov={ov} />}
        {view === "benchmark" && <Benchmark ov={ov} />}
        {view === "alertas" && <Alertas ov={ov} />}
      </div>
    </Shell>
  );
}

function Resumen({ ov }: { ov: Overview }) {
  const k = ov.kpis;
  const maxMonth = Math.max(...ov.monthly.map((m) => m.ingresos), 1);
  const maxSeg = Math.max(...ov.segments.map((s) => s.revenue), 1);
  return (
    <>
      <div className="mb-6 grid grid-cols-2 gap-4 lg:grid-cols-4">
        <Kpi label="Ingresos 2025" value={mxn(k.revenue)} sub={`Crecimiento YoY ${pct(k.growth)}`} tone="emerald" />
        <Kpi label="EBITDA" value={mxn(k.ebitda)} sub={`Margen ${pct(k.margen_ebitda)}`} tone="violet" />
        <Kpi label="Margen bruto" value={pct(k.margen_bruto)} sub={`Utilidad neta ${mxn(k.neta)}`} tone="blue" />
        <Kpi label="Ciclo de efectivo (CCC)" value={days(k.ccc)} sub={`DSO ${days(k.dso)} · DPO ${days(k.dpo)}`} tone={k.ccc <= 0 ? "emerald" : "amber"} />
      </div>
      <div className="grid grid-cols-1 gap-6 lg:grid-cols-2">
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
      </div>
    </>
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
