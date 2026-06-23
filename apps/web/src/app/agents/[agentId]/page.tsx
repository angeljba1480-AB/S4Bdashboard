"use client";

import { PageHeader, Shell } from "@/components/Shell";
import { api } from "@/lib/api";
import type { Agent } from "@shared/types";
import { ArrowLeft } from "lucide-react";
import Link from "next/link";
import { useParams } from "next/navigation";
import { useEffect, useState } from "react";

export default function AgentDetail() {
  const params = useParams<{ agentId: string }>();
  const [agent, setAgent] = useState<Agent | null>(null);

  useEffect(() => {
    if (params.agentId) api.agent(params.agentId).then(setAgent).catch(() => {});
  }, [params.agentId]);

  return (
    <Shell>
      <PageHeader title={agent?.name ?? "Agente"} subtitle="Configuración y política de privacidad del agente." />
      <div className="p-8">
        <Link href="/agents" className="mb-4 inline-flex items-center gap-1 text-sm text-slate-500 hover:text-slate-800">
          <ArrowLeft className="h-4 w-4" /> Volver a agentes
        </Link>
        {agent && (
          <div className="grid grid-cols-1 gap-4 sm:grid-cols-2 lg:grid-cols-3">
            {[
              ["Tipo", agent.type],
              ["Área", agent.area],
              ["Modo de privacidad", agent.privacy_mode],
              ["Razonamiento premium", agent.requires_premium_reasoning ? "Sí" : "No"],
              ["Estado", agent.status],
              ["ID", agent.id],
            ].map(([k, v]) => (
              <div key={k} className="rounded-2xl border border-slate-200 bg-white p-5">
                <div className="text-xs uppercase tracking-wide text-slate-400">{k}</div>
                <div className="mt-1 font-semibold text-slate-800">{v}</div>
              </div>
            ))}
          </div>
        )}
        {agent && (
          <Link
            href="/chat"
            className="mt-6 inline-block rounded-lg bg-violet-600 px-4 py-2 text-sm font-semibold text-white hover:bg-violet-700"
          >
            Usar este agente en el chat →
          </Link>
        )}
      </div>
    </Shell>
  );
}
