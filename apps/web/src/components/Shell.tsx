"use client";

import { api, clearToken } from "@/lib/api";
import { HelpButton } from "@/components/HelpButton";
import { GlobalSearch } from "@/components/GlobalSearch";
import { NotificationBell } from "@/components/NotificationBell";
import type { Me } from "@shared/types";
import {
  Activity,
  Bell,
  Bot,
  Brain,
  Building2,
  ChevronDown,
  ChevronRight,
  FileText,
  Cpu,
  Factory,
  FolderKanban,
  GitBranch,
  HelpCircle,
  IdCard,
  ImagePlus,
  LayoutDashboard,
  LayoutGrid,
  LogOut,
  MailCheck,
  MapPin,
  MessageSquare,
  NotebookPen,
  Rocket,
  Search as SearchIcon,
  Wand2,
  Plug,
  Settings,
  Shield,
  ShieldAlert,
  ShieldCheck,
  Sparkles,
  Workflow,
  Zap,
} from "lucide-react";
import Link from "next/link";
import { usePathname, useRouter } from "next/navigation";
import { useEffect, useState } from "react";

// Sidebar recortado y unificado (ver docs/DISENO-PROCESOS-NEGOCIO.md §12). Lo esencial
// vive en PLATAFORMA; lo fusionado/en-demostración se agrupa en AVANZADO (colapsable, para
// no borrar rutas ni perder acceso). Nada se elimina: solo se ordena la navegación.
const NAV = [
  {
    group: "GENERAL",
    items: [
      { href: "/dashboard", label: "Resumen", icon: LayoutDashboard },
      { href: "/search", label: "Buscar", icon: SearchIcon },
      { href: "/operations", label: "Operación", icon: Activity },
    ],
  },
  {
    group: "PLATAFORMA",
    items: [
      { href: "/procesos", label: "Mapa de Procesos", icon: Workflow },
      { href: "/recipes", label: "Casos de uso", icon: Sparkles },
      { href: "/automations", label: "Automatizaciones", icon: Zap },
      { href: "/agents", label: "Agentes", icon: Bot },
      { href: "/integrations", label: "Integraciones", icon: Plug },
      { href: "/documents", label: "Documentos", icon: FileText },
      { href: "/chat", label: "Chat con fuentes", icon: MessageSquare },
      { href: "/notebooks", label: "Notebooks", icon: NotebookPen },
      { href: "/generate", label: "Generar imágenes", icon: ImagePlus },
      { href: "/dashboards", label: "Tableros", icon: LayoutGrid },
      { href: "/regional", label: "Trámites y casos", icon: MapPin },
      { href: "/kedb", label: "Errores conocidos (KEDB)", icon: ShieldAlert },
    ],
  },
  {
    group: "AVANZADO",
    collapsible: true,   // colapsado por defecto: módulos fusionados o en demostración
    items: [
      { href: "/flowcharts", label: "Flujogramas", icon: GitBranch },
      { href: "/workflows", label: "Workflows", icon: Workflow },
      { href: "/actions", label: "Acciones", icon: Wand2 },
      { href: "/runbooks", label: "Runbooks", icon: Factory },
      { href: "/espacios", label: "Espacios", icon: FolderKanban },
      { href: "/mail-digest", label: "Resumen de correo", icon: MailCheck },
      { href: "/memory", label: "Memoria", icon: Brain },
      { href: "/apps", label: "App Studio", icon: Rocket },
      { href: "/finetune", label: "Fine-tuning", icon: Cpu },
    ],
  },
  {
    group: "GOBIERNO",
    items: [
      { href: "/company", label: "Configuración", icon: Building2 },
      { href: "/alerts", label: "Alertas", icon: Bell },
      { href: "/account", label: "Mi cuenta", icon: IdCard },
      { href: "/audit", label: "Auditoría", icon: ShieldCheck },
      { href: "/admin", label: "Admin", icon: Settings },
      { href: "/help", label: "Ayuda", icon: HelpCircle },
    ],
  },
];

