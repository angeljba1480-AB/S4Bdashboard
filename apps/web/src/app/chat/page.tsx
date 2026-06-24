"use client";

import { CostMeter } from "@/components/CostMeter";
import { PrivacyBadge, SensitivityBadge } from "@/components/PrivacyBadge";
import { Shell } from "@/components/Shell";
import { SourceCitation } from "@/components/SourceCitation";
import { api } from "@/lib/api";
import type { Agent, ChatResponse, DocumentItem } from "@shared/types";
import { Send } from "lucide-react";
import { useEffect, useRef, useState } from "react";

interface Turn {
  role: "user" | "assistant";
  content: string;
  meta?: ChatResponse;
}

export default function ChatPage() {
  const [agents, setAgents] = useState<Agent[]>([]);
  const [docs, setDocs] = useState<DocumentItem[]>([]);
  const [agentId, setAgentId] = useState("");
  const [ctxMode, setCtxMode] = useState<"none" | "all" | "select">("all");
  const [selectedDocs, setSelectedDocs] = useState<string[]>([]);
  const [turns, setTurns] = useState<Turn[]>([]);
  const [input, setInput] = useState("");
  const [convId, setConvId] = useState<string | undefined>();
  const [loading, setLoading] = useState(false);
  const [preview, setPreview] = useState<Awaited<ReturnType<typeof api.previewRoute>> | null>(null);
  const endRef = useRef<HTMLDivElement>(null);

  useEffect(() => {
    api.agents().then((a) => {
      setAgents(a);
      if (a[0]) setAgentId(a[0].id);
    });
    api.documents().then(setDocs);
  }, []);

  useEffect(() => {
    endRef.current?.scrollIntoView({ behavior: "smooth" });
  }, [turns]);

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

  async function send() {
    if (!input.trim() || !agentId) return;
    const prompt = input.trim();
    setInput("");
    setTurns((t) => [...t, { role: "user", content: prompt }]);
    setLoading(true);
    try {
      const res = await api.chat({
        agent_id: agentId,
        prompt,
        conversation_id: convId,
        use_rag: ctxMode !== "none",
        document_ids: ctxMode === "select" && selectedDocs.length ? selectedDocs : undefined,
      });
      setConvId(res.conversation_id);
      setTurns((t) => [...t, { role: "assistant", content: res.content, meta: res }]);
    } catch (err) {
      setTurns((t) => [
        ...t,
        { role: "assistant", content: `Error: ${err instanceof Error ? err.message : "desconocido"}` },
      ]);
    } finally {
      setLoading(false);
    }
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
            {convId && (
              <div className="ml-auto flex gap-2">
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
              </div>
            )}
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
                  <div className="whitespace-pre-wrap">{t.content}</div>
                  {t.meta && (
                    <>
                      <div className="mt-2 text-xs text-slate-400">Ruta: {t.meta.reason}</div>
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
            <div className="flex gap-2">
              <input
                value={input}
                onChange={(e) => setInput(e.target.value)}
                onKeyDown={(e) => e.key === "Enter" && !e.shiftKey && (e.preventDefault(), send())}
                placeholder="Escribe tu pregunta…"
                className="flex-1 rounded-lg border border-slate-300 px-3 py-2 text-sm focus:border-violet-500 focus:outline-none"
              />
              <button
                onClick={send}
                disabled={loading}
                className="flex items-center gap-1.5 rounded-lg bg-violet-600 px-4 py-2 text-sm font-semibold text-white hover:bg-violet-700 disabled:opacity-50"
              >
                <Send className="h-4 w-4" /> Enviar
              </button>
            </div>
          </div>
        </div>

        <aside className="w-72 flex-shrink-0 border-l border-slate-200 bg-white p-4">
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
