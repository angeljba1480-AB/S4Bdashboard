"use client";

import { api, clearToken } from "@/lib/api";
import type { Me } from "@shared/types";
import {
  Activity,
  Bot,
  FileText,
  IdCard,
  LayoutDashboard,
  LayoutGrid,
  LogOut,
  MapPin,
  MessageSquare,
  Rocket,
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
  {
    group: "GENERAL",
    items: [
      { href: "/dashboard", label: "Resumen", icon: LayoutDashboard },
      { href: "/operations", label: "Operación", icon: Activity },
    ],
  },
  {
    group: "PLATAFORMA",
    items: [
      { href: "/recipes", label: "Casos de uso", icon: Sparkles },
      { href: "/dashboards", label: "Tableros", icon: LayoutGrid },
      { href: "/regional", label: "Trámites y casos", icon: MapPin },
      { href: "/apps", label: "App Studio", icon: Rocket },
      { href: "/agents", label: "Agentes", icon: Bot },
      { href: "/documents", label: "Documentos", icon: FileText },
      { href: "/chat", label: "Chat con fuentes", icon: MessageSquare },
      { href: "/workflows", label: "Workflows", icon: Workflow },
    ],
  },
  {
    group: "GOBIERNO",
    items: [
      { href: "/account", label: "Mi cuenta", icon: IdCard },
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

  const brand = me?.brand_color || "#7c3aed";
  const brandName = me?.brand_name || "Private AI";
  const tagline = me?.brand_tagline || "Gateway + Agentes";

  return (
    <div className="flex min-h-screen bg-slate-50" style={{ ["--brand" as string]: brand }}>
      <aside className="flex w-64 flex-shrink-0 flex-col border-r border-slate-200 bg-white">
        <div className="flex items-center gap-2.5 border-b border-slate-200 px-5 py-5">
          {me?.brand_logo_url ? (
            // eslint-disable-next-line @next/next/no-img-element
            <img src={me.brand_logo_url} alt={brandName} className="h-9 w-9 rounded-lg object-contain" />
          ) : (
            <div
              className="flex h-9 w-9 items-center justify-center rounded-lg"
              style={{ background: `linear-gradient(135deg, ${brand}, #4f46e5)` }}
            >
              <Shield className="h-5 w-5 text-white" />
            </div>
          )}
          <div>
            <div className="text-sm font-extrabold text-slate-900">{brandName}</div>
            <div className="text-[11px] text-slate-400">{tagline}</div>
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
                    style={active ? { background: `${brand}14`, color: brand } : undefined}
                    className={`mb-0.5 flex items-center gap-2.5 rounded-lg px-3 py-2 text-sm font-medium transition ${
                      active ? "" : "text-slate-600 hover:bg-slate-100"
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
