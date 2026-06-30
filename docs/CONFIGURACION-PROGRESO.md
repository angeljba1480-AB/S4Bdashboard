# MaestroAI · Progreso de configuración (estado vivo)

> **Regla de trabajo:** antes de tocar algo, **revisar aquí + el Autochequeo**
> (Admin → "Autochequeo del sistema", `GET /admin/readiness`) para no retrabajar.
> El Autochequeo es la fuente de verdad en runtime; este doc registra además los
> sub-pasos de Entra/Render/cuentas que el Autochequeo no puede ver.
>
> **Nunca** se anotan secretos aquí (solo estado e IDs no sensibles).
> Última actualización: 2026-06-29.

## 🔴 Núcleo
| Ítem | Estado | Detalle |
|---|---|---|
| Proveedor IA — NaN Builders (ruta `open`) | ✅ Listo | Admin → Modelos. Probar conexión OK · `qwen3.6`. Re-guardada tras cambiar llave. |
| Modelo premium (escalada, ruta `premium`) | ✅ Listo | **Claude (Anthropic) por API** (`https://api.anthropic.com/v1`, modelo *sonnet*), configurado en Admin → Modelos (override BD). **Nota:** Claude **Max ≠ API**; requiere API key de console.anthropic.com (facturación aparte). |
| Embeddings prod (`EMBEDDINGS_PROVIDER=open`, `qwen3-embedding`, `4096`) | ✅ Env + deploy | **Re-index pendiente** (docs de prueba); al cargar reales: Documentos → Re-indexar. |
| Scheduler (`SCHEDULER_ENABLED=true`) | ✅ Listo | Digests/alertas corren solos. |
| Cifrado prod (`SECRET_KEY` fuerte + `MASTER_KMS_KEY` dedicada) | ✅ Listo | `SECRET_KEY` ya era fuerte; `MASTER_KMS_KEY` distinta. **Rotación de llave invalida lo cifrado antes** → re-guardar NaN ✅ y **reconectar cuentas OAuth** (ver nota). |

> ⚠️ **Nota de rotación de llave (importante):** al cambiar `MASTER_KMS_KEY`/`SECRET_KEY`,
> todo lo cifrado con la llave anterior deja de leerse y hay que **recapturarlo**:
> API key de NaN (✅ hecho), **tokens OAuth → reconectar cuentas**, CallMeBot,
> credenciales de datasources y dataset financiero (si existían). Por eso el toolkit
> de acciones falló hasta reconectar.

## 🟡 Integraciones
| Ítem | Estado | Detalle |
|---|---|---|
| **Microsoft 365 OAuth** | ✅ Configurado | Entra + Render completos. **Solo falta conectar la cuenta** en Integraciones (acción del usuario, no config). |
| Google OAuth | ✅ Listo | Cliente "MaestroAI Web" + 4 APIs habilitadas (Gmail/Calendar/Drive/Sheets) + 7 scopes en consentimiento + cuenta conectada. |
| WhatsApp (CallMeBot) | ⏳ Pendiente | Se configura **en la app** (Alertas/Mi cuenta), no en Render. |
| n8n (workflows) | 🟡 Avanzado | `N8N_API_BASE_URL` ya presente en Render — revisar `N8N_ENABLED` + webhook base. |
| Zapier / **Make** / Webhook (salida) | ✅ Prod | Conectores de salida con plantilla. Make: escenario con *Custom webhook* → pega su URL. |
| **Subida de cualquier archivo** | ✅ Prod | `extract_text` soporta PDF, DOCX, **XLSX, PPTX, ZIP (recursivo), imágenes (OCR)**; binario desconocido se cataloga sin meter basura al RAG. Frontend acepta cualquier tipo (antes solo .txt/.md/.csv/.json), con tope de tamaño (`max_upload_mb`, def. 25). |
| **Nombre de documento autollenado** | ✅ Prod | Al elegir archivo, el nombre se llena solo (editable); se confirma la subida (no se sube a ciegas). El nombre editado gana sobre el del archivo. |

