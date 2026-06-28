"use client";

import { CostMeter } from "@/components/CostMeter";
import { PrivacyBadge, SensitivityBadge } from "@/components/PrivacyBadge";
import { Shell } from "@/components/Shell";
import { HelpButton } from "@/components/HelpButton";
import { SourceCitation } from "@/components/SourceCitation";
import { api } from "@/lib/api";
import { cleanMarkdown } from "@/lib/format";
import type { Agent, ChatResponse, DocumentItem } from "@shared/types";
import { Brain, Mic, Pause, Plus, Save, Send, Sparkles, Trash2, Volume2, Zap } from "lucide-react";
import { useEffect, useRef, useState } from "react";

interface Turn {
  role: "user" | "assistant";
  content: string;
  meta?: ChatResponse;
}

type ConvSummary = { id: string; title: string; agent_id: string; agent_name: string; messages: number; created_at: string };

export default function ChatPage() {
  const [agents, setAgents] = useState<Agent[]>([]);
  const [docs, setDocs] = useState<DocumentItem[]>([]);
  const [agentId, setAgentId] = useState("");
  const [ctxMode, setCtxMode] = useState<"none" | "all" | "select">("all");
  const [precision, setPrecision] = useState(false);
  const [useMemory, setUseMemory] = useState(false);
  const [lastPrompt, setLastPrompt] = useState("");
  const [selectedDocs, setSelectedDocs] = useState<string[]>([]);
  const [turns, setTurns] = useState<Turn[]>([]);
  const [input, setInput] = useState("");
  const [convId, setConvId] = useState<string | undefined>();
  const [history, setHistory] = useState<ConvSummary[]>([]);
  const [loading, setLoading] = useState(false);
  const [preview, setPreview] = useState<Awaited<ReturnType<typeof api.previewRoute>> | null>(null);
  const [narrating, setNarrating] = useState<number | null>(null);
  const audioRef = useRef<HTMLAudioElement | null>(null);
  const endRef = useRef<HTMLDivElement>(null);

  useEffect(() => {
    api.agents().then((a) => {
      setAgents(a);
      if (a[0]) setAgentId(a[0].id);
    });
    api.documents().then(setDocs);
    loadHistory();
  }, []);

  function loadHistory() { api.conversations().then(setHistory).catch(() => {}); }

  async function openConversation(id: string) {
    stopAudio();
    try {
      const c = await api.conversation(id);
      setConvId(c.id);
      if (c.agent_id) setAgentId(c.agent_id);
      setTurns(c.messages.map((m) => ({ role: m.role === "user" ? "user" : "assistant", content: m.content })));
    } catch { /* noop */ }
  }
  function newChat() {
    stopAudio();
    setConvId(undefined);
    setTurns([]);
    setInput("");
  }
  async function removeConversation(id: string) {
    await api.deleteConversation(id);
    if (id === convId) newChat();
    loadHistory();
  }

  useEffect(() => {
    endRef.current?.scrollIntoView({ behavior: "smooth" });
  }, [turns]);

  // Detener la narración al desmontar la página.
  useEffect(() => () => {
    if (audioRef.current) { audioRef.current.pause(); audioRef.current = null; }
  }, []);

  // Live route advisory: as the user types, preview classification + route.
  useEffect(() => {
    if (!input.trim() || !agentId) {
      setPreview(null);
      return;
    }
    const t = setTimeout(() => {
      api
        .previewRoute({
          agent_id: agentId, prompt: input.trim(),
          use_rag: ctxMode !== "none",
          document_ids: ctxMode === "select" && selectedDocs.length ? selectedDocs : undefined,
        })
        .then(setPreview)
        .catch(() => setPreview(null));
    }, 500);
    return () => clearTimeout(t);
  }, [input, agentId, selectedDocs, ctxMode]);

  async function send(promptArg?: string, approveExternal = false) {
    const prompt = (promptArg ?? input).trim();
    if (!prompt || !agentId) return;
    if (!promptArg) { setInput(""); setTurns((t) => [...t, { role: "user", content: prompt }]); }
    setLoading(true);
    try {
      const res = await api.chat({
        agent_id: agentId,
        prompt,
        conversation_id: convId,
        use_rag: ctxMode !== "none",
        use_memory: useMemory,
        document_ids: ctxMode === "select" && selectedDocs.length ? selectedDocs : undefined,
        precision,
        approve_external: approveExternal,
      });
      const wasNew = !convId;
      setConvId(res.conversation_id);
      setLastPrompt(prompt);
      setTurns((t) => [...t, { role: "assistant", content: res.content, meta: res }]);
      if (wasNew) loadHistory();
    } catch (err) {
      setTurns((t) => [
        ...t,
        { role: "assistant", content: `Error: ${err instanceof Error ? err.message : "desconocido"}` },
      ]);
    } finally {
      setLoading(false);
    }
  }

  function stopAudio() {
    if (audioRef.current) {
      audioRef.current.pause();
      audioRef.current.src = "";
      audioRef.current = null;
    }
    setNarrating(null);
  }

  async function narrate(text: string, idx: number) {
    // Toggle: si ya está sonando ese mensaje, lo paramos.
    if (narrating === idx) { stopAudio(); return; }
    stopAudio();                       // corta cualquier audio previo
    setNarrating(idx);
    try {
      const blob = await api.tts(text);
      const audio = new Audio(URL.createObjectURL(blob));
      audioRef.current = audio;
      audio.onended = () => { audioRef.current = null; setNarrating((c) => (c === idx ? null : c)); };
      await audio.play();
    } catch (e) {
      stopAudio();
      alert(e instanceof Error ? e.message : "No se pudo narrar");
    }
  }

  async function transcribe(file: File) {
    const form = new FormData();
    form.append("file", file);
    try {
      const r = await api.transcribe(form);
      setInput((v) => (v ? v + " " : "") + r.text);
    } catch (e) { alert(e instanceof Error ? e.message : "No se pudo transcribir"); }
  }

  async function runAsAction() {
    const instr = input.trim();
    if (!instr) return;
    setInput("");
    setTurns((t) => [...t, { role: "user", content: `⚡ ${instr}` }]);
    setLoading(true);
    try {
      const r = await api.agentRun(instr, false, false);
      const lines = r.steps.length
        ? r.steps.map((s, i) => `${i + 1}. ${s.label} — ${s.step_status.replace("_", " ")}`).join("\n")
        : (r.note || "No identifiqué acciones para esa instrucción.");
      setTurns((t) => [...t, { role: "assistant", content:
        `Plan del agente (${r.source}):\n${lines}\n\nLas escrituras pendientes se aprueban en «Acciones».` }]);
    } catch (e) {
      setTurns((t) => [...t, { role: "assistant", content: `Error: ${e instanceof Error ? e.message : "desconocido"}` }]);
    } finally { setLoading(false); }
  }

  async function saveToMemory(content: string) {
    const title = (lastPrompt || content).slice(0, 60);
    try {
      await api.createMemory({ title, content, source: "chat", tags: ["chat"] });
      alert("Guardado en memoria ✓");
    } catch { alert("No se pudo guardar"); }
  }

  function toggleDoc(id: string) {
    setSelectedDocs((s) => (s.includes(id) ? s.filter((x) => x !== id) : [...s, id]));
  }

  return (
    <Shell>
      <div className="flex h-screen">
        <div className="flex flex-1 flex-col">
          <div className="flex items-center gap-3 border-b border-slate-200 bg-white px-6 py-3">
            <span className="text-sm text-slate-500">Agente:</span>
            <select
              value={agentId}
              onChange={(e) => {
                stopAudio();
                setAgentId(e.target.value);
                setTurns([]);
                setConvId(undefined);
              }}
              className="rounded-lg border border-slate-300 px-3 py-1.5 text-sm"
            >
              {agents.map((a) => (
                <option key={a.id} value={a.id}>
                  {a.name} · {a.privacy_mode}
                </option>
              ))}
            </select>
            <div className="ml-auto flex items-center gap-2">
              <HelpButton topics={["chat", "documentos", "modelos"]} />
              {convId && (
                <>
                  <button
                    onClick={() => api.exportConversation(convId, "pdf")}
                    className="rounded-lg border border-slate-300 px-3 py-1.5 text-xs text-slate-600 hover:bg-slate-50"
                  >
                    Exportar PDF
                  </button>
                  <button
                    onClick={() => api.exportConversation(convId, "md")}
                    className="rounded-lg border border-slate-300 px-3 py-1.5 text-xs text-slate-600 hover:bg-slate-50"
                  >
                    Markdown
                  </button>
                </>
              )}
            </div>
          </div>

          <div className="flex-1 space-y-4 overflow-auto p-6">
            {turns.length === 0 && (
              <div className="mx-auto mt-16 max-w-md text-center text-slate-400">
                <p className="text-sm">
                  Haz una pregunta. La plataforma clasifica la sensibilidad, detecta PII, elige la ruta de
                  modelo y responde con fuentes — todo auditado.
                </p>
              </div>
            )}
            {turns.map((t, i) => (
              <div key={i} className={`flex ${t.role === "user" ? "justify-end" : "justify-start"}`}>
                <div
                  className={`max-w-2xl rounded-2xl px-4 py-3 text-sm ${
                    t.role === "user"
                      ? "bg-violet-600 text-white"
                      : "border border-slate-200 bg-white text-slate-800"
                  }`}
                >
                  {t.meta && (
                    <div className="mb-2 flex flex-wrap items-center gap-2">
                      <PrivacyBadge route={t.meta.route} />
                      <SensitivityBadge level={t.meta.classification} />
                      {t.meta.redacted && (
                        <span className="rounded-full bg-amber-100 px-2 py-0.5 text-xs text-amber-700">
                          PII redactado
                        </span>
                      )}
                      <CostMeter tokens={t.meta.token_count} cost={t.meta.cost_estimate} />
                    </div>
                  )}
                  {t.role === "assistant" ? (
                    <div className="space-y-2">
                      {t.content.split("```").map((part, k) => {
                        if (k % 2 === 1) {
                          const nl = part.indexOf("\n");
                          const code = (nl >= 0 ? part.slice(nl + 1) : part).replace(/\n$/, "");
                          return (
                            <pre key={k} className="overflow-x-auto rounded-lg bg-slate-900 p-3 text-xs text-slate-100">
                              <code>{code}</code>
                            </pre>
                          );
                        }
                        const clean = cleanMarkdown(part);
                        return clean ? <div key={k} className="whitespace-pre-wrap">{clean}</div> : null;
                      })}
                    </div>
                  ) : (
                    <div className="whitespace-pre-wrap">{t.content}</div>
                  )}
                  {t.meta?.escalated && (
                    <div className="mt-2 inline-flex items-center gap-1 rounded-full bg-violet-100 px-2 py-0.5 text-xs font-semibold text-violet-700">
                      <Sparkles className="h-3 w-3" /> Refinado con premium
                    </div>
                  )}
                  {t.meta?.escalation_pending && (
                    <div className="mt-2 rounded-lg border border-amber-200 bg-amber-50 px-3 py-2 text-xs text-amber-800">
                      Contenido sensible. ¿Refinar con el modelo premium (envío externo con PII redactada)?
                      <button onClick={() => send(lastPrompt, true)} disabled={loading}
                        className="ml-2 rounded-md bg-amber-600 px-2 py-1 font-semibold text-white disabled:opacity-50">
                        Aprobar y refinar
                      </button>
                    </div>
                  )}
                  {t.meta && (
                    <>
                      <div className="mt-2 flex items-center justify-between">
                        <span className="text-xs text-slate-400">Ruta: {t.meta.reason}</span>
                        <span className="flex items-center gap-3">
                          <button onClick={() => narrate(cleanMarkdown(t.content), i)}
                            className="flex items-center gap-1 text-xs font-semibold text-violet-600 hover:text-violet-800">
                            {narrating === i ? <><Pause className="h-3 w-3" /> Detener</> : <><Volume2 className="h-3 w-3" /> Narrar</>}
                          </button>
                          <button onClick={() => saveToMemory(t.content)}
                            className="flex items-center gap-1 text-xs font-semibold text-violet-600 hover:text-violet-800">
                            <Save className="h-3 w-3" /> Guardar en memoria
                          </button>
                        </span>
                      </div>
                      <SourceCitation citations={t.meta.citations} />
                    </>
                  )}
                </div>
              </div>
            ))}
            {loading && <div className="text-sm text-slate-400">Procesando con el router de privacidad…</div>}
            <div ref={endRef} />
          </div>

          <div className="border-t border-slate-200 bg-white p-4">
            {preview && (
              <div
                className={`mb-2 rounded-lg border px-3 py-2 text-xs ${
                  preview.level === "block"
                    ? "border-red-200 bg-red-50 text-red-700"
                    : preview.level === "warn"
                      ? "border-amber-200 bg-amber-50 text-amber-700"
                      : "border-emerald-200 bg-emerald-50 text-emerald-700"
                }`}
              >
                {preview.message}
                {preview.sources_found > 0 && (
                  <span className="opacity-70"> · {preview.sources_found} fuente(s) en contexto</span>
                )}
              </div>
            )}
            <div className="mb-2 flex flex-wrap gap-4">
              <label className="flex w-fit cursor-pointer items-center gap-1.5 text-xs text-slate-600">
                <input type="checkbox" checked={precision} onChange={(e) => setPrecision(e.target.checked)} />
                <Sparkles className="h-3.5 w-3.5 text-violet-600" /> Máxima precisión (refina con premium)
              </label>
              <label className="flex w-fit cursor-pointer items-center gap-1.5 text-xs text-slate-600">
                <input type="checkbox" checked={useMemory} onChange={(e) => setUseMemory(e.target.checked)} />
                <Brain className="h-3.5 w-3.5 text-violet-600" /> Usar memoria (trabajos previos)
              </label>
            </div>
            <div className="flex gap-2">
              <input
                value={input}
                onChange={(e) => setInput(e.target.value)}
                onKeyDown={(e) => e.key === "Enter" && !e.shiftKey && (e.preventDefault(), send())}
                placeholder="Escribe tu pregunta…"
                className="flex-1 rounded-lg border border-slate-300 px-3 py-2 text-sm focus:border-violet-500 focus:outline-none"
              />
              <label title="Transcribir audio (voz → texto)"
                className="flex cursor-pointer items-center rounded-lg border border-slate-300 px-2.5 py-2 text-slate-500 hover:bg-slate-50">
                <Mic className="h-4 w-4" />
                <input type="file" accept="audio/*" className="hidden"
                  onChange={(e) => { const f = e.target.files?.[0]; if (f) transcribe(f); e.target.value = ""; }} />
              </label>
              <button
                onClick={runAsAction}
                disabled={loading || !input.trim()}
                title="Ejecutar como acción (el agente hace los pasos en las herramientas)"
                className="flex items-center gap-1.5 rounded-lg border border-violet-300 bg-white px-3 py-2 text-sm font-semibold text-violet-700 hover:bg-violet-50 disabled:opacity-50"
              >
                <Zap className="h-4 w-4" /> Acción
              </button>
              <button
                onClick={() => send()}
                disabled={loading}
                className="flex items-center gap-1.5 rounded-lg bg-violet-600 px-4 py-2 text-sm font-semibold text-white hover:bg-violet-700 disabled:opacity-50"
              >
                <Send className="h-4 w-4" /> Enviar
              </button>
            </div>
          </div>
        </div>

        <aside className="w-72 flex-shrink-0 overflow-auto border-l border-slate-200 bg-white p-4">
          <div className="mb-2 flex items-center justify-between">
            <h3 className="text-sm font-semibold text-slate-700">Chats recientes</h3>
            <button onClick={newChat} title="Nuevo chat"
              className="flex items-center gap-1 rounded-lg border border-slate-300 px-2 py-1 text-xs font-semibold text-slate-600 hover:bg-slate-50">
              <Plus className="h-3.5 w-3.5" /> Nuevo
            </button>
          </div>
          <div className="mb-4 space-y-1">
            {history.length === 0 && <p className="text-xs text-slate-400">Aún no tienes chats.</p>}
            {history.map((c) => (
              <div key={c.id}
                className={`group flex items-center gap-1 rounded-lg border px-2 py-1.5 ${c.id === convId ? "border-violet-300 bg-violet-50" : "border-transparent hover:bg-slate-50"}`}>
                <button onClick={() => openConversation(c.id)} className="min-w-0 flex-1 text-left">
                  <span className="block truncate text-sm text-slate-700">{c.title}</span>
                  <span className="block truncate text-[11px] text-slate-400">{c.agent_name} · {c.messages} msj</span>
                </button>
                <button onClick={() => removeConversation(c.id)} title="Borrar"
                  className="shrink-0 rounded-md p-1 text-slate-300 hover:bg-red-50 hover:text-red-500 group-hover:text-slate-400">
                  <Trash2 className="h-3.5 w-3.5" />
                </button>
              </div>
            ))}
          </div>

          <h3 className="mb-3 text-sm font-semibold text-slate-700">Contexto</h3>
          <div className="mb-4 space-y-1.5">
            {([
              ["none", "Sin contexto", "Solo IA, no usa tus documentos."],
              ["all", "Buscar en todo", "El RAG busca en todos tus documentos."],
              ["select", "Elegir documentos", "Solo los documentos que marques abajo."],
            ] as const).map(([mode, label, hint]) => (
              <label key={mode} className={`block cursor-pointer rounded-lg border px-3 py-2 text-sm ${ctxMode === mode ? "border-violet-400 bg-violet-50" : "border-slate-200 hover:bg-slate-50"}`}>
                <span className="flex items-center gap-2">
                  <input type="radio" name="ctxmode" checked={ctxMode === mode} onChange={() => setCtxMode(mode)} />
                  <span className="font-medium text-slate-700">{label}</span>
                </span>
                <span className="ml-6 block text-xs text-slate-400">{hint}</span>
              </label>
            ))}
          </div>

          {ctxMode === "select" && (
            <div className="space-y-2">
              <h4 className="text-xs font-semibold uppercase text-slate-400">Documentos</h4>
              {docs.length === 0 && <p className="text-xs text-slate-400">No tienes documentos. Súbelos en «Documentos».</p>}
              {docs.map((d) => (
                <label key={d.id} className="flex cursor-pointer items-start gap-2 text-sm">
                  <input
                    type="checkbox"
                    checked={selectedDocs.includes(d.id)}
                    onChange={() => toggleDoc(d.id)}
                    className="mt-0.5"
                  />
                  <span>
                    <span className="block text-slate-700">{d.filename}</span>
                    <SensitivityBadge level={d.sensitivity} />
                  </span>
                </label>
              ))}
              {ctxMode === "select" && selectedDocs.length === 0 && (
                <p className="text-xs text-amber-600">Marca al menos un documento o cambia el modo.</p>
              )}
            </div>
          )}
        </aside>
      </div>
    </Shell>
  );
}
