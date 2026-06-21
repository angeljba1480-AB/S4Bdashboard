"use client";

import { PageHeader, Shell } from "@/components/Shell";
import { api } from "@/lib/api";
import type { AppProject } from "@shared/types";
import { CheckCircle2, Rocket } from "lucide-react";
import { useEffect, useState } from "react";

export default function AppStudioPage() {
  const [apps, setApps] = useState<AppProject[]>([]);
  const [name, setName] = useState("");
  const [description, setDescription] = useState("");
  const [busy, setBusy] = useState(false);
  const [active, setActive] = useState<AppProject | null>(null);
  const [checkout, setCheckout] = useState<{ amount: number; currency: string } | null>(null);
  const [error, setError] = useState("");

  function load() {
    api.apps().then(setApps).catch(() => {});
  }
  useEffect(load, []);

  async function build() {
    if (!name.trim()) return;
    setBusy(true);
    setError("");
    try {
      const app = await api.createApp({ name, description });
      setActive(app);
      setName("");
      setDescription("");
      load();
    } catch (e) {
      setError(e instanceof Error ? e.message : "Error");
    } finally {
      setBusy(false);
    }
  }

  async function deploy(app: AppProject) {
    setBusy(true);
    setError("");
    try {
      const res = await api.deployApp(app.id);
      if (res.payment_required) {
        setActive(app);
        setCheckout(res.checkout ?? null);
      } else if (res.app) {
        setActive(res.app);
        setCheckout(null);
        load();
      }
    } catch (e) {
      setError(e instanceof Error ? e.message : "Error");
    } finally {
      setBusy(false);
    }
  }

  async function payAndDeploy(app: AppProject) {
    setBusy(true);
    try {
      await api.confirmCheckout(app.id);
      const res = await api.deployApp(app.id);
      if (res.app) setActive(res.app);
      setCheckout(null);
      load();
    } finally {
      setBusy(false);
    }
  }

  return (
    <Shell>
      <PageHeader
        title="App Studio"
        subtitle="Construye tu app o automatización con IA en tus herramientas. Publicar a producción tiene costo."
      />
      <div className="p-8">
        {error && <div className="mb-4 rounded-lg bg-red-50 px-4 py-2 text-sm text-red-600">{error}</div>}

        <div className="grid gap-6 lg:grid-cols-2">
          {/* Builder */}
          <div className="rounded-2xl border border-slate-200 bg-white p-5">
            <h2 className="mb-1 font-semibold text-slate-800">Nueva app</h2>
            <p className="mb-4 text-sm text-slate-500">Describe qué quieres y la IA arma el plan. Construir es gratis.</p>
            <input
              value={name}
              onChange={(e) => setName(e.target.value)}
              placeholder="Nombre (ej. Citas Barbería)"
              className="mb-2 w-full rounded-lg border border-slate-300 px-3 py-2 text-sm"
            />
            <textarea
              value={description}
              onChange={(e) => setDescription(e.target.value)}
              placeholder="¿Qué debe hacer? (ej. agenda de citas con recordatorios por WhatsApp)"
              rows={3}
              className="mb-3 w-full rounded-lg border border-slate-300 px-3 py-2 text-sm"
            />
            <button
              onClick={build}
              disabled={busy}
              className="rounded-lg bg-violet-600 px-4 py-2 text-sm font-semibold text-white disabled:opacity-50"
            >
              {busy ? "Construyendo…" : "Construir con IA"}
            </button>
          </div>

          {/* Result / spec */}
          <div className="rounded-2xl border border-slate-200 bg-white p-5">
            <h2 className="mb-1 font-semibold text-slate-800">Plan de la app</h2>
            {!active ? (
              <p className="text-sm text-slate-400">Construye una app para ver su plan aquí.</p>
            ) : (
              <>
                <div className="mb-2 flex items-center gap-2">
                  <span className="font-medium text-slate-700">{active.name}</span>
                  {active.status === "deployed" ? (
                    <span className="flex items-center gap-1 rounded-full bg-emerald-100 px-2 py-0.5 text-xs text-emerald-700">
                      <CheckCircle2 className="h-3.5 w-3.5" /> En producción
                    </span>
                  ) : (
                    <span className="rounded-full bg-slate-100 px-2 py-0.5 text-xs text-slate-500">Construida</span>
                  )}
                </div>
                <pre className="max-h-60 overflow-auto whitespace-pre-wrap rounded-lg bg-slate-50 p-3 text-xs text-slate-600">
                  {active.spec || "—"}
                </pre>

                {checkout && active.status !== "deployed" ? (
                  <div className="mt-3 rounded-lg border border-amber-200 bg-amber-50 p-3">
                    <div className="text-sm font-semibold text-amber-800">Publicar a producción</div>
                    <p className="mt-1 text-sm text-amber-700">
                      Costo: {checkout.amount} {checkout.currency}. Al confirmar, tu app queda en línea.
                    </p>
                    <button
                      onClick={() => payAndDeploy(active)}
                      disabled={busy}
                      className="mt-2 rounded-lg bg-amber-600 px-4 py-2 text-sm font-semibold text-white disabled:opacity-50"
                    >
                      Pagar y publicar
                    </button>
                  </div>
                ) : active.status === "deployed" ? (
                  <div className="mt-3 text-sm text-emerald-700">🔗 {active.deploy_url}</div>
                ) : (
                  <button
                    onClick={() => deploy(active)}
                    disabled={busy}
                    className="mt-3 inline-flex items-center gap-1.5 rounded-lg bg-slate-900 px-4 py-2 text-sm font-semibold text-white disabled:opacity-50"
                  >
                    <Rocket className="h-4 w-4" /> Publicar a producción
                  </button>
                )}
              </>
            )}
          </div>
        </div>

        {/* My apps */}
        {apps.length > 0 && (
          <div className="mt-6 rounded-2xl border border-slate-200 bg-white p-5">
            <h2 className="mb-3 font-semibold text-slate-800">Mis apps</h2>
            <div className="space-y-2">
              {apps.map((a) => (
                <div key={a.id} className="flex items-center justify-between rounded-lg border border-slate-200 p-3">
                  <div>
                    <div className="text-sm font-medium text-slate-800">{a.name}</div>
                    <div className="text-xs text-slate-400">{a.description}</div>
                  </div>
                  <div className="flex items-center gap-2">
                    <span className={`rounded-full px-2 py-0.5 text-xs ${a.status === "deployed" ? "bg-emerald-100 text-emerald-700" : "bg-slate-100 text-slate-500"}`}>
                      {a.status === "deployed" ? "Producción" : "Construida"}
                    </span>
                    <button onClick={() => { setActive(a); setCheckout(null); }} className="text-xs font-semibold text-violet-700">
                      Ver
                    </button>
                  </div>
                </div>
              ))}
            </div>
          </div>
        )}
      </div>
    </Shell>
  );
}
