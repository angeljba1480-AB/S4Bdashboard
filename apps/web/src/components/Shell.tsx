"use client";

import { api, clearToken } from "@/lib/api";
import type { Me } from "@shared/types";
import {
  Bot,
  FileText,
  LayoutDashboard,
  LogOut,
  MessageSquare,
  Settings,
  Shield,
  ShieldCheck,
  Sparkles,
  Workflow,
} from "lucide-react";
import Link from "next/link";
import { usePathname, useRouter } from "next/navigation";
import { useEffect, useState } from "react";

const NAV = [
  { group: "GENERAL", items: [{ href: "/dashboard", label: "Resumen", icon: LayoutDashboard }] },
  {
    group: "PLATAFORMA",
    items: [
      { href: "/recipes", label: "Casos de uso", icon: Sparkles },
      { href: "/agents", label: "Agentes", icon: Bot },
      { href: "/documents", label: "Documentos", icon: FileText },
      { href: "/chat", label: "Chat con fuentes", icon: MessageSquare },
      { href: "/workflows", label: "Workflows", icon: Workflow },
    ],
  },
  {
    group: "GOBIERNO",
    items: [
      { href: "/audit", label: "Auditoría", icon: ShieldCheck },
      { href: "/admin", label: "Admin", icon: Settings },
    ],
  },
];

export function Shell({ children }: { children: React.ReactNode }) {
  const pathname = usePathname();
  const router = useRouter();
  const [me, setMe] = useState<Me | null>(null);

  useEffect(() => {
    api.me().then(setMe).catch(() => router.push("/login"));
  }, [router]);

  function logout() {
    clearToken();
    router.push("/login");
  }

  return (
    <div className="flex min-h-screen bg-slate-50">
      <aside className="flex w-64 flex-shrink-0 flex-col border-r border-slate-200 bg-white">
        <div className="flex items-center gap-2.5 border-b border-slate-200 px-5 py-5">
          <div className="flex h-9 w-9 items-center justify-center rounded-lg bg-gradient-to-br from-violet-600 to-indigo-600">
            <Shield className="h-5 w-5 text-white" />
          </div>
          <div>
            <div className="text-sm font-extrabold text-slate-900">Private AI</div>
            <div className="text-[11px] text-slate-400">Gateway + Agentes</div>
          </div>
        </div>
        <nav className="flex-1 space-y-6 px-3 py-5">
          {NAV.map((g) => (
            <div key={g.group}>
              <div className="px-2 pb-2 text-[10px] font-bold uppercase tracking-wider text-slate-400">
                {g.group}
              </div>
              {g.items.map((it) => {
                const Icon = it.icon;
                const active = pathname === it.href;
                return (
                  <Link
                    key={it.href}
                    href={it.href}
                    className={`mb-0.5 flex items-center gap-2.5 rounded-lg px-3 py-2 text-sm font-medium transition ${
                      active
                        ? "bg-violet-50 text-violet-700"
                        : "text-slate-600 hover:bg-slate-100"
                    }`}
                  >
                    <Icon className="h-4 w-4" /> {it.label}
                  </Link>
                );
              })}
            </div>
          ))}
        </nav>
        <div className="border-t border-slate-200 p-4">
          {me && (
            <div className="mb-3">
              <div className="text-sm font-semibold text-slate-800">{me.name}</div>
              <div className="text-xs text-slate-400">{me.tenant_name} · {me.role}</div>
            </div>
          )}
          <button
            onClick={logout}
            className="flex w-full items-center gap-2 rounded-lg px-3 py-2 text-sm text-slate-500 hover:bg-slate-100"
          >
            <LogOut className="h-4 w-4" /> Cerrar sesión
          </button>
        </div>
      </aside>
      <main className="flex-1 overflow-auto">{children}</main>
    </div>
  );
}

export function PageHeader({ title, subtitle }: { title: string; subtitle?: string }) {
  return (
    <div className="border-b border-slate-200 bg-white px-8 py-5">
      <h1 className="text-xl font-bold text-slate-900">{title}</h1>
      {subtitle && <p className="mt-0.5 text-sm text-slate-500">{subtitle}</p>}
    </div>
  );
}
