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
  web/            Portal Next.js (App Router + Tailwind): dashboard, agentes,
                  documentos, chat con fuentes, workflows, auditoría, admin.
  api/            Backend FastAPI: auth multi-tenant, policy engine, clasificador
                  de datos, detección PII (RFC/CURP/CLABE…), RAG, router de
                  privacidad, model adapters, auditoría y cost meter.
  s4b-dashboard/  Dashboards mockup originales de Silent4Business (Vite + React).
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
Portal: http://localhost:3000 · Login demo: `admin@s4b.mx` / `demo1234`

### 3. Todo con Docker
```bash
docker compose -f infra/docker-compose.yml up --build
```

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
| `INTERNAL` / `PUBLIC` | Open / Premium | Modelo abierto, o premium si requiere razonamiento |
| Violación de política | Blocked | Prompt injection / exfiltración |

## Modelos y configuración

El **MOCK adapter funciona sin configurar nada**, así la plataforma corre de
extremo a extremo. Para usar proveedores reales, edita `apps/api/.env`
(`PREMIUM_ENABLED`, `VPC_ENABLED`, `LOCAL_ENABLED`, etc.). El panel **Admin**
muestra qué rutas usan proveedor real vs mock.

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
- [ ] **Fase 5 — Enterprise hardening**: SSO real, KMS, SIEM, Qdrant/pgvector productivo, DLP avanzado, confidential computing.

## Blueprint

El diseño completo está documentado en
[`docs/BLUEPRINT.md`](docs/BLUEPRINT.md) (PRD v0.1 derivado del documento
original). Referencias regulatorias: LFPDPPP, OWASP Top 10 for LLM Apps 2025,
NIST AI RMF.
