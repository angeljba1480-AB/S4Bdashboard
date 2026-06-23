import React, { useState } from 'react';
import {
  LineChart, Line, BarChart, Bar, AreaChart, Area, PieChart, Pie, Cell,
  XAxis, YAxis, CartesianGrid, Tooltip, ResponsiveContainer, Legend,
  ComposedChart, ReferenceLine
} from 'recharts';
import {
  TrendingUp, TrendingDown, AlertCircle, CheckCircle2, DollarSign, Users, Briefcase,
  Activity, Shield, Target, ArrowLeft, Sparkles, Layers, BarChart3,
  PieChart as PieIcon, Building2, Calendar, Plus, ChevronDown, ChevronRight,
  Search, Download, ArrowUpRight, ArrowDownRight, Award, Flame, Clock,
  Mail, Phone, FileText, MoreHorizontal
} from 'lucide-react';
 
// ============================================================================
// DATA
// ============================================================================
const company = {
  name: 'Silent4Business',
  period: 'T3 2026 · cierre Oct',
  ceo: 'Layla Delgadillo',
 
  finance: {
    revenueLTM: 198_400_000, revenueLastYear: 161_700_000, growthYoY: 0.227,
    grossProfit: 103_200_000, grossMargin: 0.520,
    ebitdaLTM: 41_600_000, ebitdaMargin: 0.210,
    netIncomeLTM: 24_800_000, netMargin: 0.125,
    cash: 28_400_000, ar: 38_200_000, arOverdue: 8_900_000, ap: 14_800_000,
    dso: 58, dpo: 42,
    creditTotal: 50_000_000, creditUsed: 18_000_000, creditCost: 0.142,
    workingCapital: 51_800_000, debtToEbitda: 0.43, quickRatio: 1.84,
  },
 
  ops: {
    activeProjects: 47, activeClients: 31, newClientsQ: 4,
    backlog: 84_600_000, pipeline: 142_300_000,
    nps: 64, slaCompliance: 0.984, projectsAtRisk: 6,
    avgProjectMargin: 0.243,
  },
 
  people: {
    headcount: 112, payrollMonthly: 11_200_000,
    utilizationRate: 0.74, attrition12m: 0.18,
    revenuePerEmployee: 1_771_429, avgTenure: 3.2, benchHeadcount: 9,
  },
 
  segments: [
    { id: 'soc', name: 'SOC/NOC Administrado', revenue: 96_400_000, margin: 0.28, share: 0.486, growth: 0.184, color: '#10b981', mrr: 7_900_000, clients: 18 },
    { id: 'dfir', name: 'Ciberinteligencia & DFIR', revenue: 38_600_000, margin: 0.34, share: 0.195, growth: 0.312, color: '#3b82f6', mrr: 1_800_000, clients: 14 },
    { id: 'grc', name: 'GRC & Cumplimiento', revenue: 24_800_000, margin: 0.22, share: 0.125, growth: 0.092, color: '#f59e0b', mrr: 900_000, clients: 11 },
    { id: 'impl', name: 'Implementación', revenue: 22_100_000, margin: 0.16, share: 0.111, growth: -0.046, color: '#8b5cf6', mrr: 0, clients: 8 },
    { id: '4you', name: '4YOU PyME/Hogar', revenue: 16_500_000, margin: 0.41, share: 0.083, growth: 1.840, color: '#ec4899', mrr: 1_300_000, clients: 247 },
  ],
 
  verticals: [
    { name: 'Gobierno', revenue: 64_200_000, clients: 6, dso: 86 },
    { name: 'Financiero', revenue: 52_100_000, clients: 9, dso: 42 },
    { name: 'Manufactura', revenue: 31_800_000, clients: 7, dso: 38 },
    { name: 'Energía', revenue: 22_400_000, clients: 4, dso: 64 },
    { name: 'Salud', revenue: 14_900_000, clients: 3, dso: 51 },
    { name: 'PyME (4YOU)', revenue: 13_000_000, clients: 2, dso: 12 },
  ],
 
  areas: [
    { id: 'soc', name: 'SOC/NOC', headcount: 38, payroll: 3_680_000, billable: true, utilization: 0.79, attrition: 0.24, avgSalary: 96_842, leader: 'Carlos Méndez' },
    { id: 'dfir', name: 'Pentesting/DFIR', headcount: 18, payroll: 2_160_000, billable: true, utilization: 0.71, attrition: 0.16, avgSalary: 120_000, leader: 'Ana Torres' },
    { id: 'grc', name: 'GRC', headcount: 14, payroll: 1_540_000, billable: true, utilization: 0.68, attrition: 0.14, avgSalary: 110_000, leader: 'Roberto Silva' },
    { id: 'impl', name: 'Implementación', headcount: 16, payroll: 1_600_000, billable: true, utilization: 0.74, attrition: 0.19, avgSalary: 100_000, leader: 'Miguel Ángel R.' },
    { id: 'sales', name: 'Comercial', headcount: 12, payroll: 1_080_000, billable: false, utilization: null, attrition: 0.22, avgSalary: 90_000, leader: 'Patricia Núñez' },
    { id: 'product', name: 'Producto 4YOU', headcount: 8, payroll: 720_000, billable: false, utilization: null, attrition: 0.10, avgSalary: 90_000, leader: 'Daniel Ortiz' },
    { id: 'admin', name: 'Admin & Finanzas', headcount: 6, payroll: 420_000, billable: false, utilization: null, attrition: 0.08, avgSalary: 70_000, leader: 'Esther Ramírez' },
  ],
 
  topClients: [
    { id: 'sener', name: 'Secretaría de Energía', vertical: 'Gobierno', revenue: 24_800_000, margin: 0.31, projects: 5, status: 'green', tenure: 4.2, contact: 'Lic. Eduardo Vargas', renewal: 'Mar 2027', services: ['SOC/NOC', 'GRC', 'DFIR'], dso: 92 },
    { id: 'bbva', name: 'BBVA México', vertical: 'Financiero', revenue: 18_600_000, margin: 0.28, projects: 4, status: 'amber', tenure: 3.8, contact: 'Mtro. Andrés Romo', renewal: 'Ene 2027', services: ['SOC/NOC', 'DFIR', 'Implementación'], dso: 92 },
    { id: 'cfe', name: 'CFE', vertical: 'Energía', revenue: 15_400_000, margin: 0.24, projects: 3, status: 'amber', tenure: 2.9, contact: 'Ing. María L. Castro', renewal: 'Sep 2027', services: ['Implementación', 'GRC'], dso: 64 },
    { id: 'banorte', name: 'Banorte', vertical: 'Financiero', revenue: 12_800_000, margin: 0.32, projects: 3, status: 'green', tenure: 5.1, contact: 'Lic. Jorge Mendoza', renewal: 'Jun 2027', services: ['SOC/NOC', 'DFIR'], dso: 38 },
    { id: 'bimbo', name: 'Grupo Bimbo', vertical: 'Manufactura', revenue: 11_200_000, margin: 0.26, projects: 2, status: 'green', tenure: 3.4, contact: 'Mtra. Sandra Pérez', renewal: 'Nov 2027', services: ['SOC/NOC', 'GRC'], dso: 35 },
    { id: 'senado', name: 'Senado de la República', vertical: 'Gobierno', revenue: 9_800_000, margin: 0.18, projects: 2, status: 'red', tenure: 1.8, contact: 'Lic. Roberto Hdz', renewal: 'Abr 2027', services: ['SOC/NOC'], dso: 124 },
    { id: 'cemex', name: 'Cemex', vertical: 'Manufactura', revenue: 8_600_000, margin: 0.21, projects: 2, status: 'green', tenure: 4.7, contact: 'Ing. Pablo Lozano', renewal: 'Feb 2027', services: ['SOC/NOC', 'GRC', 'DFIR'], dso: 41 },
    { id: 'abc', name: 'Hospital ABC', vertical: 'Salud', revenue: 7_200_000, margin: 0.29, projects: 1, status: 'green', tenure: 2.3, contact: 'Dra. Laura Fdz', renewal: 'May 2027', services: ['GRC', 'DFIR'], dso: 47 },
  ],
 
  projectsAtRisk: [
    { id: 'p1', name: 'CFE — Implementación SIEM Fase 2', client: 'CFE', clientId: 'cfe', overrun: 0.35, currentMargin: 0.06, type: 'Sobrecosto HH', value: 8_400_000, completion: 0.62, owner: 'Miguel Ángel R.' },
    { id: 'p2', name: 'Senado — Servicio gestionado', client: 'Senado', clientId: 'senado', currentMargin: 0.18, type: 'Margen bajo target', value: 9_800_000, completion: 0.41, owner: 'Carlos Méndez' },
    { id: 'p3', name: 'BBVA — DFIR retainer', client: 'BBVA', clientId: 'bbva', currentMargin: 0.21, type: 'Cartera vencida 92d', value: 4_200_000, completion: 0.78, owner: 'Ana Torres' },
    { id: 'p4', name: 'Salud Digna — Cumplimiento NOM', client: 'Salud Digna', overrun: 0.18, currentMargin: 0.11, type: 'Scope creep', value: 2_800_000, completion: 0.55, owner: 'Roberto Silva' },
    { id: 'p5', name: 'Grupo Modelo — Pentest anual', client: 'Grupo Modelo', currentMargin: 0.13, type: 'Re-trabajo', value: 1_600_000, completion: 0.84, owner: 'Ana Torres' },
    { id: 'p6', name: 'IPN — Capacitación masiva', client: 'IPN', currentMargin: 0.09, type: 'Cobranza pública', value: 1_200_000, completion: 0.92, owner: 'Patricia Núñez' },
  ],
 
  monthly: [
    { mes: 'Nov 25', ingresos: 14.8, ebitda: 2.9, nomina: 9.8, cobranza: 13.2, costoOp: 11.9 },
    { mes: 'Dic 25', ingresos: 16.2, ebitda: 3.4, nomina: 9.9, cobranza: 15.4, costoOp: 12.8 },
    { mes: 'Ene 26', ingresos: 15.4, ebitda: 3.1, nomina: 10.1, cobranza: 14.9, costoOp: 12.3 },
    { mes: 'Feb 26', ingresos: 16.8, ebitda: 3.6, nomina: 10.4, cobranza: 16.1, costoOp: 13.2 },
    { mes: 'Mar 26', ingresos: 17.6, ebitda: 3.9, nomina: 10.6, cobranza: 17.2, costoOp: 13.7 },
    { mes: 'Abr 26', ingresos: 18.4, ebitda: 4.1, nomina: 10.8, cobranza: 17.8, costoOp: 14.3 },
    { mes: 'May 26', ingresos: 17.9, ebitda: 3.8, nomina: 10.9, cobranza: 16.4, costoOp: 14.1 },
    { mes: 'Jun 26', ingresos: 19.2, ebitda: 4.3, nomina: 11.0, cobranza: 18.6, costoOp: 14.9 },
    { mes: 'Jul 26', ingresos: 18.6, ebitda: 4.0, nomina: 11.1, cobranza: 17.9, costoOp: 14.6 },
    { mes: 'Ago 26', ingresos: 20.1, ebitda: 4.6, nomina: 11.2, cobranza: 19.3, costoOp: 15.5 },
    { mes: 'Sep 26', ingresos: 21.3, ebitda: 4.9, nomina: 11.2, cobranza: 20.1, costoOp: 16.4 },
    { mes: 'Oct 26', ingresos: 21.8, ebitda: 5.0, nomina: 11.2, cobranza: 20.8, costoOp: 16.8 },
  ],
 
  benchmarks: [
    { id: 'growth', metric: 'Crecimiento YoY', s4b: 0.227, industry: 0.135, topQ: 0.240, format: 'pct', higherBetter: true, trend: [0.142, 0.156, 0.178, 0.195, 0.211, 0.227] },
    { id: 'gm', metric: 'Margen bruto', s4b: 0.520, industry: 0.555, topQ: 0.620, format: 'pct', higherBetter: true, trend: [0.488, 0.495, 0.502, 0.508, 0.514, 0.520] },
    { id: 'ebitda', metric: 'Margen EBITDA', s4b: 0.210, industry: 0.180, topQ: 0.270, format: 'pct', higherBetter: true, trend: [0.182, 0.189, 0.197, 0.201, 0.207, 0.210] },
    { id: 'rule40', metric: 'Regla del 40', s4b: 0.437, industry: 0.315, topQ: 0.500, format: 'pct', higherBetter: true, trend: [0.324, 0.345, 0.375, 0.396, 0.418, 0.437] },
    { id: 'dso', metric: 'DSO (días cobranza)', s4b: 58, industry: 62, topQ: 45, format: 'days', higherBetter: false, trend: [62, 61, 60, 59, 58, 58] },
    { id: 'util', metric: 'Utilización facturable', s4b: 0.740, industry: 0.700, topQ: 0.820, format: 'pct', higherBetter: true, trend: [0.71, 0.72, 0.73, 0.73, 0.74, 0.74] },
    { id: 'rev_emp', metric: 'Ingreso por colaborador', s4b: 1_771_429, industry: 1_850_000, topQ: 2_400_000, format: 'mxn', higherBetter: true, trend: [1_540_000, 1_590_000, 1_640_000, 1_690_000, 1_740_000, 1_771_429] },
    { id: 'attr', metric: 'Attrition 12m', s4b: 0.180, industry: 0.220, topQ: 0.120, format: 'pct', higherBetter: false, trend: [0.21, 0.20, 0.19, 0.19, 0.18, 0.18] },
    { id: 'nrr', metric: 'Net Revenue Retention', s4b: 1.140, industry: 1.080, topQ: 1.250, format: 'pct', higherBetter: true, trend: [1.08, 1.09, 1.11, 1.12, 1.13, 1.14] },
  ],
 
  alerts: [
    { id: 'a1', level: 'high', area: 'Cartera', msg: 'BBVA México · 92 días vencidos · $4.8M', action: 'Escalación CFO', impact: 4_800_000, owner: 'Paco Bernal', dueDate: '15 Nov 2026', status: 'En proceso', detail: 'Cliente solicitó extensión de plazo por reorganización en su área de procurement.' },
    { id: 'a2', level: 'high', area: 'Margen', msg: 'Senado de la República · margen 18% (target 25%)', action: 'Renegociar T&M', impact: 686_000, owner: 'Layla Delgadillo', dueDate: '30 Nov 2026', status: 'Sin iniciar', detail: 'Servicio fijo mensual con horas extras no facturadas.' },
    { id: 'a3', level: 'med', area: 'Proyecto', msg: 'CFE SIEM Fase 2 · 35% sobrecosto HH', action: 'Revisión scope', impact: 1_400_000, owner: 'Miguel Ángel R.', dueDate: '20 Nov 2026', status: 'En proceso', detail: 'Scope creep en integración con SCADA legacy.' },
    { id: 'a4', level: 'med', area: 'Talento', msg: 'Attrition SOC 24% LTM (target 18%)', action: 'Plan retención', impact: 2_100_000, owner: 'Carlos Méndez', dueDate: '15 Dic 2026', status: 'En proceso', detail: 'Salida de 9 analistas en 12 meses.' },
    { id: 'a5', level: 'med', area: 'Pipeline', msg: 'Gobierno: ciclo ventas se alargó a 142d', action: 'Diversificar', impact: null, owner: 'Patricia Núñez', dueDate: '31 Dic 2026', status: 'Sin iniciar', detail: 'Procesos de licitación más largos.' },
    { id: 'a6', level: 'low', area: 'Cumplimiento', msg: 'Re-auditoría ISO 27001 vence en 47 días', action: 'Calendarizar', impact: null, owner: 'Roberto Silva', dueDate: '24 Dic 2026', status: 'Sin iniciar', detail: 'Calendario de auditor interno y externo.' },
  ],
 
  clientHistory: {
    bbva: { months: ['May', 'Jun', 'Jul', 'Ago', 'Sep', 'Oct'], revenue: [2.8, 2.9, 3.1, 3.0, 3.2, 3.4], margin: [0.26, 0.27, 0.28, 0.27, 0.29, 0.28] },
    cfe: { months: ['May', 'Jun', 'Jul', 'Ago', 'Sep', 'Oct'], revenue: [2.1, 2.2, 2.4, 2.5, 2.6, 2.6], margin: [0.28, 0.27, 0.25, 0.24, 0.23, 0.24] },
    sener: { months: ['May', 'Jun', 'Jul', 'Ago', 'Sep', 'Oct'], revenue: [3.8, 4.0, 4.1, 4.2, 4.3, 4.4], margin: [0.30, 0.31, 0.31, 0.32, 0.32, 0.31] },
  },
};
 
