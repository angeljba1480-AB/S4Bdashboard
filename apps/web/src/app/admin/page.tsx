"use client";

import { PageHeader, Shell } from "@/components/Shell";
import { api } from "@/lib/api";
import { useEffect, useState } from "react";

export default function AdminPage() {
  const [routes, setRoutes] = useState<{ route: string; enabled: boolean; model: string; mode: string }[]>([]);
  const [users, setUsers] = useState<{ id: string; email: string; name: string; role: string; mfa_enabled: boolean }[]>([]);
  const [error, setError] = useState("");

  useEffect(() => {
    api.routes().then(setRoutes).catch((e) => setError(e.message));
    api.users().then(setUsers).catch(() => {});
  }, []);

  return (
    <Shell>
      <PageHeader title="Administración" subtitle="Usuarios, roles, modelos habilitados y rutas de privacidad." />
      <div className="space-y-6 p-8">
        {error && <div className="rounded-lg bg-red-50 px-4 py-2 text-sm text-red-600">{error}</div>}

        <div className="rounded-2xl border border-slate-200 bg-white p-5">
          <h2 className="mb-4 font-semibold text-slate-800">Rutas de modelo (router de privacidad)</h2>
          <div className="grid grid-cols-1 gap-3 sm:grid-cols-2 lg:grid-cols-4">
            {routes.map((r) => (
              <div key={r.route} className="rounded-xl border border-slate-200 p-4">
                <div className="text-sm font-semibold capitalize text-slate-800">{r.route}</div>
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
