"use client";

import { PageHeader, Shell } from "@/components/Shell";
import { api } from "@/lib/api";
import { BadgeCheck, ShieldCheck, Users } from "lucide-react";
import { useEffect, useState } from "react";

type Account = Awaited<ReturnType<typeof api.account>>;

export default function AccountPage() {
  const [acc, setAcc] = useState<Account | null>(null);
  const [mfaOn, setMfaOn] = useState<boolean | null>(null);
  const [setup, setSetup] = useState<{ secret: string; otpauth_uri: string } | null>(null);
  const [code, setCode] = useState("");
  const [backup, setBackup] = useState<string[] | null>(null);
  const [mfaMsg, setMfaMsg] = useState("");

  useEffect(() => {
    api.account().then(setAcc).catch(() => {});
    api.me().then((m) => setMfaOn(m.mfa_enabled)).catch(() => {});
  }, []);

  async function startSetup() {
    setMfaMsg(""); setBackup(null);
    try { setSetup(await api.mfaSetup()); } catch (e) { setMfaMsg(e instanceof Error ? e.message : "Error"); }
  }
  async function verify() {
    setMfaMsg("");
    try {
      const r = await api.mfaVerify(code);
      setBackup(r.backup_codes); setSetup(null); setMfaOn(true); setCode("");
      setMfaMsg("MFA activado. Guarda tus códigos de respaldo.");
    } catch (e) { setMfaMsg(e instanceof Error ? e.message : "Código inválido"); }
  }
  async function disable() {
    setMfaMsg("");
    try { await api.mfaDisable(code); setMfaOn(false); setCode(""); setBackup(null); setMfaMsg("MFA desactivado."); }
    catch (e) { setMfaMsg(e instanceof Error ? e.message : "Código inválido"); }
  }

  if (!acc) {
    return (
      <Shell>
        <PageHeader title="Mi cuenta" subtitle="Tu licencia y las licencias de la empresa." />
        <div className="p-8 text-sm text-slate-400">Cargando…</div>
      </Shell>
    );
  }

  return (
    <Shell>
      <PageHeader title="Mi cuenta" subtitle="Tu licencia y las licencias de la empresa." />
      <div className="space-y-6 p-8">
        <div className="grid grid-cols-1 gap-6 lg:grid-cols-2">
          {/* User license */}
          <div className="rounded-2xl border border-slate-200 bg-white p-5">
            <div className="mb-3 flex items-center gap-2">
              <BadgeCheck className="h-5 w-5 text-violet-600" />
              <h2 className="font-semibold text-slate-800">Tu licencia</h2>
            </div>
            <div className="space-y-1 text-sm">
              <div className="flex justify-between"><span className="text-slate-500">Usuario</span><span className="font-medium text-slate-800">{acc.user.name}</span></div>
              <div className="flex justify-between"><span className="text-slate-500">Correo</span><span className="text-slate-700">{acc.user.email}</span></div>
              <div className="flex justify-between"><span className="text-slate-500">Tipo de licencia</span><span className="font-medium capitalize text-slate-800">{acc.license.type}</span></div>
              <div className="flex justify-between">
                <span className="text-slate-500">Estado</span>
                <span className={`rounded-full px-2 py-0.5 text-xs ${acc.license.status === "active" ? "bg-emerald-100 text-emerald-700" : "bg-slate-100 text-slate-500"}`}>
                  {acc.license.seat_assigned ? "Asiento activo" : "Sin asiento"}
                </span>
              </div>
            </div>
          </div>

          {/* Company licenses */}
          <div className="rounded-2xl border border-slate-200 bg-white p-5">
            <div className="mb-3 flex items-center gap-2">
              <Users className="h-5 w-5 text-blue-600" />
              <h2 className="font-semibold text-slate-800">Licencias de la empresa</h2>
            </div>
            <div className="mb-3 text-sm">
              <div className="flex justify-between"><span className="text-slate-500">Empresa</span><span className="font-medium text-slate-800">{acc.company.name}</span></div>
              <div className="flex justify-between"><span className="text-slate-500">Plan</span><span className="capitalize text-slate-700">{acc.company.plan}</span></div>
              <div className="flex justify-between">
                <span className="text-slate-500">Suscripción</span>
                <span className={`rounded-full px-2 py-0.5 text-xs ${acc.company.subscription_status === "active" ? "bg-emerald-100 text-emerald-700" : acc.company.subscription_status === "trial" ? "bg-amber-100 text-amber-700" : "bg-red-100 text-red-700"}`}>
                  {acc.company.subscription_status}
                </span>
              </div>
              <div className="flex justify-between"><span className="text-slate-500">Renovación</span><span className="text-slate-700">{acc.company.renews_at ?? "—"}</span></div>
            </div>
            <div className="rounded-xl bg-slate-50 p-3">
              <div className="flex items-end justify-between">
                <span className="text-sm text-slate-500">Asientos usados</span>
                <span className="text-2xl font-bold text-slate-900">{acc.company.seats_used}/{acc.company.seats_licensed}</span>
              </div>
              <div className="mt-2 h-2 overflow-hidden rounded-full bg-slate-200">
                <div className="h-full bg-violet-600"
                  style={{ width: `${acc.company.seats_licensed ? (acc.company.seats_used / acc.company.seats_licensed) * 100 : 0}%` }} />
              </div>
              <div className="mt-1 text-xs text-slate-400">{acc.company.seats_available} disponibles</div>
            </div>
          </div>
        </div>

        {/* MFA (segundo factor) */}
        <div className="rounded-2xl border border-slate-200 bg-white p-5">
          <div className="mb-3 flex items-center gap-2">
            <ShieldCheck className="h-5 w-5 text-emerald-600" />
            <h2 className="font-semibold text-slate-800">Seguridad · Verificación en dos pasos (MFA)</h2>
            {mfaOn !== null && (
              <span className={`ml-2 rounded-full px-2 py-0.5 text-xs ${mfaOn ? "bg-emerald-100 text-emerald-700" : "bg-slate-100 text-slate-500"}`}>
                {mfaOn ? "Activo" : "Inactivo"}
              </span>
            )}
          </div>
          <p className="mb-3 text-sm text-slate-500">
            Protege tu cuenta con una app de autenticación (Google Authenticator, Authy, 1Password…).
          </p>

          {mfaOn === false && !setup && (
            <button onClick={startSetup} className="rounded-lg bg-slate-900 px-4 py-2 text-sm font-semibold text-white">Activar MFA</button>
          )}

          {setup && (
            <div className="space-y-2 rounded-xl bg-slate-50 p-4 text-sm">
              <div className="text-slate-600">1. Agrega esta clave en tu app de autenticación:</div>
              <div className="font-mono text-xs break-all rounded bg-white p-2">{setup.secret}</div>
              <div className="text-[11px] text-slate-400 break-all">URI: {setup.otpauth_uri}</div>
              <div className="text-slate-600">2. Escribe el código de 6 dígitos que muestra la app:</div>
              <div className="flex gap-2">
                <input value={code} onChange={(e) => setCode(e.target.value)} placeholder="123456"
                  className="w-32 rounded-lg border border-slate-300 px-3 py-2 text-sm tracking-widest" />
                <button onClick={verify} className="rounded-lg bg-violet-600 px-4 py-2 text-sm font-semibold text-white">Verificar y activar</button>
              </div>
            </div>
          )}

          {backup && (
            <div className="mt-3 rounded-xl border border-amber-300 bg-amber-50 p-4">
              <div className="mb-2 text-sm font-semibold text-amber-800">Códigos de respaldo (guárdalos; se muestran una sola vez)</div>
              <div className="grid grid-cols-2 gap-1 font-mono text-sm text-amber-900 sm:grid-cols-4">
                {backup.map((c) => <span key={c}>{c}</span>)}
              </div>
            </div>
          )}

          {mfaOn === true && !setup && (
            <div className="flex items-center gap-2">
              <input value={code} onChange={(e) => setCode(e.target.value)} placeholder="Código para desactivar"
                className="w-44 rounded-lg border border-slate-300 px-3 py-2 text-sm" />
              <button onClick={disable} className="rounded-lg border border-red-300 px-4 py-2 text-sm font-semibold text-red-600 hover:bg-red-50">Desactivar MFA</button>
            </div>
          )}
          {mfaMsg && <div className="mt-2 text-xs text-slate-500">{mfaMsg}</div>}
        </div>

        <div className="rounded-2xl border border-slate-200 bg-white p-5">
          <h2 className="mb-3 font-semibold text-slate-800">Usuarios con licencia</h2>
          <table className="w-full text-sm">
            <thead className="border-b border-slate-200 text-xs uppercase text-slate-400">
              <tr><th className="py-2 text-left">Nombre</th><th className="text-left">Correo</th><th className="text-left">Rol</th><th className="text-left">Estado</th></tr>
            </thead>
            <tbody>
              {acc.licensed_users.map((u) => (
                <tr key={u.email} className="border-b border-slate-100">
                  <td className="py-2 text-slate-700">{u.name}</td>
                  <td className="text-slate-500">{u.email}</td>
                  <td className="capitalize text-slate-600">{u.role}</td>
                  <td><span className="rounded-full bg-emerald-100 px-2 py-0.5 text-xs text-emerald-700">{u.status}</span></td>
                </tr>
              ))}
            </tbody>
          </table>
        </div>
      </div>
    </Shell>
  );
}
