// Contenido de Ayuda compartido: lo usa la página /help y los popups por sección.
export type Guide = { id: string; title: string; tag: string; steps: string[]; note?: string };

export const GUIDES: Guide[] = [
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
      "Enrutamiento NaN-primero: los datos NO sensibles siempre empiezan con NaN (open). El premium NO es la ruta base.",
      "Cascada (premium a demanda): se escala a premium solo si activas “Máxima precisión” o si la respuesta de NaN es insuficiente. Contenido sensible requiere tu aprobación.",
      "Si NO hay premium configurado: todo se resuelve con NaN (no se promete premium). Si tampoco hay NaN, responde en modo demostración (mock) e indica que configures un proveedor real.",
      "Eficiencia (Admin → Eficiencia de tokens): condensa contexto grande antes de premium, pon un tope de gasto y activa Reranking RAG para más precisión.",
    ],
    note: "Datos sensibles (PII/confidencial/restringido) nunca salen a NaN/premium: van a VPC o local según la política.",
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
  {
    id: "chat",
    title: "Chat con fuentes (3 modos de contexto)",
    tag: "Chat",
    steps: [
      "Elige el modo: sin contexto, buscar en todo el RAG, o elegir documentos.",
      "“Máxima precisión” refina con premium (si está configurado); si no, responde NaN.",
      "“Usar memoria” recupera trabajos previos para responder con base en ellos.",
      "El banner muestra la clasificación del dato y la ruta real usada; todo queda auditado.",
    ],
  },
  {
    id: "memoria",
    title: "Memoria y etiquetas (recordar trabajos)",
    tag: "Memoria",
    steps: [
      "Guarda resultados del chat/casos con “Guardar en memoria”.",
      "Organiza con etiquetas (estilo gestor de contenido) y busca por texto o tag.",
      "Actívala en el chat con “Usar memoria” para continuar trabajos previos.",
    ],
  },
  {
    id: "onprem",
    title: "Integrar modelos/servicios on-prem (local del cliente)",
    tag: "Modelos",
    steps: [
      "Sirve para que MaestroAI use la infraestructura LOCAL del cliente (Ollama, vLLM, Qdrant, n8n) en vez de la nube.",
      "MaestroAI en la nube no ve 'localhost': expón el servicio con un túnel (Cloudflare/ngrok) y usa esa URL pública, o despliega MaestroAI on-prem.",
      "Admin → Modelos y conectores → Local (Ollama): Base URL https://<túnel>/v1 + modelo (ej. llama3.2:3b) → Activo → Probar conexión.",
      "Lo confidencial/restringido se procesará con tu modelo local y nunca saldrá a la nube.",
      "Qdrant: VECTOR_STORE=qdrant + QDRANT_URL; n8n: Admin → n8n; trainer LoRA: FINETUNE_TRAINER_URL. Ver docs/ONPREM-LAB.md.",
    ],
    note: "Para producción regulada, lo ideal es desplegar MaestroAI dentro de la red del cliente (alcanza los servicios por red interna).",
  },
  {
    id: "finetune",
    title: "Fine-tuning ligero (LoRA)",
    tag: "Modelos",
    steps: [
      "Sirve para enseñar TONO, FORMATO y tareas repetitivas — NO conocimiento (eso va por RAG).",
      "1) Crea un dataset y agrega ejemplos (prompt → respuesta ideal), o impórtalos desde Memoria.",
      "2) Cada ejemplo se anonimiza (la PII se redacta) antes de guardarse.",
      "3) Revisa (gate): valida mínimo de ejemplos, sin PII residual y sin inyecciones.",
      "4) Entrena: se exporta a JSONL y se manda a tu trainer con GPU (o queda 'simulado' si no hay backend).",
      "5) El adapter resultante se sirve por Ollama/vLLM como ruta local/VPC (privado).",
    ],
    note: "Requiere un trainer con GPU (FINETUNE_TRAINER_URL). Sin él, los jobs quedan en modo laboratorio.",
  },
  {
    id: "notebooks",
    title: "Notebooks (estilo NotebookLM)",
    tag: "Notebooks",
    steps: [
      "Crea un notebook y añade fuentes (documentos del RAG por área).",
      "Haz preguntas: responde citando las fuentes.",
      "Genera artefactos: resumen, FAQ, guía, briefing o cronología.",
    ],
  },
];

export function guidesByIds(ids: string[]): Guide[] {
  const map = new Map(GUIDES.map((g) => [g.id, g]));
  return ids.map((id) => map.get(id)).filter((g): g is Guide => Boolean(g));
}