// ============================================================================
// UTILS
// ============================================================================
const fmt = {
  mxn: (n) => '$' + (n / 1_000_000).toFixed(1) + 'M',
  mxnK: (n) => '$' + (n / 1_000).toFixed(0) + 'K',
  pct: (n, d = 1) => (n * 100).toFixed(d) + '%',
  pctSigned: (n, d = 1) => (n >= 0 ? '+' : '') + (n * 100).toFixed(d) + '%',
};
const formatBenchValue = (val, format) => {
  if (format === 'pct') return (val * 100).toFixed(1) + '%';
  if (format === 'mxn') return '$' + (val / 1_000_000).toFixed(2) + 'M';
  if (format === 'days') return val + 'd';
  return val;
};
const delta = (s4b, ref, higherBetter = true) => {
  const diff = s4b - ref;
  const pct = ref !== 0 ? diff / Math.abs(ref) : 0;
  const good = higherBetter ? diff >= 0 : diff <= 0;
  return { diff, pct, good };
};
 
// ============================================================================
// MOCKUP 1 — COMMAND CENTER
// ============================================================================
function MockupTerminal() {
  const [section, setSection] = useState('overview');
  const [drill, setDrill] = useState(null);
  const sections = [
    { id: 'overview', label: 'OVERVIEW', k: 'F1' },
    { id: 'finance', label: 'FINANZAS', k: 'F2' },
    { id: 'ops', label: 'OPERACIÓN', k: 'F3' },
    { id: 'people', label: 'TALENTO', k: 'F4' },
    { id: 'bench', label: 'BENCHMARK', k: 'F5' },
    { id: 'alerts', label: 'ALERTAS', k: 'F6' },
  ];
  const renderContent = () => {
    if (drill?.type === 'client') return <TerminalClientDrill id={drill.id} onBack={() => setDrill(null)} />;
    if (drill?.type === 'project') return <TerminalProjectDrill id={drill.id} onBack={() => setDrill(null)} />;
    if (drill?.type === 'area') return <TerminalAreaDrill id={drill.id} onBack={() => setDrill(null)} />;
    if (drill?.type === 'metric') return <TerminalMetricDrill id={drill.id} onBack={() => setDrill(null)} />;
    if (drill?.type === 'alert') return <TerminalAlertDrill id={drill.id} onBack={() => setDrill(null)} />;
    if (drill?.type === 'segment') return <TerminalSegmentDrill id={drill.id} onBack={() => setDrill(null)} />;
    if (section === 'overview') return <TerminalOverview onDrill={setDrill} />;
    if (section === 'finance') return <TerminalFinance />;
    if (section === 'ops') return <TerminalOps onDrill={setDrill} />;
    if (section === 'people') return <TerminalPeople onDrill={setDrill} />;
    if (section === 'bench') return <TerminalBench onDrill={setDrill} />;
    if (section === 'alerts') return <TerminalAlerts onDrill={setDrill} />;
  };
  return (
    <div className="min-h-screen bg-[#0a0e0a] text-[#d4f0d4]" style={{ fontFamily: '"JetBrains Mono","IBM Plex Mono",monospace' }}>
      <div className="border-b border-emerald-900/60 bg-black/40 px-4 py-2 flex items-center justify-between text-[11px] uppercase tracking-[0.18em]">
        <div className="flex items-center gap-3">
          <div className="w-2 h-2 rounded-full bg-emerald-400 animate-pulse"></div>
          <span className="text-emerald-400 font-bold">S4B://COMMAND_CENTER</span>
          <span className="text-emerald-700">|</span>
          <span className="text-emerald-600">{company.period}</span>
        </div>
        <div className="flex items-center gap-3">
          <span className="text-emerald-600">USR: layla.d</span>
          <span className="text-amber-400">●</span>
          <span className="text-amber-400">3 ALRT</span>
        </div>
      </div>
      <div className="border-b border-emerald-900/60 bg-black/20 flex">
        {sections.map((s) => (
          <button key={s.id} onClick={() => { setSection(s.id); setDrill(null); }}
            className={`px-5 py-2 text-[11px] uppercase tracking-[0.2em] border-r border-emerald-900/60 transition ${
              section === s.id && !drill ? 'bg-emerald-500/15 text-emerald-300 border-b-2 border-b-emerald-400' :
              'text-emerald-700 hover:text-emerald-400 hover:bg-emerald-500/5'
            }`}>
            <span className="text-emerald-900/80 mr-2">[{s.k}]</span>{s.label}
          </button>
        ))}
      </div>
      {renderContent()}
      <div className="border-t border-emerald-900/60 bg-black/40 px-3 py-2 text-[10px] uppercase tracking-wider text-emerald-700">
        CMD → [D]rill-down · [E]xport · [F]ilter · [B]enchmark · LATENCY: 12ms
      </div>
    </div>
  );
}
 
const TermPanel = ({ title, right, children, className = '' }) => (
  <div className={`border border-emerald-900/60 bg-black/40 ${className}`}>
    <div className="px-3 py-2 border-b border-emerald-900/60 flex items-center justify-between">
      <span className="text-[10px] uppercase tracking-[0.2em] text-emerald-500">▮ {title}</span>
      {right && <span className="text-[10px] text-emerald-700">{right}</span>}
    </div>
    {children}
  </div>
);
const TermBack = ({ onBack, label }) => (
  <div className="px-4 py-2 border-b border-emerald-900/60 bg-black/20 flex items-center gap-3">
    <button onClick={onBack} className="text-[10px] uppercase tracking-[0.2em] text-emerald-500 hover:text-emerald-300 inline-flex items-center gap-1">
      <ArrowLeft className="w-3 h-3" /> BACK
    </button>
    <span className="text-emerald-900">/</span>
    <span className="text-[10px] uppercase tracking-[0.2em] text-emerald-300">{label}</span>
  </div>
);
const Stat = ({ l, v, d, dg, warn }) => (
  <div className="bg-black p-3">
    <div className="text-[9px] text-emerald-700 uppercase tracking-[0.2em]">{l}</div>
    <div className={`text-2xl font-bold mt-1 tabular-nums ${warn ? 'text-amber-400' : 'text-emerald-300'}`}>{v}</div>
    {d && <div className={`text-[10px] mt-1 ${dg ? 'text-emerald-500' : 'text-amber-400'}`}>{d}</div>}
  </div>
);
 
function TerminalOverview({ onDrill }) {
  return (
    <div className="p-4 space-y-3">
      <div className="grid grid-cols-6 gap-px bg-emerald-900/40 border border-emerald-900/60">
        <Stat l="REVENUE LTM" v={fmt.mxn(company.finance.revenueLTM)} d="+22.7%" dg />
        <Stat l="EBITDA" v={fmt.mxn(company.finance.ebitdaLTM)} d="21.0% mg" dg />
        <Stat l="CASH" v={fmt.mxn(company.finance.cash)} d="WC 51.8M" dg />
        <Stat l="AR / DSO" v={fmt.mxn(company.finance.ar)} d="58 días" />
        <Stat l="HEADCOUNT" v={company.people.headcount} d="74% util" dg />
        <Stat l="PROY ACTIVOS" v={company.ops.activeProjects} d="6 risk" />
      </div>
      <div className="grid grid-cols-12 gap-3">
        <TermPanel title="INGRESOS_MENSUALES.LIVE" right="12M | MXN" className="col-span-8">
          <div className="p-2 h-64">
            <ResponsiveContainer width="100%" height="100%">
              <ComposedChart data={company.monthly}>
                <CartesianGrid stroke="#0d2b18" strokeDasharray="2 2" />
                <XAxis dataKey="mes" stroke="#3b6e3b" tick={{ fontSize: 9, fill: '#5a8a5a' }} />
                <YAxis stroke="#3b6e3b" tick={{ fontSize: 9, fill: '#5a8a5a' }} />
                <Tooltip contentStyle={{ background: '#0a0e0a', border: '1px solid #10b981', fontSize: 11 }} />
                <Bar dataKey="nomina" fill="#dc2626" opacity={0.4} />
                <Bar dataKey="ingresos" fill="#10b981" />
                <Line type="monotone" dataKey="ebitda" stroke="#fbbf24" strokeWidth={2} dot={{ fill: '#fbbf24', r: 3 }} />
              </ComposedChart>
            </ResponsiveContainer>
          </div>
        </TermPanel>
        <TermPanel title="MIX_LINEAS_NEGOCIO" className="col-span-4">
          <div className="p-3 space-y-2">
            {company.segments.map((s) => (
              <button key={s.id} onClick={() => onDrill({ type: 'segment', id: s.id })} className="w-full text-left hover:bg-emerald-500/5 p-1 -m-1 rounded">
                <div className="flex items-center justify-between text-[10px] mb-1">
                  <span className="text-emerald-400">{s.name}</span>
                  <span className="text-emerald-600 tabular-nums">{fmt.mxn(s.revenue)}</span>
                </div>
                <div className="h-2 bg-emerald-950 rounded-sm overflow-hidden">
                  <div style={{ width: fmt.pct(s.share, 0), background: s.color }} className="h-full"></div>
                </div>
                <div className="flex justify-between mt-0.5">
                  <span className="text-[9px] text-emerald-700">mg {fmt.pct(s.margin)}</span>
                  <span className={`text-[9px] tabular-nums ${s.growth >= 0.15 ? 'text-emerald-400' : s.growth >= 0 ? 'text-amber-400' : 'text-red-500'}`}>{fmt.pctSigned(s.growth)}</span>
                </div>
              </button>
            ))}
          </div>
        </TermPanel>
        <TermPanel title="TOP_CLIENTS" right="8 of 31" className="col-span-8">
          <table className="w-full text-[11px] tabular-nums">
            <thead><tr className="text-emerald-700 text-[9px] uppercase tracking-wider border-b border-emerald-900/60">
              <th className="text-left px-3 py-1.5">CLIENTE</th><th className="text-left px-3 py-1.5">VERT</th>
              <th className="text-right px-3 py-1.5">REV LTM</th><th className="text-right px-3 py-1.5">MG</th>
              <th className="text-right px-3 py-1.5">PRJ</th><th className="text-center px-3 py-1.5">ST</th>
            </tr></thead>
            <tbody>{company.topClients.map((c) => (
              <tr key={c.id} onClick={() => onDrill({ type: 'client', id: c.id })} className="border-b border-emerald-950/50 hover:bg-emerald-500/5 cursor-pointer">
                <td className="px-3 py-1.5 text-emerald-300">{c.name}</td>
                <td className="px-3 py-1.5 text-emerald-600 text-[10px]">{c.vertical}</td>
                <td className="px-3 py-1.5 text-right text-emerald-400">{fmt.mxn(c.revenue)}</td>
                <td className={`px-3 py-1.5 text-right ${c.margin >= 0.25 ? 'text-emerald-400' : c.margin >= 0.20 ? 'text-amber-400' : 'text-red-500'}`}>{fmt.pct(c.margin)}</td>
                <td className="px-3 py-1.5 text-right text-emerald-500">{c.projects}</td>
                <td className="px-3 py-1.5 text-center"><span className={`inline-block w-2 h-2 rounded-full ${c.status === 'green' ? 'bg-emerald-400' : c.status === 'amber' ? 'bg-amber-400' : 'bg-red-500'}`}></span></td>
              </tr>))}
            </tbody>
          </table>
        </TermPanel>
        <div className="col-span-4 border border-red-900/60 bg-black/40">
          <div className="px-3 py-2 border-b border-red-900/60 flex items-center justify-between">
            <span className="text-[10px] uppercase tracking-[0.2em] text-red-400">▮ ALERTS.STREAM</span>
            <span className="text-[10px] text-red-600 animate-pulse">● LIVE</span>
          </div>
          <div className="divide-y divide-red-950/50">{company.alerts.slice(0, 5).map((a) => (
            <button key={a.id} onClick={() => onDrill({ type: 'alert', id: a.id })} className="w-full text-left px-3 py-2 hover:bg-red-500/5">
              <div className="flex items-start gap-2">
                <span className={`text-[9px] uppercase font-bold tracking-wider px-1.5 py-0.5 rounded-sm ${a.level === 'high' ? 'bg-red-500/20 text-red-400 border border-red-500/40' : a.level === 'med' ? 'bg-amber-500/20 text-amber-400 border border-amber-500/40' : 'bg-emerald-500/20 text-emerald-400 border border-emerald-500/40'}`}>{a.level}</span>
                <span className="text-[9px] text-emerald-700">{a.area}</span>
              </div>
              <div className="text-[11px] text-emerald-300 mt-1">{a.msg}</div>
              <div className="text-[10px] text-emerald-600 mt-0.5">→ {a.action}</div>
            </button>))}
          </div>
        </div>
      </div>
    </div>
  );
}
 
