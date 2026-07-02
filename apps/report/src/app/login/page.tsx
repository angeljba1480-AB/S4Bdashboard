"use client";

import { Lock } from "lucide-react";
import { useState } from "react";

export default function LoginPage() {
  const [password, setPassword] = useState("");
  const [error, setError] = useState("");
  const [loading, setLoading] = useState(false);

  async function submit(e: React.FormEvent) {
    e.preventDefault();
    setLoading(true);
    setError("");
    try {
      const r = await fetch("/api/login", {
        method: "POST",
        headers: { "Content-Type": "application/json" },
        body: JSON.stringify({ password }),
      });
      if (r.ok) {
        const params = new URLSearchParams(window.location.search);
        window.location.href = params.get("next") || "/";
        return;
      }
      const j = await r.json().catch(() => ({}));
      setError(j.error || "No se pudo iniciar sesión");
    } catch {
      setError("Error de red");
    } finally {
      setLoading(false);
    }
  }

  return (
    <div className="flex min-h-screen items-center justify-center bg-slate-100 p-4">
      <div className="w-full max-w-sm rounded-2xl border border-slate-200 bg-white p-8 shadow-sm">
        <div className="mb-5 flex flex-col items-center text-center">
          <div className="mb-3 flex h-12 w-12 items-center justify-center rounded-xl bg-gradient-to-br from-violet-600 to-indigo-600">
            <Lock className="h-6 w-6 text-white" />
          </div>
          <h1 className="text-lg font-extrabold text-slate-900">Tablero Financiero</h1>
          <p className="mt-1 text-sm text-slate-500">Acceso restringido · Silent4Business</p>
        </div>
        <form onSubmit={submit} className="space-y-3">
          <input
            type="password"
            autoFocus
            value={password}
            onChange={(e) => setPassword(e.target.value)}
            placeholder="Contraseña de acceso"
            className="w-full rounded-lg border border-slate-300 px-3 py-2.5 text-sm outline-none focus:border-violet-500 focus:ring-2 focus:ring-violet-100"
          />
          {error && <p className="text-sm text-red-600">{error}</p>}
          <button
            type="submit"
            disabled={loading || !password}
            className="w-full rounded-lg bg-violet-600 px-4 py-2.5 text-sm font-semibold text-white transition hover:bg-violet-700 disabled:opacity-50"
          >
            {loading ? "Verificando…" : "Entrar"}
          </button>
        </form>
        <p className="mt-4 text-center text-[11px] text-slate-400">
          La contraseña se valida en el servidor. Este reporte no está indexado.
        </p>
      </div>
    </div>
  );
}
