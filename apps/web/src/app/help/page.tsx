"use client";

import { PageHeader, Shell } from "@/components/Shell";
import { ChevronDown, HelpCircle, Search } from "lucide-react";
import { useState } from "react";

type Guide = { id: string; title: string; tag: string; steps: string[]; note?: string };

const GUIDES: Guide[] = [
  {
    id: "n8n",
    title: "Conectar n8n y automatizar",
    tag: "Automatización",
    steps: [
      "Por defecto MaestroAI usa un n8n gestionado (cero configuración): no necesitas instalar nada para empezar.",
      "¿Quieres usar tu propio n8n? Ve a Admin → n8n e introduce la Webhook Base URL (ej. https://n8n.tuempresa.com/webhook) y tu API key. Pulsa Guardar; verás el motor (n8n / simulado) y el origen.",
      "En n8n crea un workflow que arranque con un nodo Webhook y copia el nombre/ruta del workflow (será tu referencia).",
      "En MaestroAI ve a Automatizaciones → Nueva automatización y elige acción “workflow”. En “referencia” pon el nombre del workflow de n8n.",
      "Elige el disparador: manual, programada (diaria/semanal/mensual) o por evento (ej. document_uploaded).",
      "Para que n8n hable con tus sistemas, en Integraciones añade un Conector de salida (REST) o un Webhook entrante firmado; n8n orquesta el resto (DB, SOAP, apps propias, 400+ apps).",
      "Prueba la automatización con “Ejecutar” y revisa el resultado en Auditoría.",
    ],
    note: "n8n es el puente universal para sistemas a la medida sin API. Regla: webhooks para eventos, REST para comandos, n8n para el resto.",
  },
  {
    id: "correo",
    title: "Conectar correo (Outlook / Gmail / IMAP)",
    tag: "Integraciones",
    steps: [
      "Ve a Integraciones → Conectar correo.",
      "Outlook o Gmail: pulsa Conectar y autoriza en la pantalla de Microsoft/Google. Puedes añadir varias cuentas por proveedor (trabajo + personal).",
      "Otros (Yahoo, iCloud, Zoho, hosting…): usa IMAP con el preset o host/puerto y una contraseña de aplicación.",
      "Para acciones de escritura (enviar correo, calendario, Teams), reconecta para otorgar los permisos nuevos — ver guía de Acciones.",
    ],
  },
  {
    id: "documentos",
    title: "Subir documentos y usar el RAG por área",
    tag: "Documentos",
    steps: [
      "Ve a Documentos → Subir. Asigna un área y una categoría (propuesta, licitación, ISO, conocimiento…).",
      "El sistema detecta el tratamiento (público/interno/confidencial/restringido) y la PII; puedes corregirlo.",
      "El contenido se cifra y se indexa en el RAG. Los permisos por área deciden quién lo ve.",
      "En el Chat elige el modo de contexto: sin contexto, todo, o elegir documentos.",
      "Para más precisión activa el Reranking en Admin → Eficiencia de tokens.",
    ],
  },
  {
    id: "acciones",
    title: "Acciones en Google / Microsoft (con aprobación)",
    tag: "Acciones",
    steps: [
      "Configura los permisos de escritura en Azure/Google y reconecta — ver docs/ACCIONES-ESCRITURA-SETUP.",
      "Ve a Acciones: las lecturas (Sheets, Calendar, OneDrive, Excel, SharePoint) corren al instante.",
      "Las escrituras (enviar correo, crear eventos, append a Sheets/Excel, Teams) requieren tu aprobación.",
      "Con “Permitir siempre” autorizas una acción a futuro (revocable en cualquier momento).",
    ],
  },
  {
    id: "conectores",
    title: "Conectores de salida (CRM / ERP / Delivery)",
    tag: "Integraciones",
    steps: [
      "Integraciones → Conectores. Empieza con una plantilla (HubSpot, Salesforce, Shopify, Rappi, genérico).",
      "Indica nombre, endpoint (URL) y token. El token se guarda cifrado.",
      "Abre el detalle (ícono ℹ️) para ver qué se configuró y el ejemplo de payload por tipo.",
      "Usa el ojo (👁️) para revelar el token configurado — solo ADMIN/DEVOPS y queda auditado.",
      "Pulsa Probar para enviar un payload de prueba.",
    ],
  },
  {
    id: "legados",
    title: "Importar sistemas legados (BD de solo lectura / CSV)",
    tag: "Integraciones",
    steps: [
      "Integraciones → Fuentes de datos. Para una base de datos: pon el DSN (postgresql://… o mysql://…) y una consulta SELECT.",
      "Pulsa Probar (valida solo lectura) y luego Importar: el resultado entra al repositorio + RAG.",
      "¿Sin API pero exporta CSV/Excel? Usa “Importar CSV”: pega el contenido (encabezados en la primera fila) y delimitador.",
      "Usa el ojo (👁️) para revelar el DSN (sensible) — solo ADMIN/DEVOPS, auditado.",
    ],
  },
  {
    id: "modelos",
    title: "Modelos externos, cascada, rerank y eficiencia",
    tag: "Modelos",
    steps: [
      "Admin → Modelos externos: configura el proveedor Abierto (NaN) y/o Premium (Base URL + modelo + API key).",
      "Pulsa Probar conexión para verificar que el modelo responde (latencia + muestra, o el error).",
      "Cascada: el modelo barato redacta y el premium refina las tareas avanzadas (con aprobación para contenido sensible).",
      "Eficiencia (Admin → Eficiencia de tokens): condensa contexto grande antes de premium, pon un tope de gasto y activa Reranking RAG para más precisión.",
    ],
  },
  {
    id: "imagenes",
    title: "Generar imágenes (texto → imagen)",
    tag: "Imágenes",
    steps: [
      "Ve a Generar imágenes, escribe el prompt, elige relación de aspecto (1:1/16:9/9:16) y variantes (1–4).",
      "El prompt se redacta de PII antes de salir; las imágenes quedan en tu galería por área y auditadas.",
    ],
    note: "Requiere un proveedor que exponga /images/generations. La API documentada de NaN no expone imágenes hoy (su Generate es de su web).",
  },
  {
    id: "webhooks",
    title: "Webhooks entrantes firmados (HMAC)",
    tag: "Integraciones",
    steps: [
      "Integraciones → Webhooks entrantes → Crear. Copia el secreto (se muestra una sola vez).",
      "El sistema externo firma el cuerpo con HMAC-SHA256 y lo manda en el header X-Signature a la URL del webhook.",
      "Conecta el webhook a una automatización (disparador por evento) para reaccionar a lo que llega.",
    ],
  },
];

