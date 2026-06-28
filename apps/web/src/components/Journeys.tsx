"use client";

import { ArrowRight, ChevronDown, Compass } from "lucide-react";
import Link from "next/link";
import { useState } from "react";

type Step = { label: string; href: string; result: string };
type Journey = { key: string; title: string; subtitle: string; steps: Step[] };

// Recorridos por objetivo: cada paso lleva a su pestaña y dice DÓNDE se ve el resultado.
const JOURNEYS: Journey[] = [
  {
    key: "ventas",
    title: "1 · Atención y ventas",
    subtitle: "Del correo del cliente a la cotización enviada y con seguimiento.",
    steps: [
      { label: "Resumen de correo automatizado", href: "/mail-digest",
        result: "Resultado: pop-up en la campana 🔔, y/o tu correo y WhatsApp." },
      { label: "Caso «Cotización rápida»", href: "/recipes?category=operaciones",
        result: "Resultado: documento (descarga Word/PDF) + botón «Enviar a WhatsApp»." },
      { label: "Runbook «Cotización y seguimiento»", href: "/runbooks?sector=servicios",
        result: "Al instalarlo queda en Acciones; el agente lo ejecuta (lecturas al momento, escrituras con tu aprobación)." },
      { label: "Chat con fuentes", href: "/chat",
        result: "Resultado: respuesta citada en pantalla; puedes narrarla (voz) y guardar a Memoria." },
    ],
  },
  {
    key: "operacion",
    title: "2 · Operación y planta",
    subtitle: "Automatiza de áreas de servicio hasta producción.",
    steps: [
      { label: "Runbooks de manufactura/producción", href: "/runbooks?sector=manufactura",
        result: "Al instalar, se ejecuta desde Acciones (órdenes de trabajo, OEE, mantenimiento…)." },
      { label: "Conecta tus sistemas (ERP/SFTP/DB/Webhook)", href: "/integrations",
        result: "Resultado: los datos entran al repositorio + RAG y quedan buscables." },
      { label: "Documentos y Búsqueda global", href: "/search",
        result: "Resultado: encuentras todo (documentos, recetas, notebooks) en un solo lugar." },
    ],
  },
  {
    key: "contenido",
    title: "3 · Contenido y comunicación",
    subtitle: "Genera materiales y compártelos.",
    steps: [
      { label: "Generar imágenes", href: "/generate",
        result: "Resultado: galería; clic en una imagen la abre en grande y la descargas." },
      { label: "Casos que producen documentos", href: "/recipes?category=crecer",
        result: "Resultado: Word / PDF / PowerPoint / Excel + «Enviar a WhatsApp»." },
      { label: "Notebooks (fuentes → artefactos)", href: "/notebooks",
        result: "Resultado: resumen, FAQ, guía y briefing citados a partir de tus fuentes." },
    ],
  },
  {
    key: "automatizacion",
    title: "4 · Automatización y avisos",
    subtitle: "Que las cosas pasen solas y te enteres.",
    steps: [
      { label: "Workflows", href: "/workflows",
        result: "Al ejecutar: si el flujo responde, ves la respuesta ahí mismo; si es asíncrono, el resultado llega como documento/correo o como ALERTA. Conéctalo a una alerta para enterarte." },
      { label: "Automatizaciones (programadas o por evento)", href: "/automations",
        result: "Resultado: corren solas (cron/evento); su estado y última ejecución se ven en la lista." },
      { label: "Alertas configurables", href: "/alerts",
        result: "Resultado: pop-up 🔔 + Telegram/WhatsApp/webhook; incluye resúmenes diarios/semanales." },
    ],
  },
  {
    key: "gobierno",
    title: "5 · Gobierno y cumplimiento",
    subtitle: "Configura, audita y mejora con tus datos.",
    steps: [
      { label: "Configuración de empresa", href: "/company",
        result: "Resultado: todos los casos quedan preconfigurados con tu contexto." },
      { label: "Autochequeo y Admin", href: "/admin",
        result: "Resultado: qué falta por activar (modelos, antivirus, MFA…) con la guía para resolverlo." },
      { label: "Auditoría", href: "/audit",
        result: "Resultado: bitácora navegable de todo lo que hizo la plataforma." },
    ],
  },
];

export function Journeys() {
  const [open, setOpen] = useState<string>("ventas");

  return (
    <div className="mb-6 rounded-2xl border border-violet-200 bg-violet-50/40 p-5">
      <div className="mb-1 flex items-center gap-2">
        <Compass className="h-5 w-5 text-violet-600" />
        <h2 className="font-semibold text-slate-800">Recorridos guiados</h2>
      </div>
      <p className="mb-4 text-xs text-slate-500">
        Cada recorrido encadena funciones por objetivo. Toca un paso para ir a su pestaña;
        debajo dice <b>dónde ves el resultado</b>.
      </p>
      <div className="space-y-2">
        {JOURNEYS.map((j) => {
          const isOpen = open === j.key;
          return (
            <div key={j.key} className="overflow-hidden rounded-xl border border-slate-200 bg-white">
              <button onClick={() => setOpen(isOpen ? "" : j.key)}
                className="flex w-full items-center justify-between px-4 py-3 text-left">
                <span>
                  <span className="font-semibold text-slate-800">{j.title}</span>
                  <span className="block text-xs text-slate-500">{j.subtitle}</span>
                </span>
                <ChevronDown className={`h-4 w-4 shrink-0 text-slate-400 transition ${isOpen ? "rotate-180" : ""}`} />
              </button>
              {isOpen && (
                <ol className="space-y-2 border-t border-slate-100 px-4 py-3">
                  {j.steps.map((s, i) => (
                    <li key={i} className="rounded-lg border border-slate-100 p-3">
                      <Link href={s.href} className="flex items-center gap-1.5 text-sm font-semibold text-violet-700 hover:text-violet-900">
                        <span className="flex h-5 w-5 items-center justify-center rounded-full bg-violet-100 text-[11px]">{i + 1}</span>
                        {s.label} <ArrowRight className="h-3.5 w-3.5" />
                      </Link>
                      <p className="mt-1 pl-6 text-xs text-slate-500">{s.result}</p>
                    </li>
                  ))}
                </ol>
              )}
            </div>
          );
        })}
      </div>
    </div>
  );
}
