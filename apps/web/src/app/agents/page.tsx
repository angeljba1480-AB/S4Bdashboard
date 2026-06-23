"use client";

import { PageHeader, Shell } from "@/components/Shell";
import { api } from "@/lib/api";
import type { Agent } from "@shared/types";
import { Bot, Plus } from "lucide-react";
import Link from "next/link";
import { useEffect, useState } from "react";

const AREA_COLORS: Record<string, string> = {
  ciberseguridad: "bg-red-50 text-red-600",
  ventas: "bg-emerald-50 text-emerald-600",
  finanzas: "bg-amber-50 text-amber-600",
  general: "bg-violet-50 text-violet-600",
};

export default function AgentsPage() {
  const [agents, setAgents] = useState<Agent[]>([]);
  const [showForm, setShowForm] = useState(false);
  const [name, setName] = useState("");
  const [area, setArea] = useState("general");
  const [mode, setMode] = useState("auto");

  function load() {
    api.agents().then(setAgents);
  }
  useEffect(load, []);

  async function create(e: React.FormEvent) {
    e.preventDefault();
    await api.createAgent({ name, area, privacy_mode: mode, type: "general" });
    setName("");
    setShowForm(false);
    load();
  }

  return (
    <Shell>
      <PageHeader title="Agentes verticales" subtitle="Agentes por área: legal, ventas, ciberseguridad, finanzas, RH." />
      <div className="p-8">
        <div className="mb-5 flex justify-end">
          <button
            onClick={() => setShowForm((s) => !s)}
            className="flex items-center gap-1.5 rounded-lg bg-violet-600 px-4 py-2 text-sm font-semibold text-white hover:bg-violet-700"
          >
            <Plus className="h-4 w-4" /> Nuevo agente
          </button>
        </div>

        {showForm && (
          <form onSubmit={create} className="mb-6 grid grid-cols-1 gap-3 rounded-2xl border border-slate-200 bg-white p-5 sm:grid-cols-4">
            <input
              required
              value={name}
              onChange={(e) => setName(e.target.value)}
              placeholder="Nombre del agente"
              className="rounded-lg border border-slate-300 px-3 py-2 text-sm sm:col-span-2"
            />
            <select value={area} onChange={(e) => setArea(e.target.value)} className="rounded-lg border border-slate-300 px-3 py-2 text-sm">
              <option value="general">General</option>
              <option value="ciberseguridad">Ciberseguridad</option>
              <option value="ventas">Ventas</option>
              <option value="finanzas">Finanzas</option>
              <option value="legal">Legal</option>
              <option value="rh">RH</option>
            </select>
            <select value={mode} onChange={(e) => setMode(e.target.value)} className="rounded-lg border border-slate-300 px-3 py-2 text-sm">
              <option value="auto">Privacidad: auto</option>
              <option value="no_external">Sin salida externa</option>
              <option value="local_only">Solo local</option>
            </select>
            <button className="rounded-lg bg-slate-900 px-4 py-2 text-sm font-semibold text-white sm:col-span-4">
              Crear agente
            </button>
          </form>
        )}

        <div className="grid grid-cols-1 gap-4 md:grid-cols-2 lg:grid-cols-3">
          {agents.map((a) => (
            <Link
              key={a.id}
              href={`/agents/${a.id}`}
              className="rounded-2xl border border-slate-200 bg-white p-5 transition hover:border-violet-300 hover:shadow-sm"
            >
              <div className="mb-3 flex items-center justify-between">
                <div className="flex h-10 w-10 items-center justify-center rounded-lg bg-violet-50">
                  <Bot className="h-5 w-5 text-violet-600" />
                </div>
                <span className={`rounded-full px-2 py-0.5 text-xs font-medium ${AREA_COLORS[a.area] ?? "bg-slate-100 text-slate-600"}`}>
                  {a.area}
                </span>
              </div>
              <div className="font-semibold text-slate-900">{a.name}</div>
              <div className="mt-1 text-sm text-slate-500">{a.type}</div>
              <div className="mt-3 flex items-center gap-2 text-xs text-slate-400">
                <span className="rounded bg-slate-100 px-1.5 py-0.5">{a.privacy_mode}</span>
                {a.requires_premium_reasoning && (
                  <span className="rounded bg-violet-100 px-1.5 py-0.5 text-violet-600">premium</span>
                )}
              </div>
            </Link>
          ))}
        </div>
      </div>
    </Shell>
  );
}
