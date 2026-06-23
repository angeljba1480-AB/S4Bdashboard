# Manual de Administrador — MaestroAI

> Guía de configuración, operación y gobierno de la plataforma **MaestroAI**.
> Para el uso diario, ver [`MANUAL-USUARIO.md`](./MANUAL-USUARIO.md).

---

## 1. Arquitectura

```
plataforma.maestroai.mx (dominio + SSL, público)
        │
        ▼
   Vercel ───────────► Portal Next.js (apps/web)
        │  NEXT_PUBLIC_API_BASE_URL
        ▼
   Render ───────────► Backend FastAPI (apps/api)
        │                 ├─ Enrutador de Privacidad + RAG + Auditoría
        │                 ├─ Supabase Postgres (datos persistentes)
        │                 ├─ NaN Builders (ruta open) / Ollama (ruta local)
        │                 └─ n8n (workflows) · Zapier (conectores)
```

- **Frontend:** Vercel, rama de producción `main`, Root Directory `apps/web`.
- **Backend:** Render (Docker), Root Directory `apps/api`, rama `main`.
- **Base de datos:** Supabase Postgres (Session Pooler).
- **Repo:** se desarrolla en rama de trabajo y se fusiona a `main` para desplegar.

---

## 2. Roles y permisos

| Rol | Nombre | Puede |
|---|---|---|
| `super_admin` | Super Admin | Todo, multi-tenant. |
| `admin` | **Admin Empresa** | Configuración del tenant: marca, facturación, usuarios, API keys, rutas, integraciones. |
| `user` | Usuario Negocio | Usar casos, agentes, documentos, automatizaciones. |
| `security` | Security / Compliance | Auditoría, políticas, revisión de eventos. |

La **autenticación** es JWT (Bearer). El endpoint `/me` devuelve el perfil,
la marca y la localización del país. **SSO/OIDC** es opcional (configurable).

---

## 3. Panel de administración (portal → Admin)

Disponible para **Admin Empresa**:

- **Marca (white-label):** nombre, tagline, logo (URL) y color primario. Se
  refleja en el portal y en los documentos Word/PDF exportados.
- **Marca y región:** país del tenant (México por defecto; multi-país LATAM).
- **Suscripción y asientos:** asientos usados/licenciados/disponibles, plan,
  estado, y alta de usuarios (con enforcement de asientos).
- **Planes (MXN):** Emprende / Negocio / Empresa / Gobierno (setup + anual por
  asiento). Estimador de costo incluido.
- **Usuarios:** listar y crear (402 si no hay asientos o la suscripción venció).
- **Integraciones · API & conectores:** API keys, conectores, webhooks.
- **MCP de empresa · Trámites:** agregar/importar trámites privados del tenant.

---

## 4. Variables de entorno (Backend / Render)

Configurar en **Render → Service → Environment**.

### Núcleo
| Variable | Descripción |
|---|---|
| `SECRET_KEY` | Clave de firma JWT (32+ caracteres). |
| `DATABASE_URL` | Postgres de Supabase (Session Pooler). Sin ella usa SQLite efímero. |
| `CORS_ORIGINS` | Orígenes permitidos (coma-separados). |
| `CORS_ORIGIN_REGEX` | Regex de orígenes; por defecto `*.vercel.app` y `*.maestroai.mx`. |
| `APP_ENV` | `production`. |

### Rutas de modelos (Enrutador de Privacidad)
| Ruta | Variables |
|---|---|
| **Open** (NaN Builders) | `OPEN_ENABLED=true`, `OPEN_API_KEY`, `OPEN_BASE_URL=https://api.nan.builders/v1`, `OPEN_MODEL` |
| **Local** (Ollama) | `LOCAL_ENABLED=true`, `LOCAL_BASE_URL=<url>/v1`, `LOCAL_MODEL` |
| **VPC** (vLLM/TGI) | `VPC_ENABLED=true`, `VPC_BASE_URL`, `VPC_API_KEY`, `VPC_MODEL` |
| **Premium** (OpenAI/Claude/Gemini) | `PREMIUM_ENABLED=true`, `PREMIUM_API_KEY`, `PREMIUM_BASE_URL`, `PREMIUM_MODEL` |

| `ALLOW_CLOUD_FALLBACK` | Si una ruta privada (local/VPC) **no** tiene modelo real, permite subir al mejor proveedor real (open/premium) en vez del simulador. **Opt-in** (default `false`): habilítalo solo si aceptas que datos privados los procese la nube mientras conectas tu modelo local. |

### Workflows / Automatización
| Variable | Descripción |
|---|---|
| `N8N_ENABLED=true` | Activa la integración n8n. |
| `N8N_WEBHOOK_BASE_URL` | `https://<tu-n8n>/webhook` |
| `N8N_API_BASE_URL` | `https://<tu-n8n>/api/v1` (auto-provisión de workflows). |
| `N8N_API_KEY` | API key de n8n. |
| `N8N_AUTO_PROVISION` | `true` — la plataforma crea los workflows por tenant. |
| `SCHEDULER_ENABLED` | Programador interno para automatizaciones por tiempo. |