export default function HelpPage() {
  const [q, setQ] = useState("");
  const [open, setOpen] = useState<string | null>("n8n");
  const ql = q.trim().toLowerCase();
  const list = ql
    ? GUIDES.filter((g) => (g.title + " " + g.tag + " " + g.steps.join(" ") + " " + (g.note ?? "")).toLowerCase().includes(ql))
    : GUIDES;

  return (
    <Shell>
      <PageHeader title="Ayuda" subtitle="Guías paso a paso en español para configurar y usar MaestroAI." />

      <div className="mb-4 flex items-center gap-2 rounded-lg border border-slate-300 bg-white px-3 py-2">
        <Search className="h-4 w-4 text-slate-400" />
        <input value={q} onChange={(e) => setQ(e.target.value)} placeholder="Buscar en la ayuda (ej. n8n, correo, rerank)…"
          className="w-full text-sm outline-none" />
      </div>

      <div className="space-y-2">
        {list.map((g) => (
          <div key={g.id} className="overflow-hidden rounded-2xl border border-slate-200 bg-white">
            <button onClick={() => setOpen(open === g.id ? null : g.id)}
              className="flex w-full items-center justify-between px-5 py-4 text-left">
              <span className="flex items-center gap-3">
                <HelpCircle className="h-5 w-5 text-violet-600" />
                <span className="font-semibold text-slate-800">{g.title}</span>
                <span className="rounded-full bg-slate-100 px-2 py-0.5 text-[11px] font-medium text-slate-500">{g.tag}</span>
              </span>
              <ChevronDown className={`h-4 w-4 text-slate-400 transition ${open === g.id ? "rotate-180" : ""}`} />
            </button>
            {open === g.id && (
              <div className="border-t border-slate-100 px-5 py-4">
                <ol className="list-decimal space-y-2 pl-5 text-sm text-slate-700">
                  {g.steps.map((s, i) => <li key={i}>{s}</li>)}
                </ol>
                {g.note && <p className="mt-3 rounded-lg bg-amber-50 px-3 py-2 text-xs text-amber-800">{g.note}</p>}
              </div>
            )}
          </div>
        ))}
        {list.length === 0 && <div className="rounded-xl border border-slate-200 bg-white p-6 text-center text-sm text-slate-400">Sin resultados para “{q}”.</div>}
      </div>
    </Shell>
  );
}
