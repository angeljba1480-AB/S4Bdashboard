"use client";

import { PageHeader, Shell } from "@/components/Shell";
import { api } from "@/lib/api";
import { useEffect, useState } from "react";

type Security = Awaited<ReturnType<typeof api.security>>;

export default function AdminPage() {
  const [routes, setRoutes] = useState<{ route: string; provider: string; enabled: boolean; model: string; mode: string }[]>([]);
  const [users, setUsers] = useState<{ id: string; email: string; name: string; role: string; mfa_enabled: boolean }[]>([]);
  const [security, setSecurity] = useState<Security | null>(null);
  const [error, setError] = useState("");

  useEffect(() => {
    api.routes().then(setRoutes).catch((e) => setError(e.message));
    api.users().then(setUsers).catch(() => {});
    api.security().then(setSecurity).catch(() => {});
  }, []);

  return (
    <Shell>
      <PageHeader title="Administración" subtitle="Usuarios, roles, modelos habilitados y rutas de privacidad." />
      <div className="space-y-6 p-8">
        {error && <div className="rounded-lg bg-red-50 px-4 py-2 text-sm text-red-600">{error}</div>}

        {security && (
          <div className="rounded-2xl border border-slate-200 bg-white p-5">
            <h2 className="mb-4 font-semibold text-slate-800">Postura de seguridad (Enterprise hardening)</h2>
            <div className="grid grid-cols-1 gap-3 sm:grid-cols-2 lg:grid-cols-4">
              <div className="rounded-xl border border-slate-200 p-4">
                <div className="text-xs uppercase tracking-wide text-slate-400">Cifrado en reposo</div>
                <div className="mt-1 font-semibold text-slate-800">
                  {security.encryption_at_rest.enabled ? security.encryption_at_rest.algo : "Desactivado"}
                </div>
                <div className="text-xs text-slate-400">KMS v{security.encryption_at_rest.kms_key_version}</div>
              </div>
              <div className="rounded-xl border border-slate-200 p-4">
                <div className="text-xs uppercase tracking-wide text-slate-400">Vector store</div>
                <div className="mt-1 font-semibold capitalize text-slate-800">{security.vector_store}</div>
              </div>
              <div className="rounded-xl border border-slate-200 p-4">
                <div className="text-xs uppercase tracking-wide text-slate-400">SSO / OIDC</div>
                <div className="mt-1 font-semibold text-slate-800">
                  {security.sso.enabled ? "Habilitado" : "Password"}
                </div>
                <div className="truncate text-xs text-slate-400">{security.sso.issuer ?? "—"}</div>
              </div>
              <div className="rounded-xl border border-slate-200 p-4">
                <div className="text-xs uppercase tracking-wide text-slate-400">Fallback de rutas</div>
                <div className="mt-1 font-semibold text-slate-800">{security.fallback_order.join(" → ")}</div>
              </div>
            </div>
          </div>
        )}

        <div className="rounded-2xl border border-slate-200 bg-white p-5">
          <h2 className="mb-4 font-semibold text-slate-800">Rutas de modelo (router de privacidad)</h2>
          <div className="grid grid-cols-1 gap-3 sm:grid-cols-2 lg:grid-cols-4">
            {routes.map((r) => (
              <div key={r.route} className="rounded-xl border border-slate-200 p-4">
                <div className="text-sm font-semibold capitalize text-slate-800">{r.route}</div>
                <div className="text-xs font-medium text-violet-600">{r.provider}</div>
                <div className="mt-1 text-xs text-slate-500">{r.model}</div>
                <span
                  className={`mt-2 inline-block rounded-full px-2 py-0.5 text-xs ${
                    r.mode === "real" ? "bg-emerald-100 text-emerald-700" : "bg-amber-100 text-amber-700"
                  }`}
                >
                  {r.mode === "real" ? "Proveedor real" : "Mock (configurar .env)"}
                </span>
              </div>
            ))}
          </div>
        </div>

        <div className="rounded-2xl border border-slate-200 bg-white p-5">
          <h2 className="mb-4 font-semibold text-slate-800">Usuarios del tenant</h2>
          <table className="w-full text-sm">
            <thead className="border-b border-slate-200 text-xs uppercase text-slate-400">
              <tr>
                <th className="py-2 text-left">Nombre</th>
                <th className="py-2 text-left">Correo</th>
                <th className="py-2 text-left">Rol</th>
                <th className="py-2 text-center">MFA</th>
              </tr>
            </thead>
            <tbody>
              {users.map((u) => (
                <tr key={u.id} className="border-b border-slate-100">
                  <td className="py-2 text-slate-700">{u.name}</td>
                  <td className="py-2 text-slate-500">{u.email}</td>
                  <td className="py-2 text-slate-500">{u.role}</td>
                  <td className="py-2 text-center">{u.mfa_enabled ? "✓" : "—"}</td>
                </tr>
              ))}
            </tbody>
          </table>
        </div>
      </div>
    </Shell>
  );
}