function TerminalFinance() {
  const f = company.finance;
  const pl = [
    { cat: 'Ingresos', val: f.revenueLTM, pct: 1.0 },
    { cat: '(-) Costo de servicio', val: -(f.revenueLTM - f.grossProfit), pct: -0.480 },
    { cat: 'Utilidad bruta', val: f.grossProfit, pct: 0.520, bold: true },
    { cat: '(-) Gasto operación', val: -(f.grossProfit - f.ebitdaLTM), pct: -0.310 },
    { cat: 'EBITDA', val: f.ebitdaLTM, pct: 0.210, bold: true },
    { cat: '(-) D&A + Financ + Imp', val: -(f.ebitdaLTM - f.netIncomeLTM), pct: -0.085 },
    { cat: 'Utilidad neta', val: f.netIncomeLTM, pct: 0.125, bold: true },
  ];
  return (
    <div className="p-4 space-y-3">
      <div className="grid grid-cols-5 gap-px bg-emerald-900/40 border border-emerald-900/60">
        <Stat l="CASH" v={fmt.mxn(f.cash)} d="Disponible" dg />
        <Stat l="AR" v={fmt.mxn(f.ar)} d={f.dso + 'd DSO'} />
        <Stat l="AP" v={fmt.mxn(f.ap)} d={f.dpo + 'd DPO'} dg />
        <Stat l="WORKING CAP" v={fmt.mxn(f.workingCapital)} d="Quick 1.84x" dg />
        <Stat l="DEUDA/EBITDA" v={f.debtToEbitda + 'x'} d="Saludable" dg />
      </div>
      <div className="grid grid-cols-12 gap-3">
        <TermPanel title="P&L_LTM" className="col-span-7">
          <table className="w-full text-[11px] tabular-nums"><tbody>{pl.map((r, i) => (
            <tr key={i} className={`border-b border-emerald-950/50 ${r.bold ? 'bg-emerald-500/5' : ''}`}>
              <td className={`px-3 py-2 ${r.bold ? 'text-emerald-300 font-bold' : 'text-emerald-500'}`}>{r.cat}</td>
              <td className={`px-3 py-2 text-right ${r.val < 0 ? 'text-red-400' : r.bold ? 'text-emerald-300 font-bold' : 'text-emerald-400'}`}>{r.val < 0 ? '-' : ''}{fmt.mxn(Math.abs(r.val))}</td>
              <td className="px-3 py-2 text-right text-emerald-700 text-[10px]">{(r.pct * 100).toFixed(1)}%</td>
            </tr>))}</tbody></table>
        </TermPanel>
        <TermPanel title="CREDITO_DEUDA" className="col-span-5">
          <div className="p-4 space-y-4">
            <div>
              <div className="flex justify-between text-[10px] mb-1">
                <span className="text-emerald-700">LÍNEA REVOLVENTE</span>
                <span className="text-emerald-400 tabular-nums">{fmt.mxn(f.creditUsed)} / {fmt.mxn(f.creditTotal)}</span>
              </div>
              <div className="h-3 bg-emerald-950"><div className="h-full bg-amber-500" style={{ width: '36%' }}></div></div>
            </div>
            <div className="grid grid-cols-2 gap-3 text-[11px]">
              {[['DEUDA TOTAL', fmt.mxn(f.creditUsed)], ['DSCR', '3.84x'], ['QUICK RATIO', f.quickRatio + 'x'], ['D/EBITDA', f.debtToEbitda + 'x']].map(([k, v]) => (
                <div key={k} className="border-l border-emerald-900 pl-3">
                  <div className="text-emerald-700 text-[9px] uppercase tracking-wider">{k}</div>
                  <div className="text-emerald-300 text-lg font-bold tabular-nums">{v}</div>
                </div>))}
            </div>
          </div>
        </TermPanel>
      </div>
    </div>
  );
}
 
function TerminalOps({ onDrill }) {
  return (
    <div className="p-4 space-y-3">
      <div className="grid grid-cols-6 gap-px bg-emerald-900/40 border border-emerald-900/60">
        <Stat l="PROY ACTIVOS" v={company.ops.activeProjects} />
        <Stat l="CLIENTES" v={company.ops.activeClients} />
        <Stat l="BACKLOG" v={fmt.mxn(company.ops.backlog)} />
        <Stat l="PIPELINE" v={fmt.mxn(company.ops.pipeline)} />
        <Stat l="NPS" v={company.ops.nps} />
        <Stat l="SLA" v={fmt.pct(company.ops.slaCompliance, 1)} dg />
      </div>
      <TermPanel title="PROYECTOS_EN_RIESGO">
        <table className="w-full text-[11px] tabular-nums">
          <thead><tr className="text-emerald-700 text-[9px] uppercase tracking-wider border-b border-emerald-900/60">
            <th className="text-left px-3 py-1.5">PROYECTO</th><th className="text-left px-3 py-1.5">RIESGO</th>
            <th className="text-right px-3 py-1.5">VALOR</th><th className="text-right px-3 py-1.5">MG</th><th className="text-right px-3 py-1.5">% AVANCE</th>
          </tr></thead>
          <tbody>{company.projectsAtRisk.map((p) => (
            <tr key={p.id} onClick={() => onDrill({ type: 'project', id: p.id })} className="border-b border-emerald-950/50 hover:bg-emerald-500/5 cursor-pointer">
              <td className="px-3 py-2 text-emerald-300">{p.name}</td>
              <td className="px-3 py-2 text-amber-400 text-[10px]">{p.type}</td>
              <td className="px-3 py-2 text-right text-emerald-400">{fmt.mxn(p.value)}</td>
              <td className={`px-3 py-2 text-right ${p.currentMargin < 0.15 ? 'text-red-500' : 'text-amber-400'}`}>{fmt.pct(p.currentMargin)}</td>
              <td className="px-3 py-2 text-right text-emerald-600">{fmt.pct(p.completion, 0)}</td>
            </tr>))}</tbody>
        </table>
      </TermPanel>
      <TermPanel title="TODOS_LOS_CLIENTES" right="CLICK PARA DETALLE">
        <table className="w-full text-[11px] tabular-nums">
          <thead><tr className="text-emerald-700 text-[9px] uppercase tracking-wider border-b border-emerald-900/60">
            <th className="text-left px-3 py-1.5">CLIENTE</th><th className="text-left px-3 py-1.5">VERTICAL</th>
            <th className="text-right px-3 py-1.5">REVENUE</th><th className="text-right px-3 py-1.5">MARGEN</th>
            <th className="text-right px-3 py-1.5">DSO</th><th className="text-right px-3 py-1.5">RENOVACIÓN</th>
          </tr></thead>
          <tbody>{company.topClients.map((c) => (
            <tr key={c.id} onClick={() => onDrill({ type: 'client', id: c.id })} className="border-b border-emerald-950/50 hover:bg-emerald-500/5 cursor-pointer">
              <td className="px-3 py-1.5 text-emerald-300">{c.name}</td>
              <td className="px-3 py-1.5 text-emerald-600">{c.vertical}</td>
              <td className="px-3 py-1.5 text-right text-emerald-400">{fmt.mxn(c.revenue)}</td>
              <td className={`px-3 py-1.5 text-right ${c.margin >= 0.25 ? 'text-emerald-400' : c.margin >= 0.20 ? 'text-amber-400' : 'text-red-500'}`}>{fmt.pct(c.margin)}</td>
              <td className={`px-3 py-1.5 text-right ${c.dso > 70 ? 'text-amber-400' : 'text-emerald-500'}`}>{c.dso}d</td>
              <td className="px-3 py-1.5 text-right text-emerald-600 text-[10px]">{c.renewal}</td>
            </tr>))}</tbody>
        </table>
      </TermPanel>
    </div>
  );
}
 
function TerminalPeople({ onDrill }) {
  const p = company.people;
  return (
    <div className="p-4 space-y-3">
      <div className="grid grid-cols-5 gap-px bg-emerald-900/40 border border-emerald-900/60">
        <Stat l="HEADCOUNT" v={p.headcount} d="+8 YoY" dg />
        <Stat l="NÓMINA/MES" v={fmt.mxn(p.payrollMonthly)} d="56% ingresos" />
        <Stat l="UTILIZACIÓN" v={fmt.pct(p.utilizationRate)} d="tgt 78%" />
        <Stat l="ATTRITION 12M" v={fmt.pct(p.attrition12m)} d="soc 24%" warn />
        <Stat l="REV/EMPL" v={fmt.mxn(p.revenuePerEmployee)} d="ind 1.85M" />
      </div>
      <TermPanel title="ÁREAS.DETAIL" right="CLICK PARA DRILL-DOWN">
        <table className="w-full text-[11px] tabular-nums">
          <thead><tr className="text-emerald-700 text-[9px] uppercase tracking-wider border-b border-emerald-900/60">
            <th className="text-left px-3 py-1.5">ÁREA</th><th className="text-left px-3 py-1.5">LÍDER</th>
            <th className="text-right px-3 py-1.5">HC</th><th className="text-right px-3 py-1.5">NÓMINA</th>
            <th className="text-right px-3 py-1.5">UTIL</th><th className="text-right px-3 py-1.5">ATTR</th>
          </tr></thead>
          <tbody>{company.areas.map((a) => (
            <tr key={a.id} onClick={() => onDrill({ type: 'area', id: a.id })} className="border-b border-emerald-950/50 hover:bg-emerald-500/5 cursor-pointer">
              <td className="px-3 py-2 text-emerald-300">{a.name}</td>
              <td className="px-3 py-2 text-emerald-600 text-[10px]">{a.leader}</td>
              <td className="px-3 py-2 text-right text-emerald-400">{a.headcount}</td>
              <td className="px-3 py-2 text-right text-emerald-400">{fmt.mxn(a.payroll)}</td>
              <td className={`px-3 py-2 text-right ${a.utilization === null ? 'text-emerald-800' : a.utilization >= 0.78 ? 'text-emerald-400' : 'text-amber-400'}`}>
                {a.utilization === null ? '—' : fmt.pct(a.utilization, 0)}</td>
              <td className={`px-3 py-2 text-right ${a.attrition > 0.20 ? 'text-amber-400' : 'text-emerald-500'}`}>{fmt.pct(a.attrition)}</td>
            </tr>))}</tbody>
        </table>
      </TermPanel>
    </div>
  );
}
 
function TerminalBench({ onDrill }) {
  return (
    <div className="p-4 space-y-3">
      <TermPanel title="INDUSTRY_SCORECARD" right="42 MSPs LATAM | $50M-$500M">
        <table className="w-full text-[11px] tabular-nums">
          <thead><tr className="text-emerald-700 text-[9px] uppercase tracking-wider border-b border-emerald-900/60">
            <th className="text-left px-3 py-1.5">MÉTRICA</th><th className="text-right px-3 py-1.5">S4B</th>
            <th className="text-right px-3 py-1.5">SECTOR</th><th className="text-right px-3 py-1.5">TOP Q</th>
            <th className="text-center px-3 py-1.5">RANK</th>
          </tr></thead>
          <tbody>{company.benchmarks.map((b) => {
            const d = delta(b.s4b, b.industry, b.higherBetter);
            const dTop = delta(b.s4b, b.topQ, b.higherBetter);
            const tier = dTop.good ? 'TOP Q' : d.good ? 'SOBRE MED' : 'BAJO MED';
            const c = dTop.good ? 'text-emerald-400' : d.good ? 'text-blue-400' : 'text-amber-400';
            return (
              <tr key={b.id} onClick={() => onDrill({ type: 'metric', id: b.id })} className="border-b border-emerald-950/50 hover:bg-emerald-500/5 cursor-pointer">
                <td className="px-3 py-2 text-emerald-300">{b.metric}</td>
                <td className={`px-3 py-2 text-right font-bold ${c}`}>{formatBenchValue(b.s4b, b.format)}</td>
                <td className="px-3 py-2 text-right text-emerald-600">{formatBenchValue(b.industry, b.format)}</td>
                <td className="px-3 py-2 text-right text-amber-400">{formatBenchValue(b.topQ, b.format)}</td>
                <td className={`px-3 py-2 text-center text-[9px] uppercase tracking-wider ${c}`}>{tier}</td>
              </tr>);
          })}</tbody>
        </table>
      </TermPanel>
    </div>
  );
}
 