### Seguridad / RAG
| Variable | Descripción |
|---|---|
| `ENCRYPTION_ENABLED` | Cifrado en reposo (AES-256-GCM). |
| `MASTER_KMS_KEY` | Semilla de llaves por tenant (en prod usar KMS real). |
| `VECTOR_STORE` | `inprocess` (default) o `qdrant`. |
| `EMBEDDINGS_PROVIDER` | `local` / `open` / `premium`. |
| `SSO_ENABLED` + `OIDC_*` | SSO opcional. |

---

## 5. Variables de entorno (Frontend / Vercel)

| Variable | Valor |
|---|---|
| `NEXT_PUBLIC_API_BASE_URL` | URL pública del backend en Render (sin `/` final). |

Settings de Vercel: Framework **Next.js**, Root Directory **`apps/web`**,
Production Branch **`main`**, "Include files outside root directory" **ON**.

---

## 6. Conectar la IA (rutas de modelos)

El Enrutador detecta la sensibilidad y elige la ruta. Para que cada ruta produzca
contenido **real**, conecta su proveedor:

- **NaN Builders (ruta open / nube):** `OPEN_ENABLED=true` + `OPEN_API_KEY` +
  `OPEN_BASE_URL=https://api.nan.builders/v1` + `OPEN_MODEL` (ver docs de NaN).
- **Ollama (ruta local / privada):** `LOCAL_ENABLED=true` + `LOCAL_BASE_URL`
  (endpoint OpenAI-compatible `/v1`) + `LOCAL_MODEL`. Si Ollama corre en tu red,
  exponlo con una URL pública (Cloudflare Tunnel/servidor) para que Render lo
  alcance.

**Mientras no haya modelo local**, activa `ALLOW_CLOUD_FALLBACK=true` para que los
casos sensibles usen NaN (real) en vez del simulador. Al conectar Ollama, lo
sensible volverá a la ruta local automáticamente (puedes apagar el fallback).

> Todo enrutamiento y fallback queda **auditado** (ruta usada, si hubo fallback).

---

## 7. Integraciones

- **n8n (gestionado):** la plataforma **auto-provisiona** 6 workflows por tenant
  (Ingesta documental, Consulta RAG, Generación de SOW, Diagnóstico cyber, Centro
  de mando, Fine-tuning). El usuario no arma flujos a mano.
- **Conectores de salida:** HubSpot, Salesforce, Shopify, Rappi, Webhook genérico
  (para **Zapier** y 9,000+ apps). Se prueban desde Integraciones.
- **API pública `/v1`:** sistemas externos llaman con `X-API-Key`.
- **Webhooks entrantes firmados:** HMAC-SHA256 (`X-Signature`).

---

## 8. Auditoría y cumplimiento

- **Auditoría** (portal → Auditoría): bitácora de eventos con nivel de riesgo.
- **Export SIEM:** descarga JSONL para tu SIEM.
- Cada generación registra: usuario, ruta del modelo, fuentes, costo y si hubo
  fallback. La privacidad **nunca** se debilita silenciosamente.

---

## 9. Base de datos (Supabase)

- Usa la cadena **Session Pooler** (IPv4) en `DATABASE_URL`.
- El backend normaliza `postgres://`→`postgresql://` y usa `pool_pre_ping`.
- Al primer arranque crea las tablas y **siembra** el tenant demo + usuarios.
- Para datos persistentes en producción, mantener Supabase (no SQLite).

---

## 10. Despliegue y operación

- **Publicar cambios:** fusionar a `main` → Vercel y Render despliegan solos.
- **Vercel:** producción en `plataforma.maestroai.mx` (Deployment Protection
  desactivada = acceso público; actívala para restringir a tu equipo).
- **Render:** plan **Starter** para que el backend no se "duerma".
- **Salud:** el backend expone `/health`.

---

## 11. Checklist de puesta a punto

- [ ] `SECRET_KEY`, `DATABASE_URL` (Supabase), `CORS_ORIGINS`
- [ ] `NEXT_PUBLIC_API_BASE_URL` en Vercel
- [ ] NaN: `OPEN_ENABLED/_API_KEY/_BASE_URL/_MODEL` (+ `ALLOW_CLOUD_FALLBACK` si aplica)
- [ ] Ollama: `LOCAL_*` (cuando esté en servidor con URL pública)
- [ ] n8n: `N8N_ENABLED/_WEBHOOK_BASE_URL/_API_BASE_URL/_API_KEY`
- [ ] Marca (white-label) y plan/asientos configurados
- [ ] Dominio + SSL y acceso público según corresponda

---

_MaestroAI · Documento de administración interno._
