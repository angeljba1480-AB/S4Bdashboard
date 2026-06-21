# Despliegue — Supabase + Vercel + NaN Builders

Arquitectura de producción del MVP:

```
Vercel (apps/web, Next.js)  ──►  API (apps/api, FastAPI en contenedor)
                                      │
                                      ├─► Supabase Postgres (datos + Auth)
                                      ├─► Supabase pgvector (RAG)
                                      └─► NaN Builders (ruta open/volumen) · VPC · Local · Premium
```

## 1. Supabase (datos + RAG)

1. Crea (o reutiliza) un proyecto Supabase.
2. **Project Settings → Database** → copia la *connection string* (pooler, puerto 6543).
3. Aplica la migración pgvector: `infra/supabase/001_pgvector.sql` (SQL editor).
4. En la API configura:
   ```
   DATABASE_URL=postgresql://postgres.<ref>:<password>@aws-0-<region>.pooler.supabase.com:6543/postgres
   VECTOR_STORE=pgvector
   ```
   Las tablas relacionales se crean solas al arrancar (SQLModel). `rag_chunks`
   guarda los embeddings (texto cifrado en reposo).

> Auth: el MVP usa JWT propio con usuarios en Postgres. Para usar **Supabase
> Auth (GoTrue)** en su lugar, ver `SSO_ENABLED` (OIDC) — Supabase expone OIDC.

## 2. API (FastAPI) — desplegar el backend

El backend ya viene listo para contenedor (`apps/api/Dockerfile`: usuario
no-root, healthcheck en `/health`, escucha en `$PORT`). Elige una opción:

### Opción A — Render (un clic, recomendada)
Hay un **blueprint** en `render.yaml` (crea la API **y** un Postgres gestionado):
1. Render → **New → Blueprint** → apunta a este repo.
2. Render genera `SECRET_KEY` y conecta `DATABASE_URL` al Postgres solo.
3. Tras el deploy, en el servicio pon **`CORS_ORIGINS=https://<tu-app>.vercel.app`**.
4. (Opcional) activa modelos: `OPEN_ENABLED=true`, `OPEN_API_KEY=…`.

### Opción B — Fly.io
Config en `apps/api/fly.toml`:
```bash
cd apps/api
fly launch --no-deploy
fly postgres create && fly postgres attach <db>     # define DATABASE_URL
fly secrets set SECRET_KEY=$(openssl rand -hex 32) \
                CORS_ORIGINS=https://<tu-app>.vercel.app
fly deploy
```

### Opción C — Railway
1. New Project → **Deploy from repo** → Root Directory `apps/api` (detecta el Dockerfile).
2. Add **PostgreSQL** → copia su `DATABASE_URL` al servicio.
3. Variables: `SECRET_KEY` (genera 32+ chars), `CORS_ORIGINS=https://<tu-app>.vercel.app`.

### Variables del backend (checklist)
| Variable | Obligatoria | Valor |
|---|---|---|
| `DATABASE_URL` | ✅ | Postgres (Render/Fly/Railway o **Supabase**). `postgres://` se normaliza solo. |
| `SECRET_KEY` | ✅ | 32+ caracteres aleatorios (firma JWT + cifrado por defecto). |
| `MASTER_KMS_KEY` | ◑ | Recomendada: clave de cifrado en reposo. Si la fijas, podrás rotar `SECRET_KEY` sin perder datos cifrados. Si la omites, usa `SECRET_KEY`. |
| `CORS_ORIGINS` | ✅ | La URL de tu app en Vercel (sin esto, el portal no conecta). |
| `APP_ENV` | — | `production`. |
| `VECTOR_STORE` | — | `inprocess` (default) o `pgvector` (reusa el Postgres; corre `infra/supabase/001_pgvector.sql`). |
| `OPEN_ENABLED` / `OPEN_API_KEY` | — | Modelos NaN Builders. |
| `N8N_*` | — | Workflows gestionados (sección 5). |

> Verifica con `GET https://<tu-api>/health` → `{"status":"ok"}`. Usuario demo:
> `admin@s4b.mx` / `demo1234` (cámbialo en producción).

## 3. Vercel (portal web)

- Importa el repo en Vercel y pon **Root Directory = `apps/web`**
  (detecta el workspace npm y resuelve `packages/shared`).
- Variable de entorno: `NEXT_PUBLIC_API_BASE_URL=https://<tu-api>`.
- Framework: Next.js (autodetectado). `vercel.json` ya incluido.

## 4. NaN Builders (modelos)

Endpoint OpenAI-compatible. En la API:
```
OPEN_ENABLED=true
OPEN_BASE_URL=<base url de NaN Builders>
OPEN_API_KEY=<key>            # secreto: solo en el entorno, nunca en git
OPEN_MODEL=<modelo>
# RAG con sus embeddings (opcional):
EMBEDDINGS_PROVIDER=open
EMBEDDINGS_MODEL=<modelo de embeddings>
EMBEDDINGS_DIM=<dimensión>    # debe coincidir con la columna vector() de pgvector
```

> Si cambias `EMBEDDINGS_DIM`, ajusta `vector(<dim>)` en `001_pgvector.sql` y
> reindexa los documentos.

## 5. Workflows — n8n gestionado (as-a-service, cero configuración)

El usuario final **no toca n8n**. Tú operas un n8n gestionado y la plataforma
**aprovisiona automáticamente** los workflows de cada tenant (vía la REST API de
n8n), aislados por path `{tenant_id}/{workflow_id}`. Configúralo una vez:

```
N8N_ENABLED=true
N8N_WEBHOOK_BASE_URL=https://n8n.tu-saas.com/webhook
N8N_API_KEY=<n8n API key>          # secreto: solo en el entorno
N8N_AUTH_HEADER=X-N8N-API-KEY
N8N_API_BASE_URL=https://n8n.tu-saas.com/api/v1   # habilita el auto-provision
N8N_AUTO_PROVISION=true
```

Flujo: al primer `/workflows/{id}/run` de un tenant, la plataforma crea+activa
sus 6 workflows (`ingesta, rag, sow, cyber, mando, finetune`) en tu n8n y marca
`n8n_provisioned`. Idempotente; re-provisionable desde **Admin → Workflows·n8n**.
El POST al webhook recibe `{run_id, workflow_id, workflow, tenant_id, user_id}` y
cada corrida se audita.

**BYO (avanzado, opcional):** un tenant técnico puede traer su propio n8n en
Admin (URL + token cifrado). Si lo define se usa el suyo; si no, el gestionado.

> **Importante (control de datos):** el pipeline sensible (clasificación, PII,
> RAG, router, cifrado, auditoría) vive **dentro de la API**. A n8n solo le llega
> un payload mínimo y parametrizado por tenant — n8n se usa para las **acciones de
> salida** (email, SOW, CRM, tareas), no para procesar el documento crudo.

## 6. Alertas de ruta (plug-and-play)

Antes de enviar, el chat consulta `POST /chat/preview` y muestra en vivo qué
detectó y qué ruta usará: verde (datos públicos/internos), ámbar (confidencial/
PII → ruta privada local/VPC) o rojo (bloqueado). Es preflight: **no ejecuta el
modelo ni audita**, solo asesora al usuario desde el inicio.

