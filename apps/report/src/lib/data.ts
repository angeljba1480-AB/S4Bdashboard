/**
 * Carga del dataset del reporte. Los datos reales NUNCA se commitean: llegan por la
 * variable de entorno `REPORT_DATA` (JSON, opcionalmente en base64) que se configura
 * en Vercel al desplegar. Si no está, cae al bundle demo versionado (datos de ejemplo).
 */
import demoBundle from "@/data/demo_bundle.json";

export type Kpis = Record<string, number>;

export type Overview = {
  entity: string;
  company: { name: string; period: string; ceo?: string; cfo?: string };
  kpis: Kpis;
  summary: Record<string, number | string>;
  monthly: { mes: string; ingresos: number; ebitda: number }[];
  segments: { name: string; revenue: number }[];
  gob_ip: Record<string, { gob: number; ip: number }>;
  benchmarks: { metric: string; s4b: number; industry: number; topQ: number; format: string; higherBetter: boolean }[];
  alerts: { level: string; area: string; msg: string; impact?: number }[];
  source: string;
  is_demo: boolean;
};

export type Client = { name: string; sector: string; entity: string; revenue: number; margin: number; status: string };

export type Projects = {
  source: string;
  totals: Kpis;
  trend: Record<string, { venta: number; gob: number; ip: number; ebitda: number; ebitda_bc: number; margen: number; proyectos: number; desviacion: number }>;
  cost_mix: { nomina: number; hw_sw: number; costo_corp: number; repr_viaticos: number; otros: number };
  clients: { name: string; sector: string; revenue: number; margin: number; status: string }[];
  detail: { cliente: string; nombre: string; tipo: string; venta: number; pct_margen: number; ebitda: number; desviacion: number }[];
};

export type Operations = {
  utilization: { year: string; horas_reales: number; horas_capacidad: number; utilizacion: number; empleados: number; capacidad_emp: number; by_project: { nombre: string; horas: number }[] };
  cost_per_hour: { year: string; by_role: { rol: string; costo_hora: number; registros: number }[] };
  client_scoring: { criteria: [string, number][]; clients: { name: string; sector: string; score: number; tier: string; facturacion: string; rentabilidad: string }[] };
  cost_comparison: { note: string; available: string[]; pending: string[]; by_month: { anio: string; mes: string; costo_bc: number | null; costo_cmi: number | null; costo_timesheet: number | null }[] };
  is_demo: boolean;
};

export type Bundle = {
  overview: Record<string, Overview>;
  clients: Record<string, Client[]>;
  projects: Projects;
  operations: Operations;
  /** Vistas cuyos datos siguen siendo demo (para etiquetarlas en la UI). */
  demoSections?: string[];
  meta?: { generatedAt?: string; sourceFiles?: string };
};

function parseEnv(raw: string): Bundle | null {
  const text = raw.trim();
  try {
    if (text.startsWith("{")) return JSON.parse(text) as Bundle;
    // base64 (JSON codificado) — útil para evitar problemas de escaping en env vars.
    const bin = atob(text);
    return JSON.parse(bin) as Bundle;
  } catch {
    return null;
  }
}

export function loadBundle(): Bundle {
  const raw = process.env.REPORT_DATA;
  if (raw && raw.trim()) {
    const parsed = parseEnv(raw);
    if (parsed) return parsed;
  }
  return demoBundle as unknown as Bundle;
}

export const DEMO_SECTION_LABELS: Record<string, string> = {
  resumen: "Resumen",
  finanzas: "Finanzas (P&L)",
  posicion: "Posición",
  clientes: "Clientes",
  benchmark: "Benchmark",
  alertas: "Alertas",
};
