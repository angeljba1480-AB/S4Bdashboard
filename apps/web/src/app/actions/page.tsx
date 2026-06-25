"use client";

import { PageHeader, Shell } from "@/components/Shell";
import { api } from "@/lib/api";
import type { ActionRequestItem } from "@shared/types";
import { CheckCircle2, ShieldCheck, Wand2, X } from "lucide-react";
import { useEffect, useState } from "react";

type Action = { id: string; provider: string; label: string; write: boolean; params: string[]; connected: boolean; granted: boolean };

export default function ActionsPage() {
  const [actions, setActions] = useState<Action[]>([]);
  const [requests, setRequests] = useState<ActionRequestItem[]>([]);
  const [grants, setGrants] = useState<{ action: string; label: string }[]>([]);
  const [sel, setSel] = useState<Action | null>(null);
  const [params, setParams] = useState<Record<string, string>>({});
  const [msg, setMsg] = useState("");

  function load() {
    api.actions().then(setActions).catch(() => {});
    api.actionRequests().then(setRequests).catch(() => {});
    api.actionGrants().then(setGrants).catch(() => {});
  }
  useEffect(load, []);

  function pick(a: Action) { setSel(a); setParams({}); setMsg(""); }

  async function run() {
    if (!sel) return;
    setMsg("");
    try {
      const r = await api.runAction(sel.id, params);
      setMsg(r.status === "pending" ? "Enviado a aprobación." : `Ejecutado: ${r.request.result}`);
      setSel(null);
      load();
    } catch (e) { setMsg(e instanceof Error ? e.message : "Error"); }
  }

  async function approve(id: string, always: boolean) { await api.approveAction(id, always); load(); }
  async function reject(id: string) { await api.rejectAction(id); load(); }
  async function revoke(action: string) { await api.revokeGrant(action); load(); }

  const google = actions.filter((a) => a.provider === "google");
  const ms = actions.filter((a) => a.provider === "microsoft");
  const pending = requests.filter((r) => r.status === "pending");
  const recent = requests.filter((r) => r.status !== "pending").slice(0, 8);

  const Group = ({ title, items }: { title: string; items: Action[] }) => (
    <div className="rounded-2xl border border-slate-200 bg-white p-5">
      <h2 className="mb-3 font-semibold text-slate-800">{title}</h2>
      <div className="space-y-2">
        {items.map((a) => (
          <div key={a.id} className="flex items-center justify-between rounded-lg border border-slate-100 px-3 py-2 text-sm">
            <span className="flex items-center gap-2 text-slate-700">
              {a.label}
              {a.write && <span className="rounded-full bg-amber-100 px-1.5 py-0.5 text-[10px] font-semibold text-amber-700">escritura</span>}
              {a.granted && <span className="rounded-full bg-emerald-100 px-1.5 py-0.5 text-[10px] font-semibold text-emerald-700">permitida siempre</span>}
              {!a.connected && <span className="text-xs text-slate-400">· conecta {a.provider}</span>}
            </span>
            <button onClick={() => pick(a)} disabled={!a.connected}
              className="rounded-md bg-violet-600 px-3 py-1 text-xs font-semibold text-white disabled:opacity-40">Usar</button>
          </div>
        ))}
      </div>
    </div>
  );

  return (
    <Shell>
      <PageHeader title="Acciones" subtitle="Toolkit Google Workspace / Microsoft 365. Las acciones que modifican datos requieren tu aprobación." />
      <div className="grid grid-cols-1 gap-6 p-8 lg:grid-cols-3">
        <div className="space-y-6 lg:col-span-2">
          <Group title="Google Workspace" items={google} />
          <Group title="Microsoft 365" items={ms} />
        </div>

        <div className="space-y-6 lg:col-span-1">
          {/* Run form */}
          {sel && (
            <div className="rounded-2xl border border-violet-200 bg-white p-5">
              <div className="mb-2 flex items-center justify-between">
                <span className="flex items-center gap-1.5 font-semibold text-slate-800"><Wand2 className="h-4 w-4 text-violet-600" /> {sel.label}</span>
                <button onClick={() => setSel(null)} className="text-slate-400 hover:text-slate-600"><X className="h-4 w-4" /></button>
              </div>
              {sel.params.map((p) => (
                <input key={p} value={params[p] || ""} onChange={(e) => setParams((s) => ({ ...s, [p]: e.target.value }))}
                  placeholder={p} className="mb-2 w-full rounded-lg border border-slate-300 px-3 py-2 text-sm" />
              ))}
              <button onClick={run} className="w-full rounded-lg bg-violet-600 px-4 py-2 text-sm font-semibold text-white">
                {sel.write && !sel.granted ? "Enviar a aprobación" : "Ejecutar"}
              </button>
            </div>
          )}
          {msg && <div className="rounded-lg border border-slate-200 bg-slate-50 px-3 py-2 text-xs text-slate-600">{msg}</div>}

          {/* Pending approvals */}
          <div className="rounded-2xl border border-slate-200 bg-white p-5">
            <h2 className="mb-3 font-semibold text-slate-800">Pendientes de aprobación</h2>
            <div className="space-y-2">
              {pending.map((r) => (
                <div key={r.id} className="rounded-lg border border-amber-200 bg-amber-50 p-3 text-sm">
                  <div className="font-medium text-slate-700">{r.label}</div>
                  <div className="mt-0.5 truncate text-xs text-slate-500">{Object.values(r.params).join(" · ")}</div>
                  <div className="mt-2 flex flex-wrap gap-1.5">
                    <button onClick={() => approve(r.id, false)} className="rounded-md bg-emerald-600 px-2 py-1 text-xs font-semibold text-white">Aprobar</button>
                    <button onClick={() => approve(r.id, true)} className="rounded-md bg-emerald-700 px-2 py-1 text-xs font-semibold text-white">Aprobar y permitir siempre</button>
                    <button onClick={() => reject(r.id)} className="rounded-md border border-slate-300 px-2 py-1 text-xs font-semibold text-slate-600">Rechazar</button>
                  </div>
                </div>
              ))}
              {pending.length === 0 && <p className="text-xs text-slate-400">Nada pendiente.</p>}
            </div>
          </div>

          {/* Standing grants */}
          {grants.length > 0 && (
            <div className="rounded-2xl border border-slate-200 bg-white p-5">
              <h2 className="mb-3 flex items-center gap-1.5 font-semibold text-slate-800"><ShieldCheck className="h-4 w-4 text-emerald-600" /> Permitidas siempre</h2>
              <div className="space-y-1">
                {grants.map((g) => (
                  <div key={g.action} className="flex items-center justify-between rounded-lg border border-slate-100 px-3 py-1.5 text-sm">
                    <span className="text-slate-600">{g.label}</span>
                    <button onClick={() => revoke(g.action)} className="text-xs font-semibold text-red-600">Revocar</button>
                  </div>
                ))}
              </div>
            </div>
          )}

          {/* Recent */}
          {recent.length > 0 && (
            <div className="rounded-2xl border border-slate-200 bg-white p-5">
              <h2 className="mb-3 font-semibold text-slate-800">Recientes</h2>
              <div className="space-y-1">
                {recent.map((r) => (
                  <div key={r.id} className="flex items-center justify-between text-sm">
                    <span className="truncate text-slate-600">{r.label}</span>
                    <span className={`ml-2 flex shrink-0 items-center gap-1 text-xs ${r.status === "executed" ? "text-emerald-600" : r.status === "failed" ? "text-red-600" : "text-slate-400"}`}>
                      {r.status === "executed" && <CheckCircle2 className="h-3.5 w-3.5" />}{r.status}
                    </span>
                  </div>
                ))}
              </div>
            </div>
          )}
        </div>
      </div>
    </Shell>
  );
}