function TerminalAlerts({ onDrill }) {
  return (
    <div className="p-4 space-y-3">
      <div className="grid grid-cols-3 gap-px bg-emerald-900/40 border border-emerald-900/60">
        {[
          { l: 'HIGH', v: company.alerts.filter((a) => a.level === 'high').length, c: 'text-red-400' },
          { l: 'MEDIUM', v: company.alerts.filter((a) => a.level === 'med').length, c: 'text-amber-400' },
          { l: 'LOW', v: company.alerts.filter((a) => a.level === 'low').length, c: 'text-emerald-400' },
        ].map((k) => (
          <div key={k.l} className="bg-black p-4">
            <div className="text-[10px] text-emerald-700 uppercase tracking-[0.2em]">{k.l} PRIORITY</div>
            <div className={`text-4xl font-bold mt-2 tabular-nums ${k.c}`}>{k.v}</div>
          </div>))}
      </div>
      <TermPanel title="ALERT_QUEUE">
        <table className="w-full text-[11px] tabular-nums">
          <thead><tr className="text-emerald-700 text-[9px] uppercase tracking-wider border-b border-emerald-900/60">
            <th className="text-left px-3 py-1.5">LEVEL</th><th className="text-left px-3 py-1.5">ÁREA</th>
            <th className="text-left px-3 py-1.5">DESCRIPCIÓN</th><th className="text-left px-3 py-1.5">OWNER</th>
            <th className="text-right px-3 py-1.5">IMPACTO</th><th className="text-left px-3 py-1.5">DUE</th>
          </tr></thead>
          <tbody>{company.alerts.map((a) => (
            <tr key={a.id} onClick={() => onDrill({ type: 'alert', id: a.id })} className="border-b border-emerald-950/50 hover:bg-emerald-500/5 cursor-pointer">
              <td className="px-3 py-2"><span className={`text-[9px] uppercase font-bold tracking-wider px-1.5 py-0.5 rounded-sm ${a.level === 'high' ? 'bg-red-500/20 text-red-400 border border-red-500/40' : a.level === 'med' ? 'bg-amber-500/20 text-amber-400 border border-amber-500/40' : 'bg-emerald-500/20 text-emerald-400 border border-emerald-500/40'}`}>{a.level}</span></td>
              <td className="px-3 py-2 text-emerald-600">{a.area}</td>
              <td className="px-3 py-2 text-emerald-300">{a.msg}</td>
              <td className="px-3 py-2 text-emerald-500 text-[10px]">{a.owner}</td>
              <td className="px-3 py-2 text-right text-amber-400">{a.impact ? fmt.mxn(a.impact) : '—'}</td>
              <td className="px-3 py-2 text-emerald-600 text-[10px]">{a.dueDate}</td>
            </tr>))}</tbody>
        </table>
      </TermPanel>
    </div>
  );
}
 
function TerminalClientDrill({ id, onBack }) {
  const c = company.topClients.find((x) => x.id === id) || company.topClients[0];
  const hist = company.clientHistory[id] || company.clientHistory.bbva;
  const histData = hist.months.map((m, i) => ({ mes: m, ingresos: hist.revenue[i], margen: hist.margin[i] * 100 }));
  return (
    <div>
      <TermBack onBack={onBack} label={`CLIENT > ${c.name.toUpperCase()}`} />
      <div className="p-4 space-y-3">
        <div className="grid grid-cols-12 gap-3">
          <TermPanel title="CLIENT_PROFILE" className="col-span-4">
            <div className="p-4 space-y-3 text-[11px]">
              <div><div className="text-emerald-700 text-[9px] uppercase tracking-wider">RAZÓN SOCIAL</div><div className="text-emerald-300 text-lg font-bold mt-0.5">{c.name}</div></div>
              <div className="grid grid-cols-2 gap-3">
                <div><div className="text-emerald-700 text-[9px] uppercase tracking-wider">VERTICAL</div><div className="text-emerald-400">{c.vertical}</div></div>
                <div><div className="text-emerald-700 text-[9px] uppercase tracking-wider">ANTIGÜEDAD</div><div className="text-emerald-400">{c.tenure} años</div></div>
                <div><div className="text-emerald-700 text-[9px] uppercase tracking-wider">RENOVACIÓN</div><div className="text-emerald-400">{c.renewal}</div></div>
                <div><div className="text-emerald-700 text-[9px] uppercase tracking-wider">CONTACTO</div><div className="text-emerald-400">{c.contact}</div></div>
              </div>
              <div className="border-t border-emerald-900 pt-3">
                <div className="text-emerald-700 text-[9px] uppercase tracking-wider mb-2">SERVICIOS</div>
                {c.services.map((s) => <div key={s} className="text-emerald-400 text-[11px]">→ {s}</div>)}
              </div>
            </div>
          </TermPanel>
          <TermPanel title="REVENUE_TIMELINE_6M" className="col-span-8">
            <div className="p-2 h-56">
              <ResponsiveContainer width="100%" height="100%">
                <ComposedChart data={histData}>
                  <CartesianGrid stroke="#0d2b18" strokeDasharray="2 2" />
                  <XAxis dataKey="mes" stroke="#3b6e3b" tick={{ fontSize: 9, fill: '#5a8a5a' }} />
                  <YAxis yAxisId="left" stroke="#3b6e3b" tick={{ fontSize: 9, fill: '#5a8a5a' }} />
                  <YAxis yAxisId="right" orientation="right" stroke="#3b6e3b" tick={{ fontSize: 9, fill: '#5a8a5a' }} />
                  <Tooltip contentStyle={{ background: '#0a0e0a', border: '1px solid #10b981', fontSize: 11 }} />
                  <Bar yAxisId="left" dataKey="ingresos" fill="#10b981" />
                  <Line yAxisId="right" type="monotone" dataKey="margen" stroke="#fbbf24" strokeWidth={2} />
                </ComposedChart>
              </ResponsiveContainer>
            </div>
          </TermPanel>
        </div>
      </div>
    </div>
  );
}
 
function TerminalProjectDrill({ id, onBack }) {
  const p = company.projectsAtRisk.find((x) => x.id === id) || company.projectsAtRisk[0];
  return (
    <div>
      <TermBack onBack={onBack} label={`PROJECT > ${p.name.toUpperCase()}`} />
      <div className="p-4 space-y-3">
        <div className="grid grid-cols-4 gap-3">
          {[['VALOR', fmt.mxn(p.value)], ['AVANCE', fmt.pct(p.completion, 0)], ['MARGEN', fmt.pct(p.currentMargin)], ['OWNER', p.owner]].map(([l, v]) => (
            <div key={l} className="border border-emerald-900/60 bg-black p-3">
              <div className="text-[9px] text-emerald-700 uppercase tracking-[0.2em]">{l}</div>
              <div className="text-2xl font-bold mt-1 tabular-nums text-emerald-300">{v}</div>
            </div>))}
        </div>
        <TermPanel title="DIAGNÓSTICO">
          <div className="p-4 text-[12px] text-emerald-300">Tipo: {p.type} · Cliente: {p.client}{p.overrun ? ` · Sobrecosto ${fmt.pct(p.overrun)}` : ''}</div>
        </TermPanel>
      </div>
    </div>
  );
}
 
function TerminalAreaDrill({ id, onBack }) {
  const a = company.areas.find((x) => x.id === id) || company.areas[0];
  return (
    <div>
      <TermBack onBack={onBack} label={`AREA > ${a.name.toUpperCase()}`} />
      <div className="p-4 space-y-3">
        <div className="grid grid-cols-5 gap-3">
          {[['HEADCOUNT', a.headcount], ['NÓMINA/MES', fmt.mxn(a.payroll)], ['SALARIO PROM', fmt.mxnK(a.avgSalary)], ['UTILIZACIÓN', a.utilization ? fmt.pct(a.utilization, 0) : '—'], ['ATTRITION', fmt.pct(a.attrition)]].map(([l, v]) => (
            <div key={l} className="border border-emerald-900/60 bg-black p-3">
              <div className="text-[9px] text-emerald-700 uppercase tracking-[0.2em]">{l}</div>
              <div className="text-2xl font-bold mt-1 tabular-nums text-emerald-300">{v}</div>
            </div>))}
        </div>
        <TermPanel title="LÍDER"><div className="p-4 text-[12px] text-emerald-300">{a.leader} · {a.billable ? 'Área facturable' : 'Área de soporte'}</div></TermPanel>
      </div>
    </div>
  );
}
 
function TerminalMetricDrill({ id, onBack }) {
  const m = company.benchmarks.find((x) => x.id === id) || company.benchmarks[0];
  const trendData = m.trend.map((v, i) => ({ p: 'P' + (i + 1), val: m.format === 'pct' ? v * 100 : v }));
  return (
    <div>
      <TermBack onBack={onBack} label={`METRIC > ${m.metric.toUpperCase()}`} />
      <div className="p-4 space-y-3">
        <div className="grid grid-cols-3 gap-3">
          {[['S4B', formatBenchValue(m.s4b, m.format), 'text-emerald-300'], ['SECTOR', formatBenchValue(m.industry, m.format), 'text-emerald-600'], ['TOP Q', formatBenchValue(m.topQ, m.format), 'text-amber-400']].map(([l, v, c]) => (
            <div key={l} className="border border-emerald-900/60 bg-black p-4">
              <div className="text-[10px] text-emerald-700 uppercase tracking-[0.2em]">{l}</div>
              <div className={`text-4xl font-bold mt-2 tabular-nums ${c}`}>{v}</div>
            </div>))}
        </div>
        <TermPanel title="EVOLUCIÓN_6_PERIODOS">
          <div className="p-2 h-64">
            <ResponsiveContainer width="100%" height="100%">
              <LineChart data={trendData}>
                <CartesianGrid stroke="#0d2b18" strokeDasharray="2 2" />
                <XAxis dataKey="p" stroke="#3b6e3b" tick={{ fontSize: 10, fill: '#5a8a5a' }} />
                <YAxis stroke="#3b6e3b" tick={{ fontSize: 10, fill: '#5a8a5a' }} />
                <Tooltip contentStyle={{ background: '#0a0e0a', border: '1px solid #10b981', fontSize: 11 }} />
                <Line type="monotone" dataKey="val" stroke="#10b981" strokeWidth={3} dot={{ r: 4, fill: '#10b981' }} />
                <ReferenceLine y={m.format === 'pct' ? m.industry * 100 : m.industry} stroke="#71717a" strokeDasharray="3 3" />
                <ReferenceLine y={m.format === 'pct' ? m.topQ * 100 : m.topQ} stroke="#fbbf24" strokeDasharray="3 3" />
              </LineChart>
            </ResponsiveContainer>
          </div>
        </TermPanel>
      </div>
    </div>
  );
}
 
function TerminalAlertDrill({ id, onBack }) {
  const a = company.alerts.find((x) => x.id === id) || company.alerts[0];
  return (
    <div>
      <TermBack onBack={onBack} label={`ALERT > ${a.area.toUpperCase()}`} />
      <div className="p-4 space-y-3">
        <div className={`border-l-4 ${a.level === 'high' ? 'border-red-500' : a.level === 'med' ? 'border-amber-500' : 'border-emerald-500'} bg-black p-4`}>
          <div className="text-emerald-300 text-xl mb-2">{a.msg}</div>
          <div className="text-emerald-600 text-[12px]">{a.detail}</div>
        </div>
        <div className="grid grid-cols-4 gap-3">
          {[['IMPACTO', a.impact ? fmt.mxn(a.impact) : '—'], ['OWNER', a.owner], ['DUE', a.dueDate], ['STATUS', a.status]].map(([l, v]) => (
            <div key={l} className="border border-emerald-900/60 bg-black p-3">
              <div className="text-[9px] text-emerald-700 uppercase tracking-[0.2em]">{l}</div>
              <div className="text-base font-bold mt-1 text-emerald-300">{v}</div>
            </div>))}
        </div>
      </div>
    </div>
  );
}
 
function TerminalSegmentDrill({ id, onBack }) {
  const s = company.segments.find((x) => x.id === id) || company.segments[0];
  return (
    <div>
      <TermBack onBack={onBack} label={`SEGMENT > ${s.name.toUpperCase()}`} />
      <div className="p-4 space-y-3">
        <div className="grid grid-cols-5 gap-3">
          {[['REVENUE', fmt.mxn(s.revenue)], ['SHARE', fmt.pct(s.share, 0)], ['MARGEN', fmt.pct(s.margin)], ['CRECIMIENTO', fmt.pctSigned(s.growth)], ['CLIENTES', s.clients]].map(([l, v]) => (
            <div key={l} className="border border-emerald-900/60 bg-black p-3">
              <div className="text-[9px] text-emerald-700 uppercase tracking-[0.2em]">{l}</div>
              <div className="text-2xl font-bold mt-1 tabular-nums text-emerald-300">{v}</div>
            </div>))}
        </div>
      </div>
    </div>
  );
}
 
