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
| Zapier NLA | ⏳ Opcional | Catálogo de apps. |

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
| Cargar datos reales del cliente | ⏳ Pendiente | Subir Excel/zip o JSON desde la app. |
| Comparativo de costos (CMI vs BC vs Timesheet) | 🟡 Cableado | `costo_bc` listo; `costo_cmi`/`costo_timesheet` requieren **Nómina**. |
| Conector SharePoint (Paso 1) | ⏳ Pendiente | App **"MaestroAI-Finanzas"** (app-only, Sites/Files.Read.All) creada; **falta construir el conector** que liste `Proyectos Finanzas` y alimente `ingest_excel`. |
| Conector BD directa (Paso 1) | ⏳ Esperando accesos | `/datasources` soporta DB de solo lectura. |
| Nómina + Catálogo de CC | ⏳ Pendiente | Para cerrar el comparativo (ver `MaestroAI_Auditoria_Esquemas_Finanzas.docx`). |

## 🏷️ Pendientes diferidos (mejoras, no bloquean)
| Ítem | Estado | Detalle |
|---|---|---|
| **Rebranding interno → MaestroAI** | ⏳ Diferido | Quedan referencias/links internos que dicen *"silent dashboard" / "s4bdashboard"*; cambiar a **MaestroAI / plataforma.maestroai.mx**. Incluye el **dominio de la API** (`s4bdashboard.onrender.com`) que está en los **redirect URIs** de Microsoft y Google — si se cambia el dominio, hay que actualizar esos redirect URIs en Entra/Google y las env `*_REDIRECT_URI`. Hacerlo en bloque para no romper OAuth. |

## Apps de Entra (referencia, sin secretos)
- **MaestroAI** — OAuth de correo (delegada, multitenant). client_id `6cde3a0a-…`, tenant `a972e859-…`.
- **MaestroAI-Finanzas** — conector SharePoint (app-only: `Sites.Read.All`, `Files.Read.All`).
