import type { ModelRoute, Sensitivity } from "@shared/types";
import { Cloud, Lock, Server, ShieldAlert, ShieldCheck } from "lucide-react";

const ROUTE_META: Record<ModelRoute, { label: string; cls: string; icon: typeof Lock }> = {
  local: { label: "Local / self-hosted", cls: "bg-emerald-100 text-emerald-700 border-emerald-200", icon: Lock },
  vpc: { label: "VPC privada", cls: "bg-blue-100 text-blue-700 border-blue-200", icon: Server },
  open: { label: "Modelo abierto", cls: "bg-amber-100 text-amber-700 border-amber-200", icon: Cloud },
  premium: { label: "Premium externo", cls: "bg-violet-100 text-violet-700 border-violet-200", icon: Cloud },
  blocked: { label: "Bloqueado", cls: "bg-red-100 text-red-700 border-red-200", icon: ShieldAlert },
};

const SENS_META: Record<Sensitivity, { label: string; cls: string }> = {
  public: { label: "Público", cls: "bg-slate-100 text-slate-600 border-slate-200" },
  internal: { label: "Interno", cls: "bg-sky-100 text-sky-700 border-sky-200" },
  confidential: { label: "Confidencial", cls: "bg-amber-100 text-amber-700 border-amber-200" },
  restricted: { label: "Restringido", cls: "bg-red-100 text-red-700 border-red-200" },
};

export function PrivacyBadge({ route }: { route: ModelRoute }) {
  const m = ROUTE_META[route];
  const Icon = m.icon;
  return (
    <span className={`inline-flex items-center gap-1 rounded-full border px-2 py-0.5 text-xs font-semibold ${m.cls}`}>
      <Icon className="h-3 w-3" /> {m.label}
    </span>
  );
}

export function SensitivityBadge({ level }: { level: Sensitivity }) {
  const m = SENS_META[level];
  return (
    <span className={`inline-flex items-center gap-1 rounded-full border px-2 py-0.5 text-xs font-semibold ${m.cls}`}>
      <ShieldCheck className="h-3 w-3" /> {m.label}
    </span>
  );
}
