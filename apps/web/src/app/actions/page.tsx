"use client";

import { PageHeader, Shell } from "@/components/Shell";
import { api } from "@/lib/api";
import type { ActionRequestItem } from "@shared/types";
import { BookMarked, CheckCircle2, Eye, Loader2, Play, ShieldCheck, Sparkles, Trash2, Wand2, X } from "lucide-react";
import { useEffect, useState } from "react";

type Action = { id: string; provider: string; label: string; write: boolean; params: string[]; connected: boolean; granted: boolean };
type AgentStep = ActionRequestItem & { step_status: string; reason: string };
type Playbook = { id: string; name: string; instruction: string; auto_approve: boolean; created_at: string };

export default function ActionsPage() {
  const [actions, setActions] = useState<Action[]>([]);
  const [requests, setRequests] = useState<ActionRequestItem[]>([]);
  const [grants, setGrants] = useState<{ action: string; label: string }[]>([]);
  const [sel, setSel] = useState<Action | null>(null);
  const [params, setParams] = useState<Record<string, string>>({});
  const [msg, setMsg] = useState("");
  // Asistente: el modelo traduce una instrucción a pasos y los ejecuta por detrás.
  const [instruction, setInstruction] = useState("");
  const [autoApprove, setAutoApprove] = useState(false);
  const [running, setRunning] = useState(false);
  const [agentSteps, setAgentSteps] = useState<AgentStep[] | null>(null);
  const [agentNote, setAgentNote] = useState("");
  const [isPreview, setIsPreview] = useState(false);
  const [playbooks, setPlaybooks] = useState<Playbook[]>([]);

  function load() {
    api.actions().then(setActions).catch(() => {});
    api.actionRequests().then(setRequests).catch(() => {});
    api.actionGrants().then(setGrants).catch(() => {});
    api.playbooks().then(setPlaybooks).catch(() => {});
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

  async function runAgent(dryRun: boolean) {
    if (!instruction.trim()) return;
    setRunning(true); setAgentSteps(null); setAgentNote(""); setIsPreview(dryRun);
    try {
      const r = await api.agentRun(instruction.trim(), autoApprove, dryRun);
      setAgentSteps(r.steps);
      setAgentNote(r.steps.length === 0
        ? (r.note || "No identifiqué acciones para esa instrucción.")
        : dryRun ? `Previsualización (${r.source}) — nada se ejecutó todavía.` : `Plan ejecutado (${r.source}).`);
      if (!dryRun) load();
    } catch (e) { setAgentNote(e instanceof Error ? e.message : "Error"); }
    finally { setRunning(false); }
  }

  async function savePlaybook() {
    if (!instruction.trim()) return;
    const name = window.prompt("Nombre de la receta:", instruction.trim().slice(0, 40));
    if (!name) return;
    try {
      await api.createPlaybook({ name, instruction: instruction.trim(), auto_approve: autoApprove });
      api.playbooks().then(setPlaybooks).catch(() => {});
      setAgentNote(`Receta «${name}» guardada.`);
    } catch (e) { setAgentNote(e instanceof Error ? e.message : "Error"); }
  }

  async function runPlaybook(pb: Playbook, dryRun: boolean) {
    setRunning(true); setAgentSteps(null); setAgentNote(""); setIsPreview(dryRun); setInstruction(pb.instruction);
    try {
      const r = await api.runPlaybook(pb.id, dryRun);
      setAgentSteps(r.steps);
      setAgentNote(`«${pb.name}» — ${dryRun ? "previsualización" : "ejecutada"} (${r.source}).`);
      if (!dryRun) load();
    } catch (e) { setAgentNote(e instanceof Error ? e.message : "Error"); }
    finally { setRunning(false); }
  }

  async function removePlaybook(id: string) {
    await api.deletePlaybook(id);
    api.playbooks().then(setPlaybooks).catch(() => {});
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
      <PageHeader title="Acciones" subtitle="Toolkit Google Workspace / Microsoft 365. Las acciones que modifican datos requieren tu aprobación." help="acciones" />
      <div className="grid grid-cols-1 gap-6 p-8 lg:grid-cols-3">
        <div className="space-y-6 lg:col-span-2">
          {/* Asistente: el modelo ejecuta los pasos en las herramientas por detrás */}
          <div className="rounded-2xl border border-violet-200 bg-gradient-to-br from-violet-50 to-white p-5">
            <h2 className="mb-1 flex items-center gap-1.5 font-semibold text-slate-800">
              <Sparkles className="h-4 w-4 text-violet-600" /> Asistente de acciones
            </h2>
            <p className="mb-3 text-xs text-slate-500">
              Escribe una instrucción en lenguaje natural y el modelo ejecuta los pasos en
              las herramientas. Las lecturas corren al momento; las escrituras requieren tu
              aprobación (salvo «Permitir siempre» o ejecución directa).
            </p>
            <textarea value={instruction} onChange={(e) => setInstruction(e.target.value)} rows={2}
              placeholder="Ej.: muéstrame mis próximos eventos y envía un correo de seguimiento a Juan"
              className="mb-2 w-full rounded-lg border border-slate-300 px-3 py-2 text-sm" />
            <div className="flex flex-wrap items-center gap-2">
              <button onClick={() => runAgent(true)} disabled={running || !instruction.trim()}
                className="flex items-center gap-1.5 rounded-lg border border-violet-300 bg-white px-3 py-2 text-sm font-semibold text-violet-700 disabled:opacity-40">
                <Eye className="h-4 w-4" /> Previsualizar
              </button>
              <button onClick={() => runAgent(false)} disabled={running || !instruction.trim()}
                className="flex items-center gap-1.5 rounded-lg bg-violet-600 px-4 py-2 text-sm font-semibold text-white disabled:opacity-40">
                {running ? <Loader2 className="h-4 w-4 animate-spin" /> : <Sparkles className="h-4 w-4" />}
                {running ? "Trabajando…" : "Ejecutar"}
              </button>
              <button onClick={savePlaybook} disabled={!instruction.trim()}
                className="flex items-center gap-1.5 rounded-lg border border-slate-300 bg-white px-3 py-2 text-sm font-semibold text-slate-600 disabled:opacity-40">
                <BookMarked className="h-4 w-4" /> Guardar receta
              </button>
              <label className="flex items-center gap-1.5 text-xs text-slate-600">
                <input type="checkbox" checked={autoApprove} onChange={(e) => setAutoApprove(e.target.checked)} />
                Escrituras sin aprobación
              </label>
            </div>
            {agentNote && <div className="mt-3 rounded-lg border border-slate-200 bg-white px-3 py-2 text-xs text-slate-600">{agentNote}</div>}
            {agentSteps && agentSteps.length > 0 && (
              <ol className="mt-3 space-y-2">
                {agentSteps.map((s, i) => {
                  const done = s.step_status === "ejecutado";
                  const proposed = isPreview;
                  return (
                    <li key={s.id || `${s.action}-${i}`} className="rounded-lg border border-slate-100 bg-white p-3 text-sm">
                      <div className="flex items-center justify-between">
                        <span className="font-medium text-slate-700">{i + 1}. {s.label}</span>
                        <span className={`flex shrink-0 items-center gap-1 text-xs ${done ? "text-emerald-600" : proposed ? "text-violet-600" : "text-amber-600"}`}>
                          {done ? <CheckCircle2 className="h-3.5 w-3.5" /> : proposed ? <Eye className="h-3.5 w-3.5" /> : <ShieldCheck className="h-3.5 w-3.5" />}
                          {s.step_status.replace("_", " ")}
                        </span>
                      </div>
                      {s.reason && <div className="mt-0.5 text-xs text-slate-500">{s.reason}</div>}
                    </li>
                  );
                })}
              </ol>
            )}
          </div>

          {/* Recetas guardadas (playbooks) */}
          {playbooks.length > 0 && (
            <div className="rounded-2xl border border-slate-200 bg-white p-5">
              <h2 className="mb-3 flex items-center gap-1.5 font-semibold text-slate-800">
                <BookMarked className="h-4 w-4 text-violet-600" /> Recetas guardadas
              </h2>
              <div className="space-y-2">
                {playbooks.map((pb) => (
                  <div key={pb.id} className="rounded-lg border border-slate-100 p-3">
                    <div className="flex items-center justify-between">
                      <span className="font-medium text-slate-700">{pb.name}</span>
                      <div className="flex items-center gap-1.5">
                        <button onClick={() => runPlaybook(pb, true)} title="Previsualizar"
                          className="rounded-md border border-slate-300 p-1 text-slate-500"><Eye className="h-3.5 w-3.5" /></button>
                        <button onClick={() => runPlaybook(pb, false)} title="Ejecutar"
                          className="rounded-md bg-violet-600 p-1 text-white"><Play className="h-3.5 w-3.5" /></button>
                        <button onClick={() => removePlaybook(pb.id)} title="Eliminar"
                          className="rounded-md border border-slate-300 p-1 text-red-500"><Trash2 className="h-3.5 w-3.5" /></button>
                      </div>
                    </div>
                    <div className="mt-0.5 truncate text-xs text-slate-500">{pb.instruction}</div>
                  </div>
                ))}
              </div>
            </div>
          )}

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
