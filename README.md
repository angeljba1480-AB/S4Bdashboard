# Private AI Platform — México 🇲🇽

> **Private AI Gateway + Vertical Agents.** AI empresarial sin perder control de
> tus datos. Implementa el [blueprint técnico](#blueprint) de una plataforma de
> AI privada: frontend user-friendly + backend multi-modelo + RAG seguro +
> auditoría + control de datos.

No es "otro ChatGPT". Es una **capa privada y gobernada** para que empresas
mexicanas usen AI sobre sus documentos y procesos sin exponer información
sensible. El diferenciador es el **Privacy Model Router**: decide
automáticamente si un dato se procesa **local**, en **VPC privada**, en un
**modelo abierto**, en **premium externo**, o si se **bloquea** — y siempre deja
evidencia auditable.

## Monorepo

```
apps/
  web/            Portal Next.js (App Router + Tailwind): dashboard, casos de uso,
                  flujogramas, documentos por área, chat con fuentes, notebooks,
                  acciones (Google/MS), integraciones, workflows, auditoría, admin.
  api/            Backend FastAPI: auth multi-tenant, policy engine, clasificador
                  de datos, detección PII (RFC/CURP/CLABE…), RAG, router de
                  privacidad, model adapters, auditoría y cost meter.
packages/
  shared/         Tipos TypeScript compartidos.
infra/
  docker-compose.yml  Stack local (Postgres, Qdrant, API, Web).
```

## Arranque rápido

### 1. Backend (API)
```bash
cd apps/api
python -m venv .venv && source .venv/bin/activate
pip install -r requirements.txt
uvicorn app.main:app --reload --port 8000
```
La primera ejecución crea la base SQLite y siembra datos demo.
Docs interactivas: http://localhost:8000/docs

### 2. Frontend (Web)
```bash
cd apps/web
cp .env.example .env.local
npm install
npm run dev
```
Portal: http://localhost:3000 · Login demo: `admin@maestroai.mx` / `demo1234`

### 3. Todo con Docker
```bash
docker compose -f infra/docker-compose.yml up --build
```

### Despliegue (Supabase + Vercel + NaN Builders)
Stack productivo: **Supabase** (Postgres + pgvector para el RAG), **Vercel**
(portal Next.js) y **NaN Builders** (ruta de modelos open/volumen). Guía paso a
paso en [`infra/DEPLOY.md`](infra/DEPLOY.md); migración pgvector en
[`infra/supabase/001_pgvector.sql`](infra/supabase/001_pgvector.sql).
Para usar Supabase como vector DB: `VECTOR_STORE=pgvector` + `DATABASE_URL` de Supabase.

## El diferenciador: Privacy Model Router

Cada `/chat` ejecuta este pipeline (sin que el usuario elija modelo):

```
prompt + documentos
  → clasificación de sensibilidad (public/internal/confidential/restricted)
  → detección de PII (RFC, CURP, CLABE, tarjetas, email, teléfono, salud, secretos)
  → policy engine (¿viola política? ¿prompt injection?)
  → retrieval RAG (vector search por tenant) + reranking
  → minimización + redacción de PII del contexto
  → route_request(): LOCAL | VPC | OPEN | PREMIUM | BLOCKED
  → adapter del modelo (mock por defecto; OpenAI/Ollama/vLLM si se configura)
  → respuesta con fuentes + auditoría + costo
```

Reglas (blueprint §6):

| Clasificación | Ruta | Regla |
|---|---|---|
| `RESTRICTED` | Local | Nunca sale; auditoría obligatoria |
| `CONFIDENTIAL` | VPC (o Local) | VPC privada si la política lo permite |
| PII detectado | VPC / Local | Nunca a proveedor externo por defecto |
| `INTERNAL` / `PUBLIC` | Open ([NaN Builders](#proveedores)) / Premium | Modelo abierto de volumen, o premium si requiere razonamiento |
| Violación de política | Blocked | Prompt injection / exfiltración |

## Modelos y configuración

El **MOCK adapter funciona sin configurar nada**, así la plataforma corre de
extremo a extremo. Para usar proveedores reales, edita `apps/api/.env`
(`PREMIUM_ENABLED`, `VPC_ENABLED`, `LOCAL_ENABLED`, etc.). El panel **Admin**
muestra qué rutas usan proveedor real vs mock, y el proveedor de cada ruta.

### Proveedores

| Ruta | Proveedor | Notas |
|---|---|---|
| Local | Self-hosted (Ollama) | Datos restringidos, nunca salen |
| VPC | vLLM / TGI en VPC privada | Datos confidenciales / con PII |
| **Open / volumen** | **NaN Builders** | Modelos abiertos optimizados en costo; endpoint OpenAI-compatible (`OPEN_BASE_URL`, `OPEN_API_KEY`, `OPEN_MODEL`) |
| Premium | OpenAI / Claude / Gemini | Razonamiento de alto nivel con datos no sensibles |

> **NaN Builders** es el proveedor elegido para la ruta de modelos abiertos /
> volumen. Como expone una API OpenAI-compatible, basta con `OPEN_ENABLED=true`
> y configurar `OPEN_BASE_URL` / `OPEN_API_KEY` / `OPEN_MODEL`.

## Pruebas

```bash
cd apps/api && source .venv/bin/activate && pytest
```
Cubre los criterios de aceptación del blueprint: detección PII, clasificación,
decisiones del router, bloqueo de prompt injection, redacción, aislamiento entre
tenants y el flujo completo de `/chat`.

## Roadmap (blueprint §10)

- [x] **Fase 1 — MVP base**: auth multi-tenant, dashboard, upload, chat, auditoría.
- [x] **Fase 2 — RAG seguro**: clasificación, PII, chunking, embeddings, citas, reranking.
- [x] **Fase 3 — Router multi-modelo**: rutas local/VPC/open/premium, costos, fallback, mock adapter.
- [x] **Fase 4 — Agentes verticales**: Document Intelligence, Cyber Diagnostic, Proposal/SOW, Executive Copilot.
- [x] **Fase 5 — Enterprise hardening**:
  - **Cifrado en reposo** AES-256-GCM con abstracción KMS y llaves por tenant + rotación (`KMS_KEY_VERSION`).
  - **SSO/OIDC** pluggable (authorization-code flow + auto-provisión de usuario/tenant).
  - **Vector store productivo** Qdrant (pluggable; in-process por defecto).
  - **SIEM**: export de auditoría en JSONL.
  - **Resiliencia**: cadena de fallback de proveedores que nunca debilita la privacidad.
  - **Export** de reportes/SOWs/conversaciones a PDF y Markdown.
  - **Red-teaming**: suite de pruebas de prompt injection, exfiltración, fuga de PII y aislamiento entre tenants.
  - _Pendiente_: confidential computing/TEE y wrapping de llaves con KMS real (AWS/GCP/Vault).

## Documentación

| Guía | Para qué |
|---|---|
| [`docs/BLUEPRINT.md`](docs/BLUEPRINT.md) · [`docs/blueprint/`](docs/blueprint/) | PRD y blueprint original + los 3 flujogramas base |
| [`docs/CORREO-OAUTH-SETUP.md`](docs/CORREO-OAUTH-SETUP.md) | Conectar correo/agenda (Outlook/Gmail/IMAP) |
| [`docs/ACCIONES-ESCRITURA-SETUP.md`](docs/ACCIONES-ESCRITURA-SETUP.md) | **Habilitar acciones de escritura** (toolkit Google/MS): scopes + reconexión |
| [`docs/INTEGRATIONS.md`](docs/INTEGRATIONS.md) | API `/v1`, conectores, toolkit de acciones, Drive, modelos externos, sistemas a la medida |
| [`docs/MANUAL-ADMIN.md`](docs/MANUAL-ADMIN.md) · [`docs/MANUAL-USUARIO.md`](docs/MANUAL-USUARIO.md) | Manuales de admin y usuario |
| [`docs/MCP.md`](docs/MCP.md) · [`docs/OLLAMA-SETUP.md`](docs/OLLAMA-SETUP.md) | MCP de trámites y modelos locales |

## Blueprint

El diseño completo está documentado en
[`docs/BLUEPRINT.md`](docs/BLUEPRINT.md) (PRD v0.1 derivado del documento
original). Referencias regulatorias: LFPDPPP, OWASP Top 10 for LLM Apps 2025,
NIST AI RMF.
