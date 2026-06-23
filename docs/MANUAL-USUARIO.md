# Manual de Usuario — MaestroAI

> Plataforma de **IA privada y gobernada** para empresas en LATAM.
> Portal: **https://plataforma.maestroai.mx** · Marca: **MaestroAI**

Este manual está dirigido al **usuario final** (Usuario Negocio). Para
configuración y administración, ver [`MANUAL-ADMIN.md`](./MANUAL-ADMIN.md).

---

## 1. Acceso

1. Abre **https://plataforma.maestroai.mx**
2. Inicia sesión con tu **correo de empresa** y contraseña.
   - Demo: `admin@maestroai.mx` / `demo1234`
3. El portal es **multi-empresa (multi-tenant)**: solo ves los datos de tu
   organización.

> El portal es instalable como **app de escritorio/móvil** (PWA): en Chrome,
> menú → "Instalar MaestroAI".

---

## 2. ¿Qué es MaestroAI?

No es "otro ChatGPT". Es una **capa privada y gobernada** sobre la IA. Su
diferenciador es el **Enrutador de Privacidad (Privacy Model Router)**: cada vez
que procesas un dato, el sistema:

1. **Clasifica** la sensibilidad (Público / Interno / Confidencial / Restringido).
2. **Detecta PII** (RFC, CURP, CLABE, tarjetas, correos, salud, secretos).
3. **Decide el camino** automáticamente:

| Clasificación | Ruta del modelo |
|---|---|
| Restringido | **Local** (nunca sale de tu infraestructura) |
| Confidencial / con PII | **VPC** o local |
| Interno / Público | **Open / Premium** (nube) |
| Inyección / exfiltración | **Bloqueado** |

4. **Minimiza y redacta** antes de enviar al modelo.
5. Responde **con fuentes citadas** y deja **evidencia auditable** (quién, qué,
   qué ruta, qué costo). **Tú nunca eliges el modelo** — el sistema lo hace por ti.

---

## 3. Navegación

La barra lateral tiene tres grupos:

### GENERAL
- **Resumen** — panel de inicio con tu actividad y métricas clave.
- **Operación** — métricas de uso: casos ejecutados, búsquedas, tokens y costo.

### PLATAFORMA
- **Casos de uso** — genera entregables con IA (ver §4).
- **Tableros** — arma dashboards describiendo lo que quieres medir (ver §8).
- **Trámites y casos** — catálogo de trámites por país/estado (ver §9).
- **App Studio** — construye mini-apps con IA y publícalas (pago por despliegue).
- **Automatizaciones** — conecta un disparador con una acción (ver §6).
- **Integraciones** — API keys, conectores y webhooks (ver §7).
- **Agentes** — agentes verticales especializados (ver §5).
- **Documentos** — sube y consulta documentos con RAG seguro (ver §10).
- **Chat con fuentes** — conversa con la IA citando tus documentos/trámites.
- **Workflows** — flujos gestionados (n8n) que la plataforma provisiona sola.

### GOBIERNO
- **Mi cuenta** — tu licencia, rol y asientos de la empresa.
- **Auditoría** — bitácora de eventos (visible según tu rol).
- **Admin** — configuración (solo Admin Empresa).

---

## 4. Casos de uso (generar documentos con IA)

El corazón del trabajo diario. "Elige qué quieres lograr, da lo mínimo y la
plataforma hace el resto. Tú solo apruebas."

1. Entra a **Casos de uso** y elige uno (ej. *Propuesta comercial*, *Carta*,
   *Reporte*, *Licitación*…).
2. Llena los **datos mínimos** que pide (cliente, servicio, monto, etc.).
3. La IA genera un **borrador** (a través del Enrutador de Privacidad).
4. **Revisa** el borrador y pulsa **Aprobar y generar**.
5. Descarga el entregable:
   - **Descargar Word** → documento `.docx` profesional con tu marca, portada,
     secciones, tabla de datos y pie de página confidencial.
   - **PDF** o **Markdown** también disponibles.

> **Si el contenido sale genérico** ("Generado por el modelo mock-local…"),
> significa que el caso se enrutó a una ruta privada que aún no tiene un modelo
> real conectado. Avisa a tu administrador (ver Manual de Admin §6).

---

