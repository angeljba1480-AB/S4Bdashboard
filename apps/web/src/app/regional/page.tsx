"use client";

import { PageHeader, Shell } from "@/components/Shell";
import { api } from "@/lib/api";
import type { Eje, Procedure } from "@shared/types";
import { ArrowRight, MapPin } from "lucide-react";
import { useEffect, useState } from "react";

export default function RegionalPage() {
  const [ejes, setEjes] = useState<Eje[]>([]);
  const [countries, setCountries] = useState<{ code: string; name: string; division_label: string }[]>([]);
  const [country, setCountry] = useState("");
  const [estados, setEstados] = useState<string[]>([]);
  const [divisionLabel, setDivisionLabel] = useState("Estado/Provincia/Región");
  const [procedures, setProcedures] = useState<Procedure[]>([]);
  const [estado, setEstado] = useState("");
  const [eje, setEje] = useState("");
  const [q, setQ] = useState("");
  const [msg, setMsg] = useState("");

  useEffect(() => {
    api.regionalEjes().then(setEjes).catch(() => {});
    api.regionalCountries().then(setCountries).catch(() => {});
    api.me().then((m) => setCountry(m.country || "MX")).catch(() => setCountry("MX"));
  }, []);

  useEffect(() => {
    if (!country) return;
    setEstado("");
    api.regionalDivisions(country).then((d) => {
      setEstados(d.divisions);
      setDivisionLabel(d.division_label);
    }).catch(() => {});
  }, [country]);

  useEffect(() => {
    if (!country) return;
    api.regionalProcedures({ country, estado: estado || undefined, eje: eje || undefined, q: q || undefined })
      .then(setProcedures)
      .catch(() => {});
  }, [country, estado, eje, q]);

  async function propose(p: Procedure) {
    await api.procedureToProposal(p.id);
    setMsg(`«${p.title}» enviado a curación. Un admin lo activa en el catálogo de casos.`);
  }

  return (
    <Shell>
      <PageHeader
        title="Trámites y casos por región"
        subtitle="Problemas y trámites que enfrenta la población, por estado y eje de desarrollo. Conviértelos en casos de uso."
      />
      <div className="p-8">
        {msg && <div className="mb-4 rounded-lg bg-emerald-50 px-4 py-2 text-sm text-emerald-700">{msg}</div>}

        <div className="mb-5 flex flex-wrap items-center gap-2">
          <select
            value={country}
            onChange={(e) => setCountry(e.target.value)}
            className="rounded-lg border border-slate-300 px-3 py-2 text-sm font-medium"
          >
            {countries.map((c) => <option key={c.code} value={c.code}>{c.name}</option>)}
          </select>
          <select
            value={estado}
            onChange={(e) => setEstado(e.target.value)}
            className="rounded-lg border border-slate-300 px-3 py-2 text-sm"
            disabled={estados.length === 0}
          >
            <option value="">{`Todo (${divisionLabel})`}</option>
            {estados.map((s) => <option key={s} value={s}>{s}</option>)}
          </select>
          <input
            value={q}
            onChange={(e) => setQ(e.target.value)}
            placeholder="Buscar trámite o problema…"
            className="w-full max-w-xs rounded-lg border border-slate-300 px-3 py-2 text-sm"
          />
          <button
            onClick={() => setEje("")}
            className={`rounded-full px-3 py-1 text-xs font-medium ${eje === "" ? "bg-violet-600 text-white" : "bg-white text-slate-600 ring-1 ring-slate-200"}`}
          >
            Todos los ejes
          </button>
          {ejes.map((e) => (
            <button
              key={e.id}
              onClick={() => setEje(e.id)}
              className={`rounded-full px-3 py-1 text-xs font-medium ${eje === e.id ? "bg-violet-600 text-white" : "bg-white text-slate-600 ring-1 ring-slate-200"}`}
            >
              {e.label} <span className="opacity-60">{e.count}</span>
            </button>
          ))}
        </div>

        <div className="grid gap-4 sm:grid-cols-2 lg:grid-cols-3">
          {procedures.map((p) => (
            <div key={p.id} className="flex flex-col rounded-2xl border border-slate-200 bg-white p-5">
              <div className="mb-2 flex items-center gap-2 text-xs text-slate-400">
                <MapPin className="h-3.5 w-3.5" /> {p.scope} · {p.eje_label}
              </div>
              <div className="font-semibold text-slate-800">{p.title}</div>
              <p className="mt-1 flex-1 text-sm text-slate-500">{p.problem}</p>
              <button
                onClick={() => propose(p)}
                className="mt-3 inline-flex items-center gap-1 self-start rounded-lg bg-slate-900 px-3 py-1.5 text-xs font-semibold text-white"
              >
                Convertir en caso de uso <ArrowRight className="h-3.5 w-3.5" />
              </button>
            </div>
          ))}
        </div>
      </div>
    </Shell>
  );
}
