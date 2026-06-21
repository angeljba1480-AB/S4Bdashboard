# PRD v0.1 — Plataforma de AI Privada en México

> Derivado del *Blueprint técnico para desarrollar una Plataforma de AI Privada
> en México*. Preparado para: Ángel Beltrán.

## 1. Tesis del producto
No competir como "otro ChatGPT". Competir como una **capa privada y gobernada**
para que empresas mexicanas usen AI sobre sus documentos y procesos sin exponer
información sensible.

**Regla de privacidad:** si no es indispensable enviar el dato, no se envía. Si
debe salir, se minimiza, anonimiza y audita.

## 2. Posicionamiento
**Categoría:** Private AI Gateway + Vertical Agents.

| No vender como | Vender como |
|---|---|
| Otro ChatGPT | AI empresarial sin perder control de tus datos |
| Tres modelos conectados | Router inteligente de privacidad, calidad y costo |
| Un chatbot genérico | Agentes verticales (documentos, ciberseguridad, ventas, SOWs, mando) |
| Consultoría de prompts | Plataforma recurrente + implementación + auditoría + workflows |

### Roles (RBAC)
Super Admin · Admin Empresa · Usuario Negocio · Security/Compliance · Developer/Ops.

## 3. Arquitectura objetivo
```
Frontend Web / Portal Empresas
  → API Gateway + Auth + Tenant Isolation
  → Policy Engine + Data Classifier + DLP
  → AI Gateway / Privacy Model Router
  → RAG Layer + Tools + Workflow Layer
  → Model Layer: Local · VPC privada · Open volumen · Premium externo
  → Observability + Audit + Billing + SIEM
```

| Capa | Stack recomendado | Stack en este MVP |
|---|---|---|
| Frontend | Next.js, React, Tailwind, shadcn/ui | Next.js + Tailwind |
| Backend API | FastAPI o NestJS | FastAPI |
| Auth | Keycloak/Auth0/Clerk/Entra | JWT + RBAC (PBKDF2) |
| Policy Engine | Servicio + Presidio/DLP + YAML | `security/` propio (regex MX + heurística) |
| AI Gateway | LiteLLM + router propio | `ai/router.py` + adapters |
| RAG | Qdrant/pgvector + reranker | Vector store in-proc (pluggable a Qdrant) |
| Workflows | n8n + Temporal | Catálogo + runner simulado |
| Model Serving | Ollama lab; vLLM/TGI prod | Mock + adapters OpenAI-compatible |
| Observabilidad | Langfuse, OTel, Grafana, SIEM | audit_events + cost meter |

## 4. Seguridad (§5)
Clasificación `public/internal/confidential/restricted` decide ruta y permisos.
DLP/PII detecta nombres, emails, teléfonos, RFC, CURP, cuentas, financieros,
salud y secretos. Cifrado en tránsito (TLS/mTLS), en reposo (AES-256 + KMS) y
exploración de cifrado en uso (TEE). RBAC + MFA. No retención externa. Auditoría
de cada evento.

```
PUBLIC       -> proveedor externo permitido
INTERNAL     -> externo solo con minimización
CONFIDENTIAL -> VPC privada o local; salida externa requiere aprobación
RESTRICTED   -> local/self-hosted; sin salida externa; auditoría obligatoria
```

## 5. Modelo de datos (§8)
`tenants, users, agents, documents, document_chunks, conversations, messages,`
`model_routes, audit_events, api_keys` — implementado en `app/models.py`.

## 6. Workflows (§9)
Ingesta documental · Consulta RAG · Generación de SOW · Diagnóstico cyber ·
Centro de mando · Fine-tuning ligero.

## 7. Roadmap (§10)
Fase 0 Diseño · Fase 1 MVP base · Fase 2 RAG seguro · Fase 3 Router multi-modelo
· Fase 4 Agentes verticales · Fase 5 Enterprise hardening.

## 8. Checklist de aceptación (§12)
- **Seguridad:** un tenant A no puede ver datos del tenant B. ✅ (tests)
- **Privacidad:** documentos con PII no salen a externo salvo política. ✅
- **RAG:** toda respuesta documental muestra fuentes. ✅
- **Auditoría:** cada llamada registra usuario, tenant, modelo, ruta, tokens,
  costo, sensibilidad y resultado. ✅
- **Costo:** dashboard con costo por tenant/agente/ruta. ✅
- **UX:** usuario no técnico sube documento, consulta y exporta sin configurar
  modelos. ✅ (export pendiente Fase 5)
- **Resiliencia:** fallback de proveedor o bloqueo seguro. ✅ (mock fallback)

## 9. Referencias
- LFPDPPP — https://www.diputados.gob.mx/LeyesBiblio/pdf/LFPDPPP.pdf
- OWASP Top 10 for LLM Applications 2025 — https://genai.owasp.org/llm-top-10/
- NIST AI Risk Management Framework — https://www.nist.gov/itl/ai-risk-management-framework
- OpenAI Enterprise Privacy — https://openai.com/enterprise-privacy/
- NVIDIA Confidential Computing — https://www.nvidia.com/en-sg/data-center/solutions/confidential-computing/
