"use client";

import { AuthImage } from "@/components/AuthImage";
import { PageHeader, Shell } from "@/components/Shell";
import { api, type GeneratedImageDto } from "@/lib/api";
import { ImageIcon, Sparkles, Trash2, Wand2, X } from "lucide-react";
import { useEffect, useState } from "react";

const ASPECTS = ["1:1", "16:9", "9:16"];
const VARIANTS = [1, 2, 3, 4];

export default function GeneratePage() {
  const [mode, setMode] = useState<"generate" | "edit">("generate");
  const [prompt, setPrompt] = useState("");
  const [aspect, setAspect] = useState("1:1");
  const [variants, setVariants] = useState(1);
  const [refs, setRefs] = useState<File[]>([]);
  const [gallery, setGallery] = useState<GeneratedImageDto[]>([]);
  const [busy, setBusy] = useState(false);
  const [msg, setMsg] = useState("");
  const [configured, setConfigured] = useState(true);
  const [preview, setPreview] = useState<GeneratedImageDto | null>(null);

  function load() {
    api.images().then(setGallery).catch(() => {});
  }
  useEffect(() => {
    load();
    api.imageConfig().then((c) => setConfigured(c.configured)).catch(() => {});
  }, []);

  async function generate() {
    if (!prompt.trim()) { setMsg("Escribe una descripción."); return; }
    if (mode === "edit" && refs.length === 0) { setMsg("Sube al menos una imagen de referencia."); return; }
    setBusy(true); setMsg("");
    try {
      if (mode === "edit") {
        const form = new FormData();
        form.append("prompt", prompt);
        form.append("aspect_ratio", aspect);
        form.append("variants", String(variants));
        refs.slice(0, 4).forEach((f) => form.append("files", f));
        await api.editImages(form);
      } else {
        await api.generateImages({ prompt, aspect_ratio: aspect, variants });
      }
      setMsg("Listo.");
      setRefs([]);
      load();
    } catch (e) {
      setMsg(e instanceof Error ? e.message : "Error al generar");
    } finally {
      setBusy(false);
    }
  }
  async function remove(id: string) {
    await api.deleteImage(id);
    setGallery((g) => g.filter((x) => x.id !== id));
  }

  async function downloadImage(img: GeneratedImageDto) {
    try {
      const url = img.has_data ? await api.imageBlob(img.id) : img.source_url;
      const a = document.createElement("a");
      a.href = url;
      a.download = `maestroai-${img.id}.png`;
      document.body.appendChild(a);
      a.click();
      a.remove();
      if (img.has_data) setTimeout(() => URL.revokeObjectURL(url), 10000);
    } catch { /* noop */ }
  }

  return (
    <Shell>
      <PageHeader title="Generar imágenes" subtitle="Texto a imagen (compatible OpenAI). El prompt se redacta de PII antes de salir; las imágenes quedan en tu galería por área y auditadas." help="imagenes" />

      {!configured && (
        <div className="mb-4 rounded-xl border border-amber-300 bg-amber-50 px-4 py-3 text-sm text-amber-800">
          No hay proveedor de imágenes configurado. Configura el <b>Abierto (NaN)</b> en
          <b> Admin → Modelos y conectores</b> con una <b>key de tier <i>inference</i></b>
          (las <i>community</i> no pueden generar imágenes). Modelo: <code>flux-2-klein</code>.
        </div>
      )}

      <div className="grid grid-cols-1 gap-6 lg:grid-cols-[360px_1fr]">
        {/* Controls */}
        <div className="rounded-2xl border border-slate-200 bg-white p-5">
          <div className="mb-3 flex gap-2">
            <button onClick={() => setMode("generate")}
              className={`flex-1 rounded-lg border px-3 py-2 text-sm ${mode === "generate" ? "border-violet-500 bg-violet-50 font-semibold text-violet-700" : "border-slate-300 text-slate-600"}`}>Texto → imagen</button>
            <button onClick={() => setMode("edit")}
              className={`flex-1 rounded-lg border px-3 py-2 text-sm ${mode === "edit" ? "border-violet-500 bg-violet-50 font-semibold text-violet-700" : "border-slate-300 text-slate-600"}`}>Editar (imagen → imagen)</button>
          </div>

          {mode === "edit" && (
            <div className="mb-3">
              <label className="text-xs font-semibold uppercase tracking-wide text-slate-500">Imágenes de referencia (hasta 4)</label>
              <input type="file" accept="image/png,image/jpeg,image/webp" multiple
                onChange={(e) => setRefs(Array.from(e.target.files || []).slice(0, 4))}
                className="mt-1 block w-full text-xs text-slate-600 file:mr-3 file:rounded-md file:border-0 file:bg-violet-600 file:px-3 file:py-1.5 file:text-white" />
              {refs.length > 0 && <div className="mt-1 text-[11px] text-slate-500">{refs.length} imagen(es): {refs.map((f) => f.name).join(", ")}</div>}
            </div>
          )}

          <label className="text-xs font-semibold uppercase tracking-wide text-slate-500">{mode === "edit" ? "Edición a aplicar" : "Prompt"}</label>
          <textarea value={prompt} onChange={(e) => setPrompt(e.target.value)} rows={4}
            placeholder={mode === "edit" ? "Convierte la escena en invierno con nieve" : "Un centro de datos futurista en Marte al atardecer, luz cinematográfica"}
            className="mt-1 w-full rounded-lg border border-slate-300 px-3 py-2 text-sm" />

          <div className="mt-4 text-xs font-semibold uppercase tracking-wide text-slate-500">Relación de aspecto</div>
          <div className="mt-1 flex gap-2">
            {ASPECTS.map((a) => (
              <button key={a} onClick={() => setAspect(a)}
                className={`flex-1 rounded-lg border px-3 py-2 text-sm ${aspect === a ? "border-violet-500 bg-violet-50 font-semibold text-violet-700" : "border-slate-300 text-slate-600"}`}>{a}</button>
            ))}
          </div>

          <div className="mt-4 text-xs font-semibold uppercase tracking-wide text-slate-500">Variantes</div>
          <div className="mt-1 flex gap-2">
            {VARIANTS.map((v) => (
              <button key={v} onClick={() => setVariants(v)}
                className={`flex-1 rounded-lg border px-3 py-2 text-sm ${variants === v ? "border-violet-500 bg-violet-50 font-semibold text-violet-700" : "border-slate-300 text-slate-600"}`}>{v}×</button>
            ))}
          </div>

          <button onClick={generate} disabled={busy}
            className="mt-5 flex w-full items-center justify-center gap-2 rounded-lg bg-violet-600 px-4 py-2.5 text-sm font-semibold text-white disabled:opacity-50">
            {mode === "edit" ? <Wand2 className="h-4 w-4" /> : <Sparkles className="h-4 w-4" />}
            {busy ? (mode === "edit" ? "Editando…" : "Generando…") : (mode === "edit" ? "Editar" : "Generar")}
          </button>
          {msg && <div className="mt-2 text-xs text-slate-500">{msg}</div>}
        </div>

        {/* Gallery */}
        <div className="rounded-2xl border border-slate-200 bg-white p-5">
          <div className="mb-3 text-xs font-semibold uppercase tracking-wide text-slate-500">Tu galería</div>
          {gallery.length === 0 ? (
            <div className="flex h-64 flex-col items-center justify-center text-slate-400">
              <ImageIcon className="mb-2 h-8 w-8" />
              <span className="text-sm">Tus imágenes generadas aparecerán aquí.</span>
            </div>
          ) : (
            <div className="grid grid-cols-2 gap-3 sm:grid-cols-3">
              {gallery.map((img) => (
                <div key={img.id} className="group relative overflow-hidden rounded-xl border border-slate-200">
                  <button type="button" onClick={() => setPreview(img)} title="Ver en grande"
                    className="block w-full cursor-zoom-in">
                    <AuthImage id={img.id} alt={img.prompt} hasData={img.has_data}
                      fallbackUrl={img.source_url} className="aspect-square w-full object-cover" />
                  </button>
                  <button onClick={() => remove(img.id)}
                    className="absolute right-1.5 top-1.5 rounded-md bg-white/90 p-1 text-slate-500 opacity-0 transition group-hover:opacity-100 hover:text-red-600">
                    <Trash2 className="h-4 w-4" />
                  </button>
                  <div className="truncate px-2 py-1 text-[11px] text-slate-500" title={img.prompt}>{img.prompt}</div>
                </div>
              ))}
            </div>
          )}
        </div>
      </div>

      {preview && (
        <div onClick={() => setPreview(null)}
          className="fixed inset-0 z-[60] flex flex-col items-center justify-center bg-black/80 p-4">
          <button onClick={() => setPreview(null)} aria-label="Cerrar"
            className="absolute right-4 top-4 rounded-full bg-white/10 p-2 text-white hover:bg-white/20">
            <X className="h-5 w-5" />
          </button>
          <div onClick={(e) => e.stopPropagation()} className="flex max-h-[88vh] max-w-[92vw] flex-col items-center">
            <AuthImage id={preview.id} alt={preview.prompt} hasData={preview.has_data}
              fallbackUrl={preview.source_url} className="max-h-[80vh] max-w-[92vw] rounded-lg object-contain" />
            <div className="mt-3 flex items-center gap-3">
              <span className="max-w-[60vw] truncate text-sm text-white/80">{preview.prompt}</span>
              <button onClick={() => downloadImage(preview)}
                className="rounded-lg bg-white/15 px-3 py-1.5 text-sm font-semibold text-white hover:bg-white/25">Descargar</button>
            </div>
          </div>
        </div>
      )}
    </Shell>
  );
}