// ============================================================================
// MOCKUP 3 — MODULAR SAAS (Notion / Linear-style)
// ============================================================================
function MockupModular() {
  const [view, setView] = useState('overview');
  const [drill, setDrill] = useState(null);
 
  const nav = [
    { group: 'GENERAL', items: [{ id: 'overview', label: 'Resumen ejecutivo', icon: Sparkles }] },
    { group: 'FINANZAS', items: [
      { id: 'finanzas', label: 'Salud financiera', icon: DollarSign },
      { id: 'flujo', label: 'Flujo & cartera', icon: Activity },
      { id: 'creditos', label: 'Créditos y deuda', icon: Layers },
    ]},
    { group: 'OPERACIÓN', items: [
      { id: 'proyectos', label: 'Proyectos', icon: Briefcase },
      { id: 'clientes', label: 'Clientes', icon: Building2 },
      { id: 'mix', label: 'Mix de servicios', icon: PieIcon },
    ]},
    { group: 'TALENTO', items: [
      { id: 'people', label: 'Headcount & nómina', icon: Users },
      { id: 'util', label: 'Utilización', icon: Target },
    ]},
    { group: 'INDUSTRIA', items: [
      { id: 'bench', label: 'Benchmarks', icon: BarChart3 },
      { id: 'pos', label: 'Posicionamiento', icon: Award },
    ]},
  ];
 
  const titles = {
    overview: ['General', 'Resumen ejecutivo'],
    finanzas: ['Finanzas', 'Salud financiera'],
    flujo: ['Finanzas', 'Flujo & cartera'],
    creditos: ['Finanzas', 'Créditos y deuda'],
    proyectos: ['Operación', 'Proyectos'],
    clientes: ['Operación', 'Clientes'],
    mix: ['Operación', 'Mix de servicios'],
    people: ['Talento', 'Headcount & nómina'],
    util: ['Talento', 'Utilización'],
    bench: ['Industria', 'Benchmarks'],
    pos: ['Industria', 'Posicionamiento'],
  };
 
  const renderContent = () => {
    if (drill?.type === 'client') return <ModularClientDrill id={drill.id} onBack={() => setDrill(null)} />;
    if (drill?.type === 'project') return <ModularProjectDrill id={drill.id} onBack={() => setDrill(null)} />;
    if (drill?.type === 'area') return <ModularAreaDrill id={drill.id} onBack={() => setDrill(null)} />;
    if (view === 'overview') return <ModOverview onDrill={setDrill} setView={setView} />;
    if (view === 'finanzas') return <ModFinance />;
    if (view === 'flujo') return <ModFlow />;
    if (view === 'creditos') return <ModCredit />;
    if (view === 'proyectos') return <ModProjects onDrill={setDrill} />;
    if (view === 'clientes') return <ModClients onDrill={setDrill} />;
    if (view === 'mix') return <ModMix />;
    if (view === 'people') return <ModPeople onDrill={setDrill} />;
    if (view === 'util') return <ModUtil />;
    if (view === 'bench') return <ModBench />;
    if (view === 'pos') return <ModPosition />;
  };
 
  const [bc1, bc2] = titles[view] || ['', ''];
 
  return (
    <div className="min-h-screen bg-slate-50 flex" style={{ fontFamily: '"Manrope",system-ui,sans-serif' }}>
      <aside className="w-64 bg-white border-r border-slate-200 flex-shrink-0">
        <div className="px-5 py-5 border-b border-slate-200">
          <div className="flex items-center gap-2.5">
            <div className="w-8 h-8 rounded-lg bg-gradient-to-br from-violet-600 to-indigo-600 flex items-center justify-center">
              <Shield className="w-4 h-4 text-white" />
            </div>
            <div>
              <div className="font-bold text-slate-900 text-[14px]">Silent4Business</div>
              <div className="text-[10px] text-slate-500">Tablero CEO</div>
            </div>
          </div>
        </div>
        <div className="p-3">
          <div className="bg-slate-100 rounded-md flex items-center gap-2 px-3 py-2 text-[12px] text-slate-500">
            <Search className="w-3.5 h-3.5" />
            <span>Buscar métrica…</span>
            <span className="ml-auto text-[10px] bg-white px-1.5 py-0.5 rounded border border-slate-200">⌘K</span>
          </div>
        </div>
        <nav className="px-3 pb-6 space-y-5">
          {nav.map((group) => (
            <div key={group.group}>
              <div className="text-[10px] font-bold uppercase tracking-[0.15em] text-slate-400 px-3 mb-1.5">{group.group}</div>
              <div className="space-y-0.5">
                {group.items.map((item) => {
                  const Icon = item.icon;
                  const active = view === item.id && !drill;
                  return (
                    <button key={item.id} onClick={() => { setView(item.id); setDrill(null); }}
                      className={`w-full flex items-center gap-2.5 px-3 py-1.5 rounded-md text-[13px] transition ${
                        active ? 'bg-violet-50 text-violet-700 font-semibold' : 'text-slate-700 hover:bg-slate-100'
                      }`}>
                      <Icon className={`w-4 h-4 ${active ? 'text-violet-600' : 'text-slate-400'}`} />
                      {item.label}
                    </button>
                  );
                })}
              </div>
            </div>
          ))}
        </nav>
      </aside>
 
      <main className="flex-1 overflow-auto">
        <header className="bg-white border-b border-slate-200 px-8 py-4 flex items-center justify-between sticky top-0 z-10">
          <div>
            <div className="flex items-center gap-2 text-[11px] text-slate-500">
              <span>{bc1}</span><ChevronRight className="w-3 h-3" /><span className="text-slate-900">{bc2}</span>
            </div>
            <h1 className="text-2xl font-bold text-slate-900 mt-0.5 tracking-tight">{bc2}</h1>
          </div>
          <div className="flex items-center gap-2">
            <button className="px-3 py-1.5 text-[12px] bg-white border border-slate-200 rounded-md text-slate-700 hover:bg-slate-50 inline-flex items-center gap-1.5">
              <Calendar className="w-3.5 h-3.5" />{company.period}<ChevronDown className="w-3 h-3" />
            </button>
            <button className="px-3 py-1.5 text-[12px] bg-violet-600 text-white rounded-md hover:bg-violet-700 inline-flex items-center gap-1.5">
              <Download className="w-3.5 h-3.5" />Exportar
            </button>
          </div>
        </header>
        <div className="p-8">{renderContent()}</div>
      </main>
    </div>
  );
}
 
// --- Modular helpers ---
const Card = ({ title, action, children, className = '' }) => (
  <div className={`bg-white rounded-xl border border-slate-200 ${className}`}>
    {(title || action) && (
      <div className="px-5 py-4 border-b border-slate-100 flex items-center justify-between">
        <div className="text-[14px] font-bold text-slate-900">{title}</div>
        {action}
      </div>
    )}
    <div className="p-5">{children}</div>
  </div>
);
 
const KPI = ({ label, value, sub, deltaVal, color = 'violet', icon: Icon }) => {
  const c = {
    violet: 'from-violet-500/10 text-violet-700 border-violet-200',
    emerald: 'from-emerald-500/10 text-emerald-700 border-emerald-200',
    blue: 'from-blue-500/10 text-blue-700 border-blue-200',
    amber: 'from-amber-500/10 text-amber-700 border-amber-200',
    rose: 'from-rose-500/10 text-rose-700 border-rose-200',
  }[color];
  return (
    <div className="bg-white rounded-xl border border-slate-200 p-5">
      <div className="flex items-start justify-between">
        {Icon && <div className={`w-9 h-9 rounded-lg bg-gradient-to-br ${c} flex items-center justify-center`}><Icon className="w-4 h-4" /></div>}
      </div>
      <div className="text-[12px] text-slate-500 mt-4">{label}</div>
      <div className="text-3xl font-bold text-slate-900 mt-1 tracking-tight tabular-nums">{value}</div>
      {(deltaVal != null || sub) && (
        <div className="flex items-center gap-2 mt-2">
          {deltaVal != null && (
            <span className={`inline-flex items-center gap-1 text-[11px] font-semibold px-1.5 py-0.5 rounded ${deltaVal >= 0 ? 'bg-emerald-50 text-emerald-700' : 'bg-red-50 text-red-700'}`}>
              {deltaVal >= 0 ? <ArrowUpRight className="w-3 h-3" /> : <ArrowDownRight className="w-3 h-3" />}
              {fmt.pctSigned(deltaVal, 1)}
            </span>
          )}
          {sub && <span className="text-[11px] text-slate-500">{sub}</span>}
        </div>
      )}
    </div>
  );
};
 
const ModBack = ({ onBack, label }) => (
  <button onClick={onBack} className="mb-5 text-[12px] text-violet-600 font-medium hover:underline inline-flex items-center gap-1">
    <ArrowLeft className="w-3.5 h-3.5" /> Volver a {label}
  </button>
);
 
// --- ModOverview ---
function ModOverview({ onDrill, setView }) {
  return (
    <div className="space-y-6">
      <div className="grid grid-cols-4 gap-4">
        <KPI label="Ingresos LTM" value="$198.4M" deltaVal={0.227} sub="vs $161.7M ant." icon={TrendingUp} color="emerald" />
        <KPI label="EBITDA" value="$41.6M" deltaVal={0.180} sub="21.0% margen" icon={Activity} color="violet" />
        <KPI label="Headcount" value={company.people.headcount} sub="74% utilización" icon={Users} color="blue" />
        <KPI label="Clientes activos" value={company.ops.activeClients} sub={`${company.ops.activeProjects} proyectos`} icon={Building2} color="amber" />
      </div>
      <div className="grid grid-cols-3 gap-4">
        <Card title="Salud financiera" action={<button onClick={() => setView('finanzas')} className="text-[11px] text-violet-600 font-medium">Ver →</button>}>
          <div className="space-y-3 text-[13px]">
            {[['Caja', '$28.4M', true], ['Cartera', '$38.2M', false], ['Línea crédito', '$32M libres', true], ['Regla 40', '43.7', true]].map(([l, v, g]) => (
              <div key={l} className="flex justify-between border-b border-slate-100 pb-2">
                <span className="text-slate-700">{l}</span>
                <span className={`font-semibold ${g ? 'text-emerald-700' : 'text-amber-700'}`}>{v}</span>
              </div>))}
          </div>
        </Card>
        <Card title="Operación" action={<button onClick={() => setView('proyectos')} className="text-[11px] text-violet-600 font-medium">Ver →</button>}>
          <div className="space-y-3 text-[13px]">
            <div className="flex justify-between"><span className="text-slate-700">Proyectos activos</span><span className="font-semibold">{company.ops.activeProjects}</span></div>
            <div className="flex justify-between"><span className="text-slate-700">En riesgo</span><span className="font-semibold text-amber-700">{company.projectsAtRisk.length}</span></div>
            <div className="flex justify-between"><span className="text-slate-700">Pipeline</span><span className="font-semibold">{fmt.mxn(company.ops.pipeline)}</span></div>
            <div className="flex justify-between"><span className="text-slate-700">SLA cumplido</span><span className="font-semibold text-emerald-700">{fmt.pct(company.ops.slaCompliance, 1)}</span></div>
          </div>
        </Card>
        <Card title="Alertas activas" action={<span className="text-[11px] text-rose-600 font-medium">3 críticas</span>}>
          <div className="space-y-2.5">
            {company.alerts.slice(0, 4).map((a) => (
              <div key={a.id} className="flex items-start gap-2.5 text-[12px]">
                <span className={`w-1.5 h-1.5 rounded-full mt-1.5 ${a.level === 'high' ? 'bg-rose-500' : a.level === 'med' ? 'bg-amber-500' : 'bg-emerald-500'}`}></span>
                <div className="flex-1">
                  <div className="text-slate-900 leading-tight">{a.msg}</div>
                  <div className="text-slate-500 text-[11px] mt-0.5">{a.area}</div>
                </div>
              </div>))}
          </div>
        </Card>
      </div>
      <Card title="Ingresos · 12 meses">
        <div className="h-72">
          <ResponsiveContainer width="100%" height="100%">
            <ComposedChart data={company.monthly}>
              <defs><linearGradient id="rev_ov" x1="0" y1="0" x2="0" y2="1">
                <stop offset="0%" stopColor="#7c3aed" stopOpacity={0.2} />
                <stop offset="100%" stopColor="#7c3aed" stopOpacity={0} />
              </linearGradient></defs>
              <CartesianGrid stroke="#f1f5f9" strokeDasharray="3 3" vertical={false} />
              <XAxis dataKey="mes" stroke="#94a3b8" tick={{ fontSize: 11 }} />
              <YAxis stroke="#94a3b8" tick={{ fontSize: 11 }} />
              <Tooltip contentStyle={{ background: 'white', border: '1px solid #e2e8f0', borderRadius: 8, fontSize: 12 }} />
              <Legend wrapperStyle={{ fontSize: 12 }} />
              <Area type="monotone" dataKey="ingresos" fill="url(#rev_ov)" stroke="#7c3aed" strokeWidth={2.5} name="Ingresos" />
              <Line type="monotone" dataKey="ebitda" stroke="#059669" strokeWidth={2.5} dot={{ r: 3 }} name="EBITDA" />
            </ComposedChart>
          </ResponsiveContainer>
        </div>
      </Card>
    </div>
  );
}
 
// --- ModFinance ---
function ModFinance() {
  return (
    <div className="space-y-6">
      <div className="grid grid-cols-4 gap-4">
        <KPI label="Ingresos LTM" value="$198.4M" deltaVal={0.227} sub="vs LTM ant." icon={TrendingUp} color="emerald" />
        <KPI label="EBITDA" value="$41.6M" deltaVal={0.180} sub="21.0% margen" icon={Activity} color="violet" />
        <KPI label="Caja + WC" value="$28.4M" deltaVal={0.120} sub="WC neto $51.8M" icon={DollarSign} color="blue" />
        <KPI label="Regla 40" value="43.7" deltaVal={0.05} sub="Top quartile" icon={Target} color="amber" />
      </div>
      <Card title="Estado de resultados LTM">
        <table className="w-full text-[13px]"><tbody>{[
          { c: 'Ingresos', v: company.finance.revenueLTM, p: 1.0, b: true },
          { c: 'Costo de servicio', v: -(company.finance.revenueLTM - company.finance.grossProfit), p: -0.480 },
          { c: 'Utilidad bruta', v: company.finance.grossProfit, p: 0.520, b: true },
          { c: 'Gastos operación', v: -(company.finance.grossProfit - company.finance.ebitdaLTM), p: -0.310 },
          { c: 'EBITDA', v: company.finance.ebitdaLTM, p: 0.210, b: true },
          { c: 'D&A + Fin + Imp', v: -(company.finance.ebitdaLTM - company.finance.netIncomeLTM), p: -0.085 },
          { c: 'Utilidad neta', v: company.finance.netIncomeLTM, p: 0.125, b: true },
        ].map((r, i) => (
          <tr key={i} className={`border-b border-slate-100 ${r.b ? 'bg-violet-50/50' : ''}`}>
            <td className={`py-2.5 ${r.b ? 'font-bold text-slate-900' : 'pl-4 text-slate-700'}`}>{r.c}</td>
            <td className={`py-2.5 text-right tabular-nums ${r.v < 0 ? 'text-red-700' : ''} ${r.b ? 'font-bold' : ''}`}>{r.v < 0 ? '−' : ''}{fmt.mxn(Math.abs(r.v))}</td>
            <td className="py-2.5 text-right tabular-nums text-slate-500 w-24">{(r.p * 100).toFixed(1)}%</td>
          </tr>))}</tbody></table>
      </Card>
    </div>
  );
}
 
