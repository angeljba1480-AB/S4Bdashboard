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

## 2. API (FastAPI)

Hospédala en un contenedor (Fly.io / Render / Railway / Cloud Run) con
`apps/api/Dockerfile`. Variables mínimas: `DATABASE_URL`, `SECRET_KEY`,
`MASTER_KMS_KEY`, `CORS_ORIGINS=https://<tu-app>.vercel.app`, y la ruta de
modelos NaN Builders (`OPEN_ENABLED=true`, `OPEN_BASE_URL`, `OPEN_API_KEY`,
`OPEN_MODEL`).

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
