"use client";

import { PageHeader, Shell } from "@/components/Shell";
import { api, type GeneratedImageDto } from "@/lib/api";
import { ImageIcon, Sparkles, Trash2 } from "lucide-react";
import { useEffect, useState } from "react";

const ASPECTS = ["1:1", "16:9", "9:16"];
const VARIANTS = [1, 2, 3, 4];

export default function GeneratePage() {
  const [prompt, setPrompt] = useState("");
  const [aspect, setAspect] = useState("1:1");
  const [variants, setVariants] = useState(1);
  const [gallery, setGallery] = useState<GeneratedImageDto[]>([]);
  const [busy, setBusy] = useState(false);
  const [msg, setMsg] = useState("");
  const [configured, setConfigured] = useState(true);

  function load() {
    api.images().then(setGallery).catch(() => {});
  }
  useEffect(() => {
    load();
    api.imageConfig().then((c) => setConfigured(c.configured)).catch(() => {});
  }, []);

  async function generate() {
    if (!prompt.trim()) { setMsg("Escribe una descripción."); return; }
    setBusy(true); setMsg("");
    try {
      await api.generateImages({ prompt, aspect_ratio: aspect, variants });
      setMsg("Listo.");
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

  return (
    <Shell>
      <PageHeader title="Generar imágenes" subtitle="Texto a imagen con FLUX (NaN). El prompt se redacta de PII antes de salir; las imágenes quedan en tu galería por área y auditadas." />

      {!configured && (
        <div className="mb-4 rounded-xl border border-amber-300 bg-amber-50 px-4 py-3 text-sm text-amber-800">
          No hay proveedor de imágenes configurado. En <b>Admin → Modelos externos</b> configura el proveedor
          <b> Abierto</b> (NaN) con su Base URL, modelo y API key, y pulsa <b>Probar conexión</b>.
        </div>
      )}

      <div className="grid grid-cols-1 gap-6 lg:grid-cols-[360px_1fr]">
        {/* Controls */}
        <div className="rounded-2xl border border-slate-200 bg-white p-5">
          <label className="text-xs font-semibold uppercase tracking-wide text-slate-500">Prompt</label>
          <textarea value={prompt} onChange={(e) => setPrompt(e.target.value)} rows={4}
            placeholder="Un centro de datos futurista en Marte al atardecer, luz cinematográfica"
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
            <Sparkles className="h-4 w-4" /> {busy ? "Generando…" : "Generar"}
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
                  {img.has_data ? (
                    /* eslint-disable-next-line @next/next/no-img-element */
                    <img src={api.imageDataUrl(img.id)} alt={img.prompt} className="aspect-square w-full object-cover" />
                  ) : (
                    <div className="flex aspect-square items-center justify-center bg-slate-100 text-xs text-slate-400">sin copia</div>
                  )}
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
    </Shell>
  );
}