// --- ModFlow ---
function ModFlow() {
  return (
    <div className="space-y-6">
      <div className="grid grid-cols-4 gap-4">
        <KPI label="Cartera total" value="$38.2M" sub="DSO 58 días" icon={DollarSign} color="amber" />
        <KPI label="Vencido +30d" value="$8.9M" sub="23% del total" icon={AlertCircle} color="rose" />
        <KPI label="Cobranza mes" value="$20.8M" deltaVal={0.035} icon={TrendingUp} color="emerald" />
        <KPI label="Caja disponible" value="$28.4M" sub="3.4 meses cubiertos" icon={Layers} color="blue" />
      </div>
      <div className="grid grid-cols-2 gap-4">
        <Card title="Aging de cartera">
          <div className="space-y-3">{[
            ['Al corriente', 29_300_000, '#10b981'],
            ['Vencido 30-60d', 4_900_000, '#f59e0b'],
            ['Vencido 60-90d', 2_800_000, '#fb923c'],
            ['Vencido +90d', 1_200_000, '#dc2626'],
          ].map(([l, v, c]) => (
            <div key={l}>
              <div className="flex justify-between text-[13px] mb-1">
                <span className="text-slate-700 flex items-center gap-2"><span className="w-2 h-2 rounded-full" style={{ background: c }}></span>{l}</span>
                <span className="font-semibold tabular-nums">{fmt.mxn(v)}</span>
              </div>
              <div className="h-1.5 bg-slate-100 rounded-full overflow-hidden">
                <div className="h-full" style={{ width: ((v / 38_200_000) * 100) + '%', background: c }}></div>
              </div>
            </div>))}
          </div>
        </Card>
        <Card title="Cobranza vs Costo · 12 meses">
          <div className="h-56">
            <ResponsiveContainer width="100%" height="100%">
              <BarChart data={company.monthly}>
                <CartesianGrid stroke="#f1f5f9" strokeDasharray="3 3" vertical={false} />
                <XAxis dataKey="mes" stroke="#94a3b8" tick={{ fontSize: 10 }} />
                <YAxis stroke="#94a3b8" tick={{ fontSize: 10 }} />
                <Tooltip />
                <Bar dataKey="cobranza" fill="#10b981" name="Cobranza" />
                <Bar dataKey="costoOp" fill="#f59e0b" name="Costo Op" opacity={0.7} />
              </BarChart>
            </ResponsiveContainer>
          </div>
        </Card>
      </div>
      <Card title="DSO por vertical">
        <div className="space-y-3">{company.verticals.map((v) => (
          <div key={v.name} className="flex items-center gap-3">
            <span className="text-[13px] text-slate-700 w-32">{v.name}</span>
            <div className="flex-1 h-2 bg-slate-100 rounded-full">
              <div className={`h-full rounded-full ${v.dso > 70 ? 'bg-rose-500' : v.dso > 50 ? 'bg-amber-500' : 'bg-emerald-500'}`} style={{ width: ((v.dso / 100) * 100) + '%' }}></div>
            </div>
            <span className={`text-[13px] font-semibold w-16 text-right tabular-nums ${v.dso > 70 ? 'text-rose-700' : 'text-slate-900'}`}>{v.dso}d</span>
          </div>))}
        </div>
      </Card>
    </div>
  );
}
 
// --- ModCredit ---
function ModCredit() {
  return (
    <div className="space-y-6">
      <div className="grid grid-cols-3 gap-4">
        <KPI label="Línea total" value="$50.0M" sub="36% utilizada" icon={Layers} color="violet" />
        <KPI label="Disponible" value="$32.0M" sub="Holgura operativa" icon={CheckCircle2} color="emerald" />
        <KPI label="Deuda/EBITDA" value="0.43x" sub="Saludable (≤2.0x)" icon={Target} color="emerald" />
      </div>
      <Card title="Línea revolvente">
        <div className="relative h-4 bg-slate-100 rounded-full overflow-hidden mb-4">
          <div className="absolute left-0 top-0 h-full bg-violet-600 rounded-full" style={{ width: '36%' }}></div>
        </div>
        <div className="grid grid-cols-4 gap-6 mt-6">
          {[['Tasa promedio', '14.2%'], ['Plazo promedio', '90 días'], ['Banco principal', 'Santander'], ['Próximo pago', '$3.2M · 28 nov']].map(([l, v]) => (
            <div key={l}>
              <div className="text-[10px] uppercase tracking-wider text-slate-500">{l}</div>
              <div className="text-base font-bold mt-0.5">{v}</div>
            </div>))}
        </div>
      </Card>
      <Card title="Ratios financieros">
        <div className="grid grid-cols-4 gap-6">
          {[['Quick Ratio', '1.84x', 'OK ≥ 1.0'], ['Current Ratio', '2.31x', 'OK ≥ 1.5'], ['DSCR', '3.84x', 'Holgado'], ['Interest Cov.', '12.4x', 'Holgado']].map(([l, v, g]) => (
            <div key={l} className="border-l-2 border-emerald-500 pl-4 py-1">
              <div className="text-[11px] uppercase tracking-wider text-slate-500">{l}</div>
              <div className="text-2xl font-bold mt-0.5">{v}</div>
              <div className="text-[11px] text-emerald-700 mt-0.5">{g}</div>
            </div>))}
        </div>
      </Card>
    </div>
  );
}
 
// --- ModProjects ---
function ModProjects({ onDrill }) {
  return (
    <div className="space-y-6">
      <div className="grid grid-cols-4 gap-4">
        <KPI label="Activos" value={company.ops.activeProjects} icon={Briefcase} color="violet" />
        <KPI label="En riesgo" value={company.projectsAtRisk.length} sub="13% del total" icon={AlertCircle} color="amber" />
        <KPI label="Backlog" value={fmt.mxn(company.ops.backlog)} icon={Layers} color="blue" />
        <KPI label="Margen prom" value={fmt.pct(company.ops.avgProjectMargin)} icon={Target} color="emerald" />
      </div>
      <Card title="Proyectos en riesgo · click para detalle">
        <table className="w-full text-[13px]">
          <thead className="border-b border-slate-200">
            <tr className="text-[10px] uppercase tracking-wider text-slate-500">
              <th className="text-left py-2 font-semibold">Proyecto</th>
              <th className="text-left py-2 font-semibold">Cliente</th>
              <th className="text-left py-2 font-semibold">Riesgo</th>
              <th className="text-right py-2 font-semibold">Valor</th>
              <th className="text-right py-2 font-semibold">Margen</th>
              <th className="text-right py-2 font-semibold">% Avance</th>
            </tr>
          </thead>
          <tbody>{company.projectsAtRisk.map((p) => (
            <tr key={p.id} onClick={() => onDrill({ type: 'project', id: p.id })} className="border-b border-slate-100 hover:bg-slate-50 cursor-pointer">
              <td className="py-3 font-medium text-slate-900">{p.name}</td>
              <td className="py-3 text-slate-600">{p.client}</td>
              <td className="py-3"><span className="text-[11px] bg-amber-50 text-amber-700 px-2 py-0.5 rounded-full">{p.type}</span></td>
              <td className="py-3 text-right tabular-nums">{fmt.mxn(p.value)}</td>
              <td className={`py-3 text-right tabular-nums font-semibold ${p.currentMargin < 0.15 ? 'text-rose-700' : 'text-amber-700'}`}>{fmt.pct(p.currentMargin)}</td>
              <td className="py-3 text-right">
                <div className="inline-flex items-center gap-2">
                  <div className="w-16 h-1.5 bg-slate-100 rounded-full"><div className="h-full bg-violet-500 rounded-full" style={{ width: fmt.pct(p.completion, 0) }}></div></div>
                  <span className="text-slate-700 tabular-nums">{fmt.pct(p.completion, 0)}</span>
                </div>
              </td>
            </tr>))}</tbody>
        </table>
      </Card>
    </div>
  );
}
 
// --- ModClients ---
function ModClients({ onDrill }) {
  return (
    <div className="space-y-6">
      <div className="grid grid-cols-4 gap-4">
        <KPI label="Clientes activos" value={company.ops.activeClients} icon={Building2} color="violet" />
        <KPI label="Top 8 = % rev" value="67%" sub="concentración" icon={PieIcon} color="amber" />
        <KPI label="Nuevos Q3" value={company.ops.newClientsQ} icon={Plus} color="emerald" />
        <KPI label="NPS" value={company.ops.nps} sub="meta: 60" icon={Target} color="blue" />
      </div>
      <Card title="Clientes activos · click para perfil completo">
        <table className="w-full text-[13px]">
          <thead className="border-b border-slate-200">
            <tr className="text-[10px] uppercase tracking-wider text-slate-500">
              <th className="text-left py-2 font-semibold">Cliente</th>
              <th className="text-left py-2 font-semibold">Vertical</th>
              <th className="text-right py-2 font-semibold">Revenue LTM</th>
              <th className="text-right py-2 font-semibold">Margen</th>
              <th className="text-right py-2 font-semibold">Proyectos</th>
              <th className="text-right py-2 font-semibold">Renovación</th>
              <th className="text-center py-2 font-semibold">Estado</th>
            </tr>
          </thead>
          <tbody>{company.topClients.map((c) => (
            <tr key={c.id} onClick={() => onDrill({ type: 'client', id: c.id })} className="border-b border-slate-100 hover:bg-slate-50 cursor-pointer">
              <td className="py-3 font-medium">{c.name}</td>
              <td className="py-3 text-slate-600">{c.vertical}</td>
              <td className="py-3 text-right tabular-nums font-semibold">{fmt.mxn(c.revenue)}</td>
              <td className={`py-3 text-right tabular-nums ${c.margin >= 0.25 ? 'text-emerald-700' : c.margin >= 0.20 ? 'text-slate-700' : 'text-rose-700'}`}>{fmt.pct(c.margin)}</td>
              <td className="py-3 text-right tabular-nums">{c.projects}</td>
              <td className="py-3 text-right tabular-nums text-slate-500 text-[12px]">{c.renewal}</td>
              <td className="py-3 text-center">
                <span className={`inline-flex items-center gap-1 text-[11px] font-medium px-2 py-0.5 rounded-full ${c.status === 'green' ? 'bg-emerald-50 text-emerald-700' : c.status === 'amber' ? 'bg-amber-50 text-amber-700' : 'bg-rose-50 text-rose-700'}`}>
                  <span className={`w-1.5 h-1.5 rounded-full ${c.status === 'green' ? 'bg-emerald-500' : c.status === 'amber' ? 'bg-amber-500' : 'bg-rose-500'}`}></span>
                  {c.status === 'green' ? 'Saludable' : c.status === 'amber' ? 'Atención' : 'Riesgo'}
                </span>
              </td>
            </tr>))}</tbody>
        </table>
      </Card>
    </div>
  );
}
 
// --- ModMix ---
function ModMix() {
  return (
    <div className="space-y-6">
      <div className="grid grid-cols-2 gap-6">
        <Card title="Ingresos por línea de servicio">
          <div className="h-64">
            <ResponsiveContainer width="100%" height="100%">
              <PieChart>
                <Pie data={company.segments} dataKey="revenue" nameKey="name" innerRadius={60} outerRadius={100} paddingAngle={2}>
                  {company.segments.map((s) => <Cell key={s.id} fill={s.color} />)}
                </Pie>
                <Tooltip />
              </PieChart>
            </ResponsiveContainer>
          </div>
          <div className="space-y-1.5 mt-3">{company.segments.map((s) => (
            <div key={s.id} className="flex items-center gap-2 text-[12px]">
              <span className="w-2 h-2 rounded-full" style={{ background: s.color }}></span>
              <span className="text-slate-700 flex-1">{s.name}</span>
              <span className="font-semibold tabular-nums">{fmt.mxn(s.revenue)}</span>
              <span className="text-slate-500 w-12 text-right tabular-nums">{fmt.pct(s.share, 0)}</span>
            </div>))}
          </div>
        </Card>
        <Card title="Ingresos por vertical">
          <div className="h-64">
            <ResponsiveContainer width="100%" height="100%">
              <BarChart data={company.verticals} layout="vertical">
                <CartesianGrid stroke="#f1f5f9" strokeDasharray="3 3" />
                <XAxis type="number" stroke="#94a3b8" tick={{ fontSize: 11 }} />
                <YAxis dataKey="name" type="category" stroke="#94a3b8" tick={{ fontSize: 11 }} width={90} />
                <Tooltip />
                <Bar dataKey="revenue" fill="#7c3aed" />
              </BarChart>
            </ResponsiveContainer>
          </div>
        </Card>
      </div>
      <Card title="Línea de servicio · detalle">
        <table className="w-full text-[13px]">
          <thead className="border-b border-slate-200">
            <tr className="text-[10px] uppercase tracking-wider text-slate-500">
              <th className="text-left py-2 font-semibold">Línea</th>
              <th className="text-right py-2 font-semibold">Revenue LTM</th>
              <th className="text-right py-2 font-semibold">% Total</th>
              <th className="text-right py-2 font-semibold">Margen</th>
              <th className="text-right py-2 font-semibold">YoY</th>
              <th className="text-right py-2 font-semibold">MRR</th>
              <th className="text-right py-2 font-semibold">Clientes</th>
            </tr>
          </thead>
          <tbody>{company.segments.map((s) => (
            <tr key={s.id} className="border-b border-slate-100">
              <td className="py-3"><span className="inline-flex items-center gap-2"><span className="w-2.5 h-2.5 rounded" style={{ background: s.color }}></span>{s.name}</span></td>
              <td className="py-3 text-right tabular-nums font-semibold">{fmt.mxn(s.revenue)}</td>
              <td className="py-3 text-right tabular-nums">{fmt.pct(s.share, 0)}</td>
              <td className="py-3 text-right tabular-nums">{fmt.pct(s.margin)}</td>
              <td className={`py-3 text-right tabular-nums font-semibold ${s.growth >= 0.15 ? 'text-emerald-700' : s.growth >= 0 ? 'text-slate-700' : 'text-rose-700'}`}>{fmt.pctSigned(s.growth)}</td>
              <td className="py-3 text-right tabular-nums">{s.mrr ? fmt.mxn(s.mrr) : '—'}</td>
              <td className="py-3 text-right tabular-nums">{s.clients}</td>
            </tr>))}</tbody>
        </table>
      </Card>
    </div>
  );
}
 