export function Shell({ children }: { children: React.ReactNode }) {
  const pathname = usePathname();
  const router = useRouter();
  const [me, setMe] = useState<Me | null>(null);
  const [logoError, setLogoError] = useState(false);
  const [showAdvanced, setShowAdvanced] = useState(false);

  useEffect(() => {
    api.me().then(setMe).catch(() => router.push("/login"));
  }, [router]);

  function logout() {
    clearToken();
    router.push("/login");
  }

  const brand = me?.brand_color || "#7c3aed";
  const brandName = me?.brand_name || "MaestroAI";
  const tagline = me?.brand_tagline || "Agentes y casos para LATAM";

  return (
    <div className="flex min-h-screen bg-slate-50" style={{ ["--brand" as string]: brand }}>
      <aside className="flex w-64 flex-shrink-0 flex-col border-r border-slate-200 bg-white">
        <div className="flex items-center gap-2.5 border-b border-slate-200 px-5 py-5">
          {me?.brand_logo_url && !logoError ? (
            // eslint-disable-next-line @next/next/no-img-element
            <img src={me.brand_logo_url} alt={brandName} onError={() => setLogoError(true)}
              className="h-9 w-9 rounded-lg object-contain" />
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
          {NAV.map((g) => {
            const collapsible = "collapsible" in g && g.collapsible;
            // Un grupo colapsable se abre solo si contiene la ruta activa, o si el usuario lo abrió.
            const hasActive = g.items.some((it) => it.href === pathname);
            const open = !collapsible || showAdvanced || hasActive;
            return (
              <div key={g.group}>
                {collapsible ? (
                  <button onClick={() => setShowAdvanced((v) => !v)}
                    className="flex w-full items-center gap-1 px-2 pb-2 text-[10px] font-bold uppercase tracking-wider text-slate-400 hover:text-slate-600">
                    {open ? <ChevronDown className="h-3 w-3" /> : <ChevronRight className="h-3 w-3" />} {g.group}
                  </button>
                ) : (
                  <div className="px-2 pb-2 text-[10px] font-bold uppercase tracking-wider text-slate-400">{g.group}</div>
                )}
                {open && g.items
                  .filter((it) => it.href !== "/regional" || me?.gov_enabled)
                  .filter((it) => it.href !== "/kedb" || me?.kedb_enabled)
                  .map((it) => {
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
            );
          })}
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
      <main className="flex-1 overflow-auto">
        <GlobalSearch />
        <NotificationBell />
        {me?.demo_mode && (
          <div className="flex items-start gap-2 border-b border-amber-200 bg-amber-50 px-8 py-2.5 text-sm text-amber-800">
            <ShieldAlert className="mt-0.5 h-4 w-4 shrink-0" />
            <span>
              <b>Modo demostración.</b> No hay un proveedor de IA configurado, así que las
              respuestas de IA (chat, casos de uso, agentes) son <b>simuladas</b>. Un administrador
              puede conectar un modelo real en <a href="/admin" className="underline">Admin → Modelos</a>.
            </span>
          </div>
        )}
        {me && !me.demo_mode && me.embeddings_semantic === false && (
          <div className="flex items-start gap-2 border-b border-slate-200 bg-slate-50 px-8 py-2 text-xs text-slate-500">
            <ShieldAlert className="mt-0.5 h-3.5 w-3.5 shrink-0" />
            <span>
              La búsqueda en documentos usa <b>coincidencia léxica</b> (no semántica): configura un
              proveedor de embeddings en <a href="/admin" className="underline">Admin</a> para
              resultados por significado.
            </span>
          </div>
        )}
        {children}
      </main>
    </div>
  );
}

export function PageHeader({ title, subtitle, help }: { title: string; subtitle?: string; help?: string | string[] }) {
  const topics = help ? (Array.isArray(help) ? help : [help]) : [];
  return (
    <div className="border-b border-slate-200 bg-white px-8 py-5">
      <div className="flex items-start justify-between gap-4">
        <h1 className="text-xl font-bold text-slate-900">{title}</h1>
        {topics.length > 0 && <HelpButton topics={topics} />}
      </div>
      {subtitle && <p className="mt-0.5 text-sm text-slate-500">{subtitle}</p>}
    </div>
  );
}
