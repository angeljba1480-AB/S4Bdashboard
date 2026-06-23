# Private AI Platform — API

Backend FastAPI: el corazón gobernado de la plataforma.

## Estructura

```
app/
  main.py            App FastAPI + CORS + lifespan (init_db + seed).
  config.py          Configuración (.env) tipada.
  db.py / models.py  SQLModel: tenants, users, agents, documents, chunks,
                     conversations, messages, audit_events, api_keys.
  auth.py            JWT, hashing PBKDF2, RBAC (require_roles), deps de tenant.
  schemas.py         Contratos Pydantic.
  seed.py            Datos demo (tenant MaestroAI + agentes + docs).
  security/
    pii.py           Detección de PII (RFC, CURP, CLABE, tarjetas, email…).
    classifier.py    Clasificación de sensibilidad.
    dlp.py           Minimización + redacción de contexto.
    policy.py        Policy engine (carga política, detecta violaciones).
    crypto.py        Cifrado en reposo AES-256-GCM + KMS por tenant (rotación).
  ai/
    router.py        route_request() — el Privacy Model Router.
    adapters.py      Adapters: Mock + OpenAI-compatible (OpenAI/Ollama/vLLM).
    resilience.py    Cadena de fallback de proveedores (privacy-safe).
    embeddings.py    Embedder local determinista (pluggable a proveedor real).
    vectorstore.py   Vector store pluggable (in-process / Qdrant).
    rag.py           Chunking, indexado (cifrado), retrieval + reranking, citas.
    cost.py          Estimación de tokens y costo por ruta.
  routers/           Endpoints HTTP.
tests/               pytest (security core + flujo API end-to-end).
```

## Endpoints

| Método | Ruta | Descripción |
|---|---|---|
| POST | `/auth/login` | Login (JWT). |
| GET | `/me` | Perfil, rol, tenant. |
| GET/POST | `/agents` | Listar / crear agentes. |
| GET | `/agents/{id}` | Detalle de agente. |
| GET | `/documents` | Listar documentos. |
| POST | `/documents/upload` | Carga → hash → clasificación → PII → índice. |
| DELETE | `/documents/{id}` | Borrar documento. |
| POST | `/chat` | Policy + RAG + router + adapter + auditoría. |
| GET/POST | `/workflows` `/workflows/{id}/run` | Catálogo y ejecución. |
| GET | `/audit` | Auditoría filtrable por tenant. |
| GET | `/audit/export` | Export SIEM (JSON Lines). |
| GET | `/usage` | Cost meter por ruta y agente. |
| POST | `/export/report` | Genera PDF/Markdown de un reporte o SOW. |
| GET | `/export/conversation/{id}` | Exporta transcripción (pdf/md). |
| GET | `/auth/sso/config` · POST `/auth/sso/callback` | SSO/OIDC opcional. |
| GET | `/admin/users` `/admin/routes` `/admin/security` | Admin (RBAC). |
| PUT | `/admin/tenant` | Política del tenant. |

## Ejecutar

```bash
python -m venv .venv && source .venv/bin/activate
pip install -r requirements.txt
uvicorn app.main:app --reload      # http://localhost:8000/docs
pytest                             # pruebas
```

Por defecto usa SQLite y el adapter MOCK (cero configuración). Configura
proveedores reales y/o Postgres en `.env` (ver `.env.example`).