// --- ModPeople ---
function ModPeople({ onDrill }) {
  return (
    <div className="space-y-6">
      <div className="grid grid-cols-4 gap-4">
        <KPI label="Headcount" value={company.people.headcount} sub="+8 YoY" icon={Users} color="violet" />
        <KPI label="Nómina/mes" value={fmt.mxn(company.people.payrollMonthly)} sub="56% ingresos" icon={DollarSign} color="amber" />
        <KPI label="Attrition 12m" value={fmt.pct(company.people.attrition12m)} sub="SOC 24%" icon={TrendingDown} color="rose" />
        <KPI label="Antigüedad prom" value={`${company.people.avgTenure} años`} icon={Clock} color="blue" />
      </div>
      <Card title="Áreas · click para detalle">
        <table className="w-full text-[13px]">
          <thead className="border-b border-slate-200">
            <tr className="text-[10px] uppercase tracking-wider text-slate-500">
              <th className="text-left py-2 font-semibold">Área</th>
              <th className="text-left py-2 font-semibold">Líder</th>
              <th className="text-right py-2 font-semibold">HC</th>
              <th className="text-right py-2 font-semibold">Nómina/mes</th>
              <th className="text-right py-2 font-semibold">Salario prom</th>
              <th className="text-right py-2 font-semibold">Attrition</th>
              <th className="text-center py-2 font-semibold">Tipo</th>
            </tr>
          </thead>
          <tbody>{company.areas.map((a) => (
            <tr key={a.id} onClick={() => onDrill({ type: 'area', id: a.id })} className="border-b border-slate-100 hover:bg-slate-50 cursor-pointer">
              <td className="py-3 font-medium">{a.name}</td>
              <td className="py-3 text-slate-600 text-[12px]">{a.leader}</td>
              <td className="py-3 text-right tabular-nums">{a.headcount}</td>
              <td className="py-3 text-right tabular-nums">{fmt.mxn(a.payroll)}</td>
              <td className="py-3 text-right tabular-nums">{fmt.mxnK(a.avgSalary)}</td>
              <td className={`py-3 text-right tabular-nums ${a.attrition > 0.20 ? 'text-amber-700 font-semibold' : 'text-slate-700'}`}>{fmt.pct(a.attrition)}</td>
              <td className="py-3 text-center">
                <span className={`text-[11px] px-2 py-0.5 rounded-full ${a.billable ? 'bg-emerald-50 text-emerald-700' : 'bg-slate-100 text-slate-600'}`}>
                  {a.billable ? 'Facturable' : 'Soporte'}
                </span>
              </td>
            </tr>))}</tbody>
        </table>
      </Card>
    </div>
  );
}
 
// --- ModUtil ---
function ModUtil() {
  const billable = company.areas.filter((a) => a.billable);
  return (
    <div className="space-y-6">
      <div className="grid grid-cols-4 gap-4">
        <KPI label="Utilización global" value={fmt.pct(company.people.utilizationRate)} sub="meta 78%" icon={Target} color="violet" />
        <KPI label="Bench" value={company.people.benchHeadcount} sub="personas no asignadas" icon={Clock} color="amber" />
        <KPI label="Rev/Empleado" value={fmt.mxn(company.people.revenuePerEmployee)} sub="vs sector $1.85M" icon={DollarSign} color="blue" />
        <KPI label="Brecha vs Top Q" value="-8pp" sub="$144K/pp = $1.15M" icon={Flame} color="rose" />
      </div>
      <Card title="Utilización por área facturable">
        <div className="space-y-4">{billable.map((a) => (
          <div key={a.id}>
            <div className="flex justify-between text-[13px] mb-1.5">
              <span className="font-medium text-slate-900">{a.name}</span>
              <span className={a.utilization >= 0.78 ? 'text-emerald-700 font-semibold' : 'text-amber-700 font-semibold'}>{fmt.pct(a.utilization, 0)}</span>
            </div>
            <div className="relative h-3 bg-slate-100 rounded-full">
              <div className={`h-full rounded-full ${a.utilization >= 0.78 ? 'bg-emerald-500' : 'bg-amber-500'}`} style={{ width: ((a.utilization / 0.95) * 100) + '%' }}></div>
              <div className="absolute top-0 h-full w-px bg-violet-700" style={{ left: ((0.78 / 0.95) * 100) + '%' }}></div>
            </div>
          </div>))}
        </div>
        <div className="mt-5 pt-4 border-t border-slate-100 text-[12px] text-slate-600">
          La línea morada marca el target de 78%. Cada punto porcentual de utilización adicional ≈ $144K MXN/mes de revenue.
        </div>
      </Card>
    </div>
  );
}
 
// --- ModBench ---
function ModBench() {
  return (
    <div className="space-y-6">
      <Card title="Industry Scorecard · 42 MSPs LATAM" action={<span className="text-[11px] text-slate-500">$50M-$500M revenue</span>}>
        <div className="space-y-3">{company.benchmarks.map((b) => {
          const d = delta(b.s4b, b.industry, b.higherBetter);
          const dTop = delta(b.s4b, b.topQ, b.higherBetter);
          const tier = dTop.good ? { l: 'Top Q', c: 'bg-emerald-50 text-emerald-700' } :
                       d.good ? { l: 'Sobre Med', c: 'bg-blue-50 text-blue-700' } :
                                { l: 'Bajo Med', c: 'bg-amber-50 text-amber-700' };
          return (
            <div key={b.id} className="grid grid-cols-12 gap-3 items-center py-3 border-b border-slate-100 last:border-0">
              <div className="col-span-3 text-[13px] font-medium text-slate-900">{b.metric}</div>
              <div className="col-span-2 text-right tabular-nums font-bold">{formatBenchValue(b.s4b, b.format)}</div>
              <div className="col-span-2 text-right tabular-nums text-slate-500 text-[12px]">{formatBenchValue(b.industry, b.format)}</div>
              <div className="col-span-2 text-right tabular-nums text-amber-700 text-[12px]">{formatBenchValue(b.topQ, b.format)}</div>
              <div className="col-span-3 flex items-center justify-end">
                <span className={`text-[11px] font-medium px-2 py-1 rounded-full ${tier.c}`}>{tier.l}</span>
              </div>
            </div>);
        })}</div>
      </Card>
    </div>
  );
}
 
// --- ModPosition ---
function ModPosition() {
  return (
    <div className="space-y-6">
      <div className="grid grid-cols-3 gap-4">
        <KPI label="Mejor que" value="68%" sub="de pares LATAM" icon={Award} color="emerald" />
        <KPI label="Áreas Top Q" value="3 / 9" sub="métricas" icon={Target} color="violet" />
        <KPI label="Brecha mayor" value="DSO" sub="vs Top Q" icon={Flame} color="amber" />
      </div>
      <div className="grid grid-cols-3 gap-4">
        <Card title="Donde lideras" className="border-emerald-200">
          <div className="text-[10px] uppercase tracking-wider text-emerald-700 mb-2">Regla 40 = 43.7</div>
          <p className="text-[13px] text-slate-700 leading-relaxed">
            Solo 27% de MSPs combinan crecimiento &gt;20% con margen EBITDA &gt;18%.
            <strong className="text-emerald-700"> Esta es tu narrativa para una eventual ronda o adquisición.</strong>
          </p>
        </Card>
        <Card title="Donde estás bien" className="border-blue-200">
          <div className="text-[10px] uppercase tracking-wider text-blue-700 mb-2">Attrition 18% vs 22%</div>
          <p className="text-[13px] text-slate-700 leading-relaxed">
            Mejor retención que el sector promedio, pero el SOC cierra en 24%.
            Llegar a Top Q (12%) requiere ataque al banding salarial del SOC senior.
          </p>
        </Card>
        <Card title="Donde apretar" className="border-amber-200">
          <div className="text-[10px] uppercase tracking-wider text-amber-700 mb-2">DSO 58d vs Top Q 45d</div>
          <p className="text-[13px] text-slate-700 leading-relaxed">
            Cerrar la brecha de 13 días libera ~$8.6M de capital de trabajo permanente.
            <strong className="text-amber-700"> Mix más diverso reduce DSO estructuralmente.</strong>
          </p>
        </Card>
      </div>
    </div>
  );
}
 
// --- Modular DRILLS ---
function ModularClientDrill({ id, onBack }) {
  const c = company.topClients.find((x) => x.id === id) || company.topClients[0];
  const hist = company.clientHistory[id] || company.clientHistory.bbva;
  const histData = hist.months.map((m, i) => ({ mes: m, ingresos: hist.revenue[i], margen: hist.margin[i] * 100 }));
  return (
    <div className="space-y-6">
      <ModBack onBack={onBack} label="Clientes" />
      <div className="bg-white rounded-xl border border-slate-200 p-7">
        <div className="flex items-start justify-between">
          <div>
            <div className="flex items-center gap-3">
              <div className="w-12 h-12 rounded-xl bg-gradient-to-br from-violet-500 to-indigo-600 flex items-center justify-center"><Building2 className="w-6 h-6 text-white" /></div>
              <div>
                <h2 className="text-3xl font-bold text-slate-900 tracking-tight">{c.name}</h2>
                <div className="text-slate-500 text-[13px] mt-1">{c.vertical} · cliente desde hace {c.tenure} años</div>
              </div>
            </div>
          </div>
          <span className={`inline-flex items-center gap-1 text-[12px] font-medium px-3 py-1 rounded-full ${c.status === 'green' ? 'bg-emerald-50 text-emerald-700' : c.status === 'amber' ? 'bg-amber-50 text-amber-700' : 'bg-rose-50 text-rose-700'}`}>
            <span className={`w-2 h-2 rounded-full ${c.status === 'green' ? 'bg-emerald-500' : c.status === 'amber' ? 'bg-amber-500' : 'bg-rose-500'}`}></span>
            {c.status === 'green' ? 'Saludable' : c.status === 'amber' ? 'Atención' : 'Riesgo'}
          </span>
        </div>
      </div>
 
      <div className="grid grid-cols-4 gap-4">
        <KPI label="Revenue LTM" value={fmt.mxn(c.revenue)} sub={((c.revenue / company.finance.revenueLTM) * 100).toFixed(1) + '% del total'} icon={DollarSign} color="emerald" />
        <KPI label="Margen" value={fmt.pct(c.margin)} sub={c.margin >= 0.25 ? 'Saludable' : c.margin >= 0.20 ? 'Atención' : 'Bajo target'} icon={Target} color={c.margin >= 0.25 ? 'emerald' : 'amber'} />
        <KPI label="Proyectos activos" value={c.projects} icon={Briefcase} color="violet" />
        <KPI label="DSO" value={c.dso + 'd'} sub={c.dso > 70 ? 'Vencido' : 'Al corriente'} icon={Clock} color={c.dso > 70 ? 'amber' : 'emerald'} />
      </div>
 
      <div className="grid grid-cols-3 gap-4">
        <Card title="Datos de contacto" className="col-span-1">
          <div className="space-y-3 text-[13px]">
            <div><div className="text-[10px] uppercase tracking-wider text-slate-500">Contacto</div><div className="font-medium mt-0.5">{c.contact}</div></div>
            <div><div className="text-[10px] uppercase tracking-wider text-slate-500">Renovación</div><div className="font-medium mt-0.5">{c.renewal}</div></div>
            <div className="pt-3 border-t border-slate-100">
              <div className="text-[10px] uppercase tracking-wider text-slate-500 mb-2">Servicios contratados</div>
              {c.services.map((s) => (
                <div key={s} className="text-[13px] py-1 flex items-center gap-2">
                  <CheckCircle2 className="w-3.5 h-3.5 text-emerald-600" />{s}
                </div>))}
            </div>
          </div>
        </Card>
        <Card title="Trayectoria 6 meses" className="col-span-2">
          <div className="h-56">
            <ResponsiveContainer width="100%" height="100%">
              <ComposedChart data={histData}>
                <CartesianGrid stroke="#f1f5f9" strokeDasharray="3 3" />
                <XAxis dataKey="mes" stroke="#94a3b8" tick={{ fontSize: 11 }} />
                <YAxis yAxisId="left" stroke="#94a3b8" tick={{ fontSize: 11 }} />
                <YAxis yAxisId="right" orientation="right" stroke="#94a3b8" tick={{ fontSize: 11 }} />
                <Tooltip />
                <Bar yAxisId="left" dataKey="ingresos" fill="#7c3aed" name="Ingresos MXN M" />
                <Line yAxisId="right" type="monotone" dataKey="margen" stroke="#f59e0b" strokeWidth={2.5} name="Margen %" dot={{ r: 4 }} />
              </ComposedChart>
            </ResponsiveContainer>
          </div>
        </Card>
      </div>
 
      <Card title="Acciones recomendadas">
        <div className="space-y-2.5">
          <div className="flex items-start gap-3 text-[13px]"><span className="w-5 h-5 rounded-full bg-violet-100 text-violet-700 text-[11px] font-bold flex items-center justify-center mt-0.5">1</span><span>Confirmar fecha de renovación con {c.contact} antes del 15 Nov</span></div>
          {c.margin < 0.25 && <div className="flex items-start gap-3 text-[13px]"><span className="w-5 h-5 rounded-full bg-amber-100 text-amber-700 text-[11px] font-bold flex items-center justify-center mt-0.5">2</span><span className="text-slate-800">Margen bajo target — revisar bandas de uso en próxima renovación</span></div>}
          {c.dso > 70 && <div className="flex items-start gap-3 text-[13px]"><span className="w-5 h-5 rounded-full bg-rose-100 text-rose-700 text-[11px] font-bold flex items-center justify-center mt-0.5">3</span><span className="text-slate-800">Cartera vencida — gestión de Paco Bernal en proceso</span></div>}
          <div className="flex items-start gap-3 text-[13px]"><span className="w-5 h-5 rounded-full bg-emerald-100 text-emerald-700 text-[11px] font-bold flex items-center justify-center mt-0.5">+</span><span>Cross-sell: oportunidad GRC ISO 27001 (~$2.4M estimado)</span></div>
        </div>
      </Card>
    </div>
  );
}
 