## 5. Agentes

Agentes verticales especializados, listos para usar:

- **Document Intelligence** — analiza documentos y responde con citas.
- **Cyber Diagnostic** — diagnóstico de ciberseguridad y roadmap.
- **Proposal / SOW** — propuestas y enunciados de trabajo.
- **Executive Copilot** — apoyo ejecutivo y resúmenes.

Entra a **Agentes**, elige uno y conversa. Cada respuesta pasa por el Enrutador
de Privacidad y cita sus fuentes. Tu Admin puede crear agentes personalizados.

---

## 6. Automatizaciones

Conecta un **disparador** con una **acción**, sin programar:

- **Disparadores:** manual, programado (diario/semanal/mensual) o por evento
  (ej. "se subió un documento").
- **Acciones:** ejecutar un **workflow** (n8n), correr un **caso de uso**,
  enviar a un **conector** (CRM/ERP) o **notificar**.

Usa la **galería de plantillas** (resumen diario, cobranza semanal, publicación
en redes, reporte de operación, alerta de documento sensible…) o crea la tuya.
Puedes **activar/desactivar** y **ejecutar ahora** cada automatización.

---

## 7. Integraciones

Conecta MaestroAI con tus sistemas:

- **API keys (entrada):** para que otros sistemas llamen a MaestroAI vía la API
  pública `/v1` con el header `X-API-Key`.
- **Conectores (salida):** envía datos a tus herramientas. Plantillas listas:
  **HubSpot, Salesforce, Shopify, Rappi, Webhook genérico** (ej. para conectar
  **Zapier** y sus 9,000+ apps). Cada conector se puede **probar**.
- **Webhooks entrantes (firmados):** un sistema externo notifica eventos
  firmando el cuerpo con HMAC-SHA256 (header `X-Signature`).

---

## 8. Tableros

Arma dashboards a tu medida:

1. **Describe** qué quieres medir; la plataforma sugiere widgets.
2. Agrega KPIs y gráficas (tokens por fuente, casos por receta, costo por ruta,
   casos recientes…) y **KPIs manuales** (tus propios números).
3. Los widgets se alimentan de **datos en vivo** (métricas de plataforma y datos
   de tu empresa).
4. Puedes **vincular** un workflow a un tablero y ejecutarlo desde ahí.

---

## 9. Trámites y casos (MCP de trámites)

Catálogo curado de trámites y problemas de la población, **por país y estado**,
organizado por ejes de desarrollo. Está estructurado en **3 capas**:

1. **País** (nacional) · 2. **Estado/Municipio** · 3. **Empresa** (privada de tu
   organización).

Filtra por estado/eje/búsqueda y convierte un trámite en una **propuesta de caso
de uso** con un clic. Estas fuentes también **aterrizan (grounding)** las
respuestas de los agentes y casos.

---

## 10. Documentos (RAG seguro)

1. **Sube** un documento.
2. El sistema lo **clasifica** (Público/Interno/Confidencial/Restringido),
   detecta **PII** e **indexa** su contenido de forma segura.
3. En **Chat con fuentes** o en los casos de uso, la IA usa esos documentos
   como contexto y **cita** de dónde sacó la información.
4. Puedes **importar** un documento a un **trámite estructurado** de empresa.

> Los documentos se almacenan **cifrados en reposo** (AES-256-GCM).

---

## 11. Mi cuenta

Consulta tu **licencia** (rol + asiento) y el **pool de licencias** de tu
empresa: asientos usados / licenciados / disponibles, plan y estado de la
suscripción.

---

## 12. Preguntas frecuentes

**¿Por qué no puedo elegir el modelo de IA?**
Por diseño: el Enrutador de Privacidad elige la ruta más segura para cada dato.

**¿Mis datos sensibles salen a la nube?**
No, salvo que tu Admin lo permita explícitamente. Los datos Restringidos van a
la ruta **local** y nunca salen; los Confidenciales/PII a **VPC/local**.

**El primer acceso del día tarda unos segundos.**
Si el backend está en un plan que "duerme" por inactividad, el primer request lo
"despierta" (~50 s). Reintenta.

**¿Cómo descargo en Word?**
En un caso de uso completado → botón **Descargar Word**.

---

_MaestroAI · Documento de uso interno._