### Microsoft 365 OAuth — sub-pasos (app "MaestroAI")
- App: **MaestroAI** (multitenant, "Todos los usuarios de cuentas Microsoft").
  → por ser multitenant, en Render `MICROSOFT_TENANT=common`.
- [x] **Redirect URI (Web)**: `https://s4bdashboard.onrender.com/oauth/microsoft/callback`
- [x] **Secreto de cliente** vigente
- [x] **Permisos delegados** (Graph) + **consentimiento admin** ✅ (10 permisos en verde)
- [x] **Habilitado en Render**: `MICROSOFT_OAUTH_ENABLED=true` + `CLIENT_ID/SECRET/REDIRECT_URI/TENANT` (todos presentes)
- [ ] **Conectar cuenta** en Integraciones → el *Toolkit de acciones* se activa solo al conectar → verificar Autochequeo 🟢

> Nota: no existe un "toggle de toolkit" separado. El toolkit (correo/calendario/Sheets)
> queda disponible cuando el OAuth está habilitado **y** la cuenta está conectada.
> **Microsoft a nivel plataforma = LISTO.** Solo resta que cada usuario conecte su cuenta.

## 🟢 Seguridad / escala
| Ítem | Estado | Detalle |
|---|---|---|
| Antivirus (ClamAV) | ✅/⏳ | `ANTIVIRUS_ENABLED` on por defecto; `CLAMAV_HOST` opcional. |
| Qdrant (vector store) | ⏳ Opcional | Para escala de RAG. |
| SSO/OIDC | ⏳ Opcional | Login corporativo. |
| Fine-tuning (LoRA) | ⏳ Opcional | Trainer en lab propio; pesos solo local. |

## 📊 Tablero Financiero (caso de uso)
| Ítem | Estado | Detalle |
|---|---|---|
| Tablero + vistas + RAG | ✅ Prod | Resumen, P&L, Posición, Clientes, Evaluación, Proyectos, Costos, Utilización, Gob/IP, Benchmark, Alertas. |
| Carga self-service (Excel/zip o JSON) cifrada por tenant | ✅ Prod | Botón "Cargar datos" en el Espacio. |
| Cargar datos reales del cliente | ✅ Prod | Self-service: Excel/zip o JSON desde la app. **Plantilla descargable** (`GET /finance/dataset/template` + botón "Descargar plantilla") con el esquema completo para que el cliente la edite y la suba sin ayuda (auto-entregable). |
| Comparativo de costos (CMI vs BC vs Timesheet) | 🟡 Cableado | `costo_bc` listo; `costo_cmi`/`costo_timesheet` requieren **Nómina**. |
| **Explorador SharePoint (tipo Drive)** | ✅ Prod | En **Documentos → "Importar de SharePoint"**: navega sitios → carpetas → archivos e importa (igual que el de Google Drive). Router `/sharepoint` (sites/files/import) + componente `SharepointBrowser`. Usa la cuenta MS conectada. **Es la vía recomendada para uso manual.** |
| Conector SharePoint (carpeta fija) | ✅ Prod (delegado) | `/datasources/sharepoint` + `SharepointPanel`: carpeta fija por URL para **imports programados/automáticos** (no navegación). Mismo backend (`integrations/sharepoint.py`). App-only ("MaestroAI-Finanzas") = alternativa futura. |
| Conector BD directa (Paso 1) | ⏳ Esperando accesos | `/datasources` soporta DB de solo lectura. |
| Nómina + Catálogo de CC | ⏳ Pendiente | Para cerrar el comparativo (ver `MaestroAI_Auditoria_Esquemas_Finanzas.docx`). |

## ⚙️ Automatizaciones "reales" (entrada → ejecución → salida)
Una automatización deja de ser un disparo a ciegas: ahora tiene **entrada** (qué procesa),
corre, y **entrega** el resultado a un canal. Todo se ve y configura en el panel **Validar**.

| Pieza | Estado | Detalle |
|---|---|---|
| **Validar (semáforo previo)** | ✅ Prod | Pasos con ✓/✗/○: Disparador, Fuente/Caso, **Entrada**, Modelo (NaN), **Salida**. `○` = opcional (no bloquea `ready`). |
| **Entrada (qué procesar)** | ✅ Prod | Para *workflows (n8n)*: elige **Documentos nuevos** (corte `since`=última corrida), **Carpeta de Drive**, **Fuente de datos (legado)** o **Sin entrada**. Se manda como `source` en el payload del webhook. Endpoint `POST /automations/{id}/source`. |
| **Ingesta NATIVA (RAG)** | ✅ Prod | El indexado (OCR→chunking→embeddings→índice) **vive en MaestroAI**, no en n8n. La automatización `ingesta` corre **nativa** (`_run_ingesta`), sin viaje a n8n: indexa los documentos `indexed=False` según la fuente (`new_documents` con corte `since`; `datasource` jala filas frescas y las indexa). Antes el workflow n8n era un stub `Webhook→NoOp` (solo eco). Validar muestra "Indexado (nativo) · N pendientes". |
| **Salida (entrega del resultado)** | ✅ Prod | Canales **Notificación / WhatsApp / Correo** (correo destino opcional). Endpoint `POST /automations/{id}/delivery`; lo entrega `_deliver_result` con remitente de marca blanca (support sender) y queda en el audit log. |
| **Casos/recetas end-to-end** | ✅ Prod | Una automatización corre `prefill`+`execute` sin paso humano y entrega el `documento` por los canales elegidos (ej. "Resumen diario de correo y agenda"). |
| **Programar** | ✅ Prod | Diario/Semanal/Mensual tras validar (`POST /automations/{id}/schedule`); las corre `run_due` (cron/scheduler). |
| **Pipeline multi-paso (motor)** | ✅ Prod (Fase 1) | Una automatización puede ser un PIPELINE de pasos encadenados (`config.steps`): `fetch`→`workflow`/`recipe`/`ai`/`connector`/`notify`→`deliver`. El resultado de un paso alimenta al siguiente (`ctx.content`). Motor `_run_steps`/`_run_step`; compatible hacia atrás (sin `steps` = acción única). Endpoints `GET/PUT /automations/{id}/steps`. **Pendiente:** `sow`/`cyber` reales (Fase 3). |
| **Canvas multi-paso (constructor)** | ✅ Prod (Fase 2) | `StepsCanvas`: botón **Constructor** en cada automatización → agrega/ordena/edita/elimina nodos del pipeline y guarda con `PUT /steps`. Reordenar por **drag-and-drop** (HTML5) o botones ←→ (fallback). Cada tipo de paso tiene su editor (fetch/workflow/recipe/ai/connector/notify/deliver). |
| **Canvas visual + editable** | ✅ Prod (Fase A+B) | `WorkflowCanvas` dibuja cada automatización como diagrama de nodos (Disparador→Entrada→Acción→Modelo→Salida) con semáforo, reusando `/validate`. **Editable (Fase B):** clic en un nodo configurable (Disparador/Entrada/Salida) abre su editor en línea (programar/fuente/entrega) y guarda con los endpoints existentes. Marca blanca (el cliente no ve n8n). Como las automatizaciones son un pipeline fijo (no DAG arbitrario), la edición es por nodo; agregar/ordenar pasos libres requeriría un modelo multi-paso (futuro). |
| **Workflows `sow` / `cyber` reales** | ✅ Prod (Fase 3) | Generan documento con IA + grounding RAG (`_run_ai_doc`): **SOW** (objetivo/alcance/entregables/cronograma/inversión) y **Diagnóstico cyber** (hallazgos/madurez/controles/roadmap), en texto plano. Nativos (como `mando`), entregables por canal. Plantillas one-click + usables como paso `workflow` en el pipeline. |
| **Centro de mando (`mando`) real** | ✅ Prod | MaestroAI calcula un reporte ejecutivo con KPIs reales (`compute_operations`: casos, tokens, costo, apps) + insights de IA (`_run_mando`), en **texto plano legible** (secciones RESUMEN/KPIS/ALERTAS/RECOMENDACIONES, viñetas `•`, sin markdown). Entrega el reporte **limpio** (no el eco JSON de n8n; `_content_from_response` extrae solo el campo útil, también bajo `body`). La notificación respeta saltos de línea (`whitespace-pre-wrap`). Se puede enviar por WhatsApp/correo vía el panel de Salida. |
| **Fix n8n BYO 404** | ✅ Prod | `resolve_n8n`: en n8n propio (BYO) usa el prefijo `{tenant_id}/` cuando MaestroAI aprovisionó los flujos (antes llamaba `/webhook/mando` → 404). |
| **Fix conector URL** | ✅ Prod | `_normalize_url` antepone `https://` a URLs de conectores de salida sin protocolo. |

> **¿Entrega n8n o MaestroAI?** Las dos vías conviven:
> - *Workflows (n8n)*: pueden entregar **dentro de n8n** con sus nodos Gmail/WhatsApp/Slack (camino idiomático, se ve en el canvas). La entrega de MaestroAI queda como respaldo/gobierno.
> - *Casos/recetas*: corren **dentro de MaestroAI** (no hay n8n) → la entrega la hace `_deliver_result`. Sin esto, el resultado se perdía.
> En ambos casos MaestroAI centraliza **auditoría, redacción PII y remitente de marca blanca**.

## 🏷️ Marca blanca (white-label)
| Pieza | Estado | Detalle |
|---|---|---|
| Branding (nombre/logo/color/tagline) | ✅ Prod | Por tenant, aplicado en la web (`Shell.tsx`). `GET/PUT /admin/branding`. |
| Remitente de soporte por tenant | ✅ Prod | Los correos salen del buzón del cliente (`support_from`/`from_name`), no del personal. `GET/PUT /company/support-sender`. |
| **Dominio propio** (`custom_domain`) | ✅ Prod (código) / ⏳ DNS | Campo por tenant + validación + UI en Admin → Marca. Falta la parte de infra: apuntar **CNAME** del dominio a Render/Vercel y agregarlo como dominio personalizado ahí. Helper `branding.base_url()`. |
| **Correos con marca del cliente** | ✅ Prod | `branding.email_footer()` / `with_signature()` agrega pie con nombre+tagline+dominio del tenant; si no hay marca, **no estampa MaestroAI**. Aplicado en `_deliver_result` (entrega por correo). |
| Rebranding interno (código) | ⏳ Diferido | Referencias internas *"s4bdashboard"* → MaestroAI; ver nota en Pendientes. |

## 🔌 SAP (ERP) — OData / S/4HANA
| Pieza | Estado | Detalle |
|---|---|---|
| Conector de salida SAP (push) | ✅ Prod | Plantillas en Integraciones: **SAP S/4HANA (OData)** (Basic auth; escritura requiere `X-CSRF-Token`) y **SAP Business One (Service Layer)** (login → cookie `B1SESSION`). |
| **Lectura SAP → repositorio/RAG (nativo)** | ✅ Prod | Lector OData nativo (`app/integrations/odata.py` + modelo `OdataSource` + UI `OdataPanel`): GET a un Entity Set (v2/v4), auth Basic/Bearer, `$filter`/`$select`/`$top`, paginación `__next`/`@odata.nextLink`. Importa al repositorio + RAG (clasificado/cifrado). Solo lectura (no necesita CSRF). Endpoints `/datasources/odata`. |
| Lectura SAP vía n8n (alternativa) | ✅ Documentado | n8n HTTP Request OData GET (maneja CSRF/paginación) → POST a MaestroAI. Útil para escrituras o transformaciones en el canvas. |

> **Nota CSRF (SAP OData):** las escrituras OData v2 piden un token: primero `GET` con header `X-CSRF-Token: Fetch` → usar el token devuelto en el `POST`. El conector genérico hace POST directo; para escrituras con CSRF conviene **n8n** o un handler dedicado.

## 📤 Exportación de reportes (descarga + nube)
| Pieza | Estado | Detalle |
|---|---|---|
| Descargar PDF/Word/PPT/Excel/MD | ✅ Prod | `POST /export/report` (ya renderizaba con branding) expuesto en UI vía `ExportMenu`. |
| Guardar en la nube (Google/MS) | ✅ Prod | `POST /export/to-cloud` → **Google Docs** (`gdocs.create`) u **OneDrive** (`onedrive.upload`) con la cuenta conectada del usuario (toolkit Google/Microsoft). |
| Dónde aparece | ✅ Prod | `ExportMenu` en notificaciones de automatización (reportes mando/sow/cyber) y en el diagnóstico del KEDB. Recetas ya tenían export propio. |

## 🛡️ KEDB — base de errores conocidos (módulo cyber)
| Pieza | Estado | Detalle |
|---|---|---|
| **Módulo KEDB (gateado)** | ✅ Prod | Solo para tenants con **perfil de ciberseguridad** (`CompanyProfile.industry` con keywords ciber/cyber/seguridad/security/soc). `me.kedb_enabled` controla el nav; el router devuelve 403 si no aplica. Modelo `KnownError` (scope tenant/shared), endpoints `/kedb` (CRUD + `/analyze`), página con análisis de síntoma + alta + lista. `scope='shared'` = errores cross-cliente curados/sanitizados por el operador (visibles a todos los tenants cyber). |
| **Cross-cliente (promover + aprobar)** | ✅ Prod | `POST /kedb/{id}/promote`: copia **sanitizada por IA** (quita cliente/IP/host/usuarios) con `scope=shared, status=pending`. El **operador (SUPER_ADMIN)** la ve en `GET /kedb/proposals` y la **aprueba/rechaza** (`/approve`, `/reject`); al aprobar queda `published` y visible para todos los tenants cyber. Pendientes ocultas de la lista normal. UI: botón **Compartir** por error + sección de **propuestas** para el operador. |
| **Extracción asistida (IA)** | ✅ Prod | `POST /kedb/extract`: del texto de un log/incidente la IA propone un error estructurado (borrador), que el usuario revisa y da de alta. |

## 🏷️ Pendientes diferidos (mejoras, no bloquean)
| Ítem | Estado | Detalle |
|---|---|---|
| **Privacidad de embeddings** | ✅ Decidido (NaN) / on-prem listo | Hoy todo va a **NaN** (sin retención por su doc). Camino on-prem **construido**: `scripts/onprem/cloudflare-tunnel.sh` + ruta `local`. Mejora pendiente: **embeddings por sensibilidad** (Restringido→privado, resto→NaN). |
| **Rebranding interno → MaestroAI** | ⏳ Diferido | Quedan referencias/links internos que dicen *"silent dashboard" / "s4bdashboard"*; cambiar a **MaestroAI / plataforma.maestroai.mx**. Incluye el **dominio de la API** (`s4bdashboard.onrender.com`) que está en los **redirect URIs** de Microsoft y Google — si se cambia el dominio, hay que actualizar esos redirect URIs en Entra/Google y las env `*_REDIRECT_URI`. Hacerlo en bloque para no romper OAuth. |

## Apps de Entra (referencia, sin secretos)
- **MaestroAI** — OAuth de correo (delegada, multitenant). client_id `6cde3a0a-…`, tenant `a972e859-…`.
- **MaestroAI-Finanzas** — conector SharePoint (app-only: `Sites.Read.All`, `Files.Read.All`).