function ModularProjectDrill({ id, onBack }) {
  const p = company.projectsAtRisk.find((x) => x.id === id) || company.projectsAtRisk[0];
  return (
    <div className="space-y-6">
      <ModBack onBack={onBack} label="Proyectos" />
      <div className="bg-white rounded-xl border border-slate-200 p-7">
        <div className="flex items-start gap-3">
          <div className="w-12 h-12 rounded-xl bg-gradient-to-br from-amber-500 to-orange-600 flex items-center justify-center"><AlertCircle className="w-6 h-6 text-white" /></div>
          <div className="flex-1">
            <h2 className="text-2xl font-bold text-slate-900 tracking-tight">{p.name}</h2>
            <div className="text-slate-500 text-[13px] mt-1">{p.client} · responsable: {p.owner}</div>
            <span className="mt-3 inline-block text-[11px] bg-amber-50 text-amber-700 px-2 py-0.5 rounded-full font-medium">{p.type}</span>
          </div>
        </div>
      </div>
 
      <div className="grid grid-cols-4 gap-4">
        <KPI label="Valor contrato" value={fmt.mxn(p.value)} icon={DollarSign} color="violet" />
        <KPI label="Avance" value={fmt.pct(p.completion, 0)} icon={Activity} color="blue" />
        <KPI label="Margen actual" value={fmt.pct(p.currentMargin)} sub={p.currentMargin < 0.15 ? 'Crítico' : 'Bajo target'} icon={Target} color={p.currentMargin < 0.15 ? 'rose' : 'amber'} />
        {p.overrun ? <KPI label="Sobrecosto" value={fmt.pct(p.overrun)} sub="vs presupuesto inicial" icon={Flame} color="rose" /> : <KPI label="Owner" value={p.owner.split(' ')[0]} sub={p.owner} icon={Users} color="blue" />}
      </div>
 
      <Card title="Diagnóstico">
        <div className="border-l-4 border-amber-500 pl-4 py-2">
          <div className="text-[11px] uppercase tracking-wider text-amber-700 mb-1">Tipo de riesgo</div>
          <div className="text-[15px] text-slate-900 font-medium">{p.type}</div>
        </div>
        {p.overrun && (
          <div className="border-l-4 border-rose-500 pl-4 py-2 mt-3">
            <div className="text-[11px] uppercase tracking-wider text-rose-700 mb-1">Sobrecosto en horas hombre</div>
            <div className="text-[14px] text-slate-700">
              {fmt.pct(p.overrun)} sobre presupuesto inicial · pérdida estimada ${(p.value * p.overrun / 1_000_000).toFixed(1)}M MXN
            </div>
          </div>
        )}
      </Card>
 
      <Card title="Plan de acción">
        <div className="space-y-3">
          {[
            ['Convocar reunión de scope review con cliente esta semana', `${p.owner} · 12 Nov 2026`],
            ['Evaluar Change Order vs absorber pérdida controlada', 'Layla Delgadillo · 18 Nov 2026'],
            ['Re-estimar presupuesto restante con buffer 15%', 'PM + Finanzas · 22 Nov 2026'],
          ].map(([t, o], i) => (
            <div key={i} className="flex items-start gap-3 pb-3 border-b border-slate-100 last:border-0">
              <span className="w-7 h-7 rounded-full bg-violet-100 text-violet-700 text-[13px] font-bold flex items-center justify-center flex-shrink-0">{i + 1}</span>
              <div>
                <div className="text-[13px] text-slate-900">{t}</div>
                <div className="text-[11px] text-slate-500 mt-1">Owner: {o}</div>
              </div>
            </div>))}
        </div>
      </Card>
    </div>
  );
}
 
function ModularAreaDrill({ id, onBack }) {
  const a = company.areas.find((x) => x.id === id) || company.areas[0];
  return (
    <div className="space-y-6">
      <ModBack onBack={onBack} label="Headcount & nómina" />
      <div className="bg-white rounded-xl border border-slate-200 p-7">
        <div className="flex items-start justify-between">
          <div className="flex items-start gap-3">
            <div className="w-12 h-12 rounded-xl bg-gradient-to-br from-violet-500 to-indigo-600 flex items-center justify-center"><Users className="w-6 h-6 text-white" /></div>
            <div>
              <h2 className="text-3xl font-bold text-slate-900 tracking-tight">{a.name}</h2>
              <div className="text-slate-500 text-[13px] mt-1">Líder: {a.leader}</div>
            </div>
          </div>
          <span className={`text-[11px] px-3 py-1 rounded-full font-medium ${a.billable ? 'bg-emerald-50 text-emerald-700' : 'bg-slate-100 text-slate-700'}`}>
            {a.billable ? 'Área facturable' : 'Área de soporte'}
          </span>
        </div>
      </div>
 
      <div className="grid grid-cols-5 gap-4">
        <KPI label="Headcount" value={a.headcount} icon={Users} color="violet" />
        <KPI label="Nómina/mes" value={fmt.mxn(a.payroll)} icon={DollarSign} color="amber" />
        <KPI label="Salario prom" value={fmt.mxnK(a.avgSalary)} icon={DollarSign} color="blue" />
        <KPI label="Utilización" value={a.utilization ? fmt.pct(a.utilization, 0) : '—'} sub={a.billable ? 'meta 78%' : 'no aplica'} icon={Target} color={a.utilization >= 0.78 ? 'emerald' : 'amber'} />
        <KPI label="Attrition" value={fmt.pct(a.attrition)} icon={TrendingDown} color={a.attrition > 0.20 ? 'rose' : 'emerald'} />
      </div>
 
      {a.billable && (
        <Card title="Utilización vs target">
          <div className="flex items-center gap-4 mb-3">
            <span className="text-[13px] text-slate-700 w-32">Actual: {fmt.pct(a.utilization)}</span>
            <div className="flex-1 relative h-4 bg-slate-100 rounded-full">
              <div className={`h-full rounded-full ${a.utilization >= 0.78 ? 'bg-emerald-500' : 'bg-amber-500'}`} style={{ width: ((a.utilization / 0.95) * 100) + '%' }}></div>
              <div className="absolute top-0 h-full w-px bg-violet-700" style={{ left: ((0.78 / 0.95) * 100) + '%' }}></div>
            </div>
            <span className="text-[12px] text-slate-500 w-20">target 78%</span>
          </div>
          <div className="text-[12px] text-slate-600 mt-3 pt-3 border-t border-slate-100">
            Cada punto porcentual ≈ ~$144K MXN de revenue adicional. {a.utilization >= 0.78 ? 'Cumpliendo target.' : `Brecha de ${((0.78 - a.utilization) * 100).toFixed(1)}pp · oportunidad ~$${(((0.78 - a.utilization) * 144) * a.headcount / 38).toFixed(0)}K MXN/mes.`}
          </div>
        </Card>
      )}
 
      <Card title="% de nómina total">
        <div className="flex items-center gap-3">
          <div className="flex-1 h-3 bg-slate-100 rounded-full">
            <div className="h-full bg-violet-500 rounded-full" style={{ width: ((a.payroll / company.people.payrollMonthly) * 100) + '%' }}></div>
          </div>
          <span className="text-[14px] font-bold tabular-nums w-16 text-right">{fmt.pct(a.payroll / company.people.payrollMonthly, 0)}</span>
        </div>
      </Card>
    </div>
  );
}
 
// ============================================================================
// PLACEHOLDERS
// ============================================================================
function MockupPlaceholder({ name, tagline }) {
  return (
    <div className="min-h-screen bg-slate-50 flex items-center justify-center" style={{ fontFamily: 'Manrope, system-ui, sans-serif' }}>
      <div className="max-w-md text-center px-6">
        <div className="w-16 h-16 bg-violet-100 rounded-2xl flex items-center justify-center mx-auto mb-6">
          <Sparkles className="w-8 h-8 text-violet-600" />
        </div>
        <h2 className="text-3xl font-bold text-slate-900 tracking-tight">{name}</h2>
        <p className="text-slate-600 mt-3">{tagline}</p>
        <div className="mt-8 px-5 py-4 bg-white border border-slate-200 rounded-xl text-left">
          <div className="text-[11px] uppercase tracking-wider text-slate-500 font-semibold">Próximamente</div>
          <div className="text-sm text-slate-700 mt-2">
            Este mockup se construye en el siguiente paso. Mientras tanto, navega <strong>Command Center</strong> o <strong>Modular SaaS</strong> — ya están completos.
          </div>
        </div>
      </div>
    </div>
  );
}
 
// ============================================================================
// APP
// ============================================================================
const MOCKUPS = [
  { id: 'terminal', name: '01 · Command Center', tagline: 'Bloomberg-style. Denso, dark, todo a la vista.', desc: '6 secciones + drill-downs.', component: MockupTerminal, ready: true },
  { id: 'editorial', name: '02 · Editorial Brief', tagline: 'Magazine-style. Cuenta una historia.', desc: 'Próximo paso.', component: () => <MockupPlaceholder name="Editorial Brief" tagline="Próximo a construir." />, ready: false },
  { id: 'modular', name: '03 · Modular SaaS', tagline: 'Notion/Linear-style. Para uso diario.', desc: '11 vistas + drill-downs.', component: MockupModular, ready: true },
  { id: 'benchmark', name: '04 · Industry Scorecard', tagline: 'Comparativo vs sector LATAM.', desc: 'Próximo paso.', component: () => <MockupPlaceholder name="Industry Scorecard" tagline="Próximo a construir." />, ready: false },
];
 
export default function App() {
  const [active, setActive] = useState('modular');
  const [showSelector, setShowSelector] = useState(true);
  const Active = MOCKUPS.find((m) => m.id === active).component;
 
  return (
    <div className="relative">
      <style>{`
        @import url('https://fonts.googleapis.com/css2?family=JetBrains+Mono:wght@400;500;700&family=IBM+Plex+Mono:wght@400;500&family=Manrope:wght@400;500;600;700;800&display=swap');
      `}</style>
 
      <div className={`fixed top-4 right-4 z-50 transition ${showSelector ? '' : 'translate-x-[calc(100%+1rem)]'}`}>
        <div className="bg-white shadow-2xl rounded-2xl border border-slate-200 w-80 overflow-hidden" style={{ fontFamily: 'Manrope, system-ui, sans-serif' }}>
          <div className="px-4 py-3 bg-gradient-to-br from-slate-900 to-slate-800 text-white flex items-center justify-between">
            <div>
              <div className="text-[10px] uppercase tracking-[0.2em] text-slate-400">Mockup activo</div>
              <div className="text-sm font-bold mt-0.5">{MOCKUPS.find((m) => m.id === active).name}</div>
            </div>
            <button onClick={() => setShowSelector(false)} className="text-slate-400 hover:text-white text-xs">Ocultar ✕</button>
          </div>
          <div className="p-2 space-y-1">
            {MOCKUPS.map((m) => (
              <button key={m.id} onClick={() => setActive(m.id)}
                className={`w-full text-left px-3 py-2.5 rounded-lg transition ${active === m.id ? 'bg-violet-50 ring-1 ring-violet-200' : 'hover:bg-slate-50'}`}>
                <div className="flex items-center gap-2">
                  <div className={`text-[13px] font-bold ${active === m.id ? 'text-violet-900' : 'text-slate-900'}`}>{m.name}</div>
                  {m.ready && <span className="text-[9px] uppercase tracking-wider bg-emerald-100 text-emerald-700 px-1.5 py-0.5 rounded font-bold">live</span>}
                </div>
                <div className={`text-[11px] mt-0.5 ${active === m.id ? 'text-violet-700' : 'text-slate-600'}`}>{m.tagline}</div>
                <div className="text-[10px] text-slate-500 mt-1">{m.desc}</div>
              </button>
            ))}
          </div>
          <div className="px-4 py-3 bg-slate-50 border-t border-slate-200 text-[10px] text-slate-500 leading-relaxed">
            Modular SaaS: 11 vistas en sidebar + click en filas para drill-down (cliente, proyecto, área).
          </div>
        </div>
      </div>
 
      {!showSelector && (
        <button onClick={() => setShowSelector(true)} className="fixed top-4 right-4 z-50 bg-violet-600 text-white px-3 py-2 rounded-lg text-xs font-semibold shadow-2xl hover:bg-violet-700" style={{ fontFamily: 'Manrope, system-ui, sans-serif' }}>
          Cambiar mockup ›
        </button>
      )}
 
      <Active />
    </div>
  );
}
 