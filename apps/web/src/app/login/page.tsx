"use client";

import { api } from "@/lib/api";
import { Shield } from "lucide-react";
import { useRouter } from "next/navigation";
import { useEffect, useState } from "react";

export default function LoginPage() {
  const router = useRouter();
  const [email, setEmail] = useState("admin@maestroai.mx");
  const [password, setPassword] = useState("demo1234");
  const [error, setError] = useState("");
  const [loading, setLoading] = useState(false);
  const [sso, setSso] = useState<{ enabled: boolean; authorize_url?: string }>({ enabled: false });

  useEffect(() => {
    api.ssoConfig().then(setSso).catch(() => {});
  }, []);

  async function submit(e: React.FormEvent) {
    e.preventDefault();
    setError("");
    setLoading(true);
    try {
      await api.login(email, password);
      router.push("/dashboard");
    } catch (err) {
      setError(err instanceof Error ? err.message : "Error de autenticación");
    } finally {
      setLoading(false);
    }
  }

  return (
    <div className="flex min-h-screen items-center justify-center bg-gradient-to-br from-slate-100 to-indigo-50 px-4">
      <div className="w-full max-w-md">
        <div className="mb-6 flex items-center gap-3">
          <div className="flex h-11 w-11 items-center justify-center rounded-xl bg-gradient-to-br from-violet-600 to-indigo-600">
            <Shield className="h-6 w-6 text-white" />
          </div>
          <div>
            <div className="text-lg font-extrabold text-slate-900">MaestroAI</div>
            <div className="text-sm text-slate-500">Agentes y casos para LATAM, sin perder control de tus datos</div>
          </div>
        </div>
        <form onSubmit={submit} className="rounded-2xl border border-slate-200 bg-white p-7 shadow-sm">
          <h1 className="mb-1 text-xl font-bold text-slate-900">Iniciar sesión</h1>
          <p className="mb-5 text-sm text-slate-500">Acceso por empresa (multi-tenant).</p>

          <label className="mb-1 block text-sm font-medium text-slate-700">Correo</label>
          <input
            value={email}
            onChange={(e) => setEmail(e.target.value)}
            className="mb-4 w-full rounded-lg border border-slate-300 px-3 py-2 text-sm focus:border-violet-500 focus:outline-none"
            type="email"
          />
          <label className="mb-1 block text-sm font-medium text-slate-700">Contraseña</label>
          <input
            value={password}
            onChange={(e) => setPassword(e.target.value)}
            className="mb-4 w-full rounded-lg border border-slate-300 px-3 py-2 text-sm focus:border-violet-500 focus:outline-none"
            type="password"
          />
          {error && <div className="mb-4 rounded-lg bg-red-50 px-3 py-2 text-sm text-red-600">{error}</div>}
          <button
            disabled={loading}
            className="w-full rounded-lg bg-violet-600 py-2.5 text-sm font-semibold text-white hover:bg-violet-700 disabled:opacity-50"
          >
            {loading ? "Entrando…" : "Entrar"}
          </button>
          {sso.enabled && sso.authorize_url && (
            <a
              href={sso.authorize_url}
              className="mt-3 block w-full rounded-lg border border-slate-300 py-2.5 text-center text-sm font-semibold text-slate-700 hover:bg-slate-50"
            >
              Entrar con SSO (OIDC)
            </a>
          )}
          <div className="mt-4 rounded-lg bg-slate-50 px-3 py-2 text-xs text-slate-500">
            Demo: <b>admin@maestroai.mx</b> · <b>demo1234</b> (también user@ / security@)
          </div>
        </form>
      </div>
    </div>
  );
}
