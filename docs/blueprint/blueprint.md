# Blueprint — Plataforma de AI Privada (México)

> Documento fuente con el que se diseñó MaestroAI. Versionado como referencia del equipo.
> Incluye los 3 flujogramas base en ./image1.png, image2.png, image3.png

Blueprint técnico para desarrollar unaPlataforma de AI Privada en México

Frontend user-friendly + backend multi-modelo + RAG seguro + auditoría + control de datos

Documento para programarlo en VS Code / Cursor / equipo de desarrollo

Tesis del producto

No competir como “otro ChatGPT”. Competir como una capa privada y gobernada para que empresas mexicanas usen AI sobre sus documentos y procesos sin exponer información sensible.

Elemento

Decisión recomendada

Mercado objetivo

Empresas mexicanas medianas y corporativas con documentos, procesos y datos sensibles.

Diferenciador

Privacy Model Router: decide cuándo usar modelo local, VPC privada, proveedor cloud o bloquear la operación.

MVP

Login por empresa, chat con RAG, carga segura de documentos, router de modelos, dashboard de auditoría/costo.

Primeros agentes

Document Intelligence, Cyber Diagnostic Agent, Proposal/SOW Agent, Executive Copilot.

Regla de privacidad

Si no es indispensable enviar el dato, no se envía. Si debe salir, se minimiza, anonimiza y audita.

Preparado para: Ángel Beltrán | Fecha: 21 de junio de 2026

Contenido

1. Resumen ejecutivo

2. Producto y posicionamiento

3. Flujogramas base

4. Arquitectura técnica objetivo

5. Seguridad, cifrado y no exposición de data

6. Backend multi-modelo y router de privacidad

7. Frontend user-friendly

8. Modelo de datos y APIs

9. Workflows operativos

10. Roadmap para programarlo

11. Backlog para VS Code / Cursor

12. Checklist de aceptación

13. Referencias

1. Resumen ejecutivo

El objetivo es construir una plataforma de AI empresarial para México con una experiencia simple para el usuario, pero con un backend serio de seguridad, ruteo de modelos, RAG, workflows y auditoría. La plataforma no debe venderse como un modelo de AI, sino como una capa de control que permite usar múltiples modelos sin perder gobierno sobre los datos.

Decisión estratégica

La ventaja no está en tener “tres modelos” atrás; la ventaja está en decidir automáticamente qué datos pueden salir, qué datos deben quedarse en privado, qué modelo conviene usar y cómo dejar evidencia auditable.

Objetivo

Descripción

Privacidad

Clasificar sensibilidad, minimizar datos, anonimizar PII y procesar local/VPC cuando el riesgo sea alto.

Usabilidad

Frontend tipo portal: agentes por área, carga de documentos, chat con fuentes, acciones y reportes.

Control económico

Medir tokens, costo por cliente, costo por agente, costo por workflow y ROI.

Gobernanza

RBAC, MFA, logs, políticas, aprobaciones humanas y retención controlada.

Escalabilidad

Arquitectura modular: frontend, API, AI Gateway, RAG, workflows, model serving y observabilidad.

2. Producto y posicionamiento

Nombre de categoría recomendado: Private AI Gateway + Vertical Agents. El producto debe ofrecer una capa segura para que empresas consulten documentos, generen reportes, automaticen procesos y usen agentes especializados sin enviar información sensible a proveedores externos de forma indiscriminada.

No vender como

Vender como

Otro ChatGPT

AI empresarial sin perder control de tus datos.

Tres modelos conectados

Router inteligente de privacidad, calidad y costo.

Un chatbot genérico

Agentes verticales para documentos, ciberseguridad, ventas, SOWs y centro de mando.

Consultoría de prompts

Plataforma recurrente + implementación + auditoría + workflows.

2.1 Usuarios y roles

Rol

Permisos principales

Super Admin

Administra tenants, planes, modelos, límites, facturación y políticas globales.

Admin Empresa

Configura usuarios, documentos, agentes, integraciones, permisos y retención.

Usuario Negocio

Usa agentes, consulta documentos autorizados y ejecuta acciones permitidas.

Security/Compliance

Revisa auditoría, incidentes, PII, salidas bloqueadas y reportes de cumplimiento.

Developer/Ops

Gestiona conectores, pipelines, deployments, logs técnicos y monitoreo.

3. Flujogramas base

Estos tres flujogramas son la lógica base para programar el producto. Deben convertirse en reglas del backend: clasificación de datos, selección de RAG/fine-tuning y pipeline seguro de entrenamiento ligero.

3.1 Arquitectura segura para AI

Regla de negocio: primero se clasifica sensibilidad; después se decide si el procesamiento es local, privado, anonimizado o externo.

3.2 Decisión: Prompt, RAG o Fine-Tuning

Regla de negocio: usar RAG para conocimiento cambiante; fine-tuning solo para comportamiento, formato o tareas repetitivas.

3.3 Pipeline seguro de fine-tuning

Regla de negocio: datasets versionados, anonimizados, cifrados y evaluados antes de producción.

4. Arquitectura técnica objetivo

La arquitectura debe separar experiencia de usuario, políticas, RAG, workflows, modelos y auditoría. Esto permite evolucionar cada capa sin rehacer toda la plataforma.

Frontend Web / Portal Empresas  ↓API Gateway + Auth + Tenant Isolation  ↓Policy Engine + Data Classifier + DLP  ↓AI Gateway / Privacy Model Router  ↓RAG Layer + Tools + Workflow Layer  ↓Model Layer:  - Local / Self-hosted  - VPC privada / managed open models  - NaN / volumen experimental  - OpenAI / Claude / Gemini / premium  ↓Observability + Audit + Billing + SIEM

Capa

Responsabilidad

Stack recomendado

Frontend

Portal, chat, carga de documentos, dashboards, configuración de agentes.

Next.js, React, Tailwind, shadcn/ui.

Backend API

Orquestación, reglas de negocio, endpoints, jobs, permisos.

FastAPI o Node.js/NestJS.

Auth

SSO, MFA, RBAC, sesiones, políticas por tenant.

Keycloak, Auth0, Clerk o Entra ID.

Policy Engine

Clasificación, DLP, minimización, bloqueo, aprobación humana.

Servicio propio + Presidio/DLP + reglas YAML.

AI Gateway

Ruteo de modelos, costos, fallback, logging, límites.

LiteLLM + router propio.

RAG

Indexación, embeddings, búsqueda vectorial, reranking y citas.

Qdrant o pgvector; reranker Qwen/Cohere/local.

Workflows

Acciones externas, aprobación, emails, CRM, tareas.

n8n self-hosted; Temporal para jobs críticos.

Model Serving

Inferencia local/privada.

Ollama lab; vLLM/TGI producción.

Observabilidad

Logs, métricas, calidad, trazabilidad, costo.

Langfuse, OpenTelemetry, Grafana, SIEM.

5. Seguridad, cifrado y no exposición de data

Principio no negociable

El cifrado es obligatorio, pero no suficiente. Si un tercero necesita leer el contenido para inferencia, el dato se descifra durante procesamiento. Para datos críticos: procesamiento local, VPC privada, minimización, anonimización y auditoría.

Control

Implementación

Clasificación de datos

public, internal, confidential, restricted. La clasificación decide ruta de modelo y permisos.

DLP/PII

Detectar nombres, emails, teléfonos, RFC, CURP, cuentas, direcciones, datos financieros, salud, secretos.

Minimización

Enviar solo fragmentos necesarios; nunca documentos completos salvo autorización explícita.

Anonimización

Reemplazar identificadores por tokens reversibles o irreversibles según caso.

Cifrado en tránsito

TLS 1.2/1.3; mTLS entre servicios críticos.

Cifrado en reposo

AES-256 en objetos, DB, backups y vector DB; KMS y rotación de llaves.

Cifrado en uso

Explorar confidential computing/TEE para clientes regulados o VPC dedicada.

RBAC + MFA

Permisos por tenant, workspace, agente, documento, acción y usuario.

No retención externa

Cuando se usen APIs externas, preferir planes/configuraciones con no-retención y contratos adecuados.

Auditoría

Guardar evento, usuario, documento, modelo, ruta, costo, clasificación y decisiones del policy engine.

// Ejemplo de clasificación de sensibilidadPUBLIC       -> proveedor externo permitidoINTERNAL     -> proveedor externo solo con minimizaciónCONFIDENTIAL -> VPC privada o modelo local; salida externa requiere aprobaciónRESTRICTED   -> local/self-hosted; no salida externa; auditoría obligatoria

6. Backend multi-modelo y router de privacidad

El usuario no debe elegir modelos manualmente. La plataforma debe decidir el modelo con base en sensibilidad, tarea, costo, latencia, calidad requerida y política del cliente.

Ruta

Cuándo usarla

Ejemplos

Local / self-hosted

Datos altamente sensibles o restringidos.

Contratos privados, PII, ciberseguridad, información financiera.

VPC privada / managed

Datos confidenciales con necesidad de escala y operación gestionada.

RAG empresarial, reportes internos, documentación por departamento.

NaN / open models volumen

Pruebas, generación sintética, bajo riesgo, coding agents.

Prompts masivos, datasets sintéticos, benchmarks, automatizaciones no sensibles.

Premium externo

Máxima calidad con datos públicos, anonimizados o mínimos.

Síntesis ejecutiva, redacción de alto nivel, razonamiento complejo.

Bloqueo

Cuando la política impide procesar o enviar datos.

PII sin permiso, documentos restringidos, prompts con exfiltración.

def route_request(user, tenant, task, documents, prompt):    classification = classify_data(documents, prompt)    pii = detect_pii(documents, prompt)    policy = load_policy(tenant, user)    if violates_policy(policy, classification, pii, task):        return BLOCK(reason="Policy violation")    minimized_context = minimize_context(documents, prompt, task)    redacted_context = redact_if_required(minimized_context, policy)    if classification == "RESTRICTED":        return LOCAL_MODEL(context=redacted_context, audit=True)    if classification == "CONFIDENTIAL":        if policy.allows_vpc:            return VPC_PRIVATE_MODEL(context=redacted_context, audit=True)        return LOCAL_MODEL(context=redacted_context, audit=True)    if task.requires_premium_reasoning and policy.allows_external:        return PREMIUM_MODEL(context=redacted_context, audit=True)    return COST_OPTIMIZED_OPEN_MODEL(context=redacted_context, audit=True)

7. Frontend user-friendly

El frontend debe ocultar la complejidad técnica. El cliente debe sentir que usa un portal empresarial simple, no una consola de modelos.

Pantalla

Funcionalidad

Dashboard

Agentes disponibles, uso mensual, costo, riesgos, documentos procesados y alertas.

Agentes

Crear, configurar y usar agentes por área: legal, ventas, ciberseguridad, finanzas, RH.

Documentos

Subir archivos, clasificar sensibilidad, detectar PII, crear índices RAG y gestionar retención.

Chat con fuentes

Respuesta con citas, fuente documental, ruta de privacidad, costo y acciones.

Workflows

Ejecutar acciones: crear SOW, enviar email, crear tarea, exportar PDF, actualizar CRM.

Auditoría

Buscar eventos por usuario, documento, modelo, riesgo, costo, salida bloqueada o PII.

Admin

Usuarios, roles, políticas, conectores, modelos habilitados, límites y llaves.

/app  /(auth)  /dashboard  /agents  /agents/[agentId]  /documents  /chat  /workflows  /audit  /settings  /admin/components  AgentCard.tsx  ChatWindow.tsx  SourceCitation.tsx  PrivacyBadge.tsx  CostMeter.tsx  DocumentUploader.tsx  AuditTable.tsx/lib  api.ts  auth.ts  policy.ts  types.ts

8. Modelo de datos y APIs

8.1 Entidades principales

Tabla

Campos clave

tenants

id, name, plan, region, kms_key_id, retention_policy, created_at

users

id, tenant_id, email, name, role, mfa_enabled, status

agents

id, tenant_id, name, type, system_prompt, tools, privacy_policy_id, status

documents

id, tenant_id, owner_id, filename, mime_type, sensitivity, pii_score, storage_uri, hash

document_chunks

id, document_id, chunk_index, text_hash, embedding_id, sensitivity, metadata

conversations

id, tenant_id, user_id, agent_id, title, created_at

messages

id, conversation_id, role, content_redacted, model_used, token_count, cost_estimate

model_routes

id, request_id, classification, selected_route, selected_model, reason

audit_events

id, tenant_id, user_id, event_type, object_type, object_id, risk_level, metadata

api_keys

id, tenant_id, provider, secret_ref, allowed_models, status

8.2 Endpoints mínimos

Método

Endpoint

Descripción

POST

/auth/login

Inicio de sesión o integración con SSO.

GET

/me

Perfil, roles, tenant y permisos.

POST

/documents/upload

Carga segura, hashing, storage y job de clasificación.

POST

/documents/{id}/classify

Clasificación de sensibilidad y PII.

POST

/documents/{id}/index

Chunking, embeddings, vector DB y metadata.

POST

/agents

Crear agente.

GET

/agents

Listar agentes autorizados.

POST

/chat

Enviar prompt; ejecuta policy engine, RAG y router de modelos.

POST

/workflows/{id}/run

Ejecutar workflow autorizado.

GET

/audit

Consultar auditoría filtrable.

GET

/usage

Tokens, costos, rutas, usuarios y ROI.

PUT

/policies/{id}

Actualizar política de privacidad y ruteo.

// Payload recomendado para /chat{  "tenant_id": "tnt_123",  "agent_id": "agt_cyber_diag",  "conversation_id": "conv_456",  "prompt": "Resume los riesgos principales del contrato",  "document_ids": ["doc_001", "doc_002"],  "privacy_mode": "auto",  "response_format": "markdown",  "human_approval_required": false}

9. Workflows operativos

Workflow

Pasos

Ingesta documental

Upload -> antivirus -> hash -> OCR si aplica -> clasificación -> PII -> chunking -> embeddings -> índice.

Consulta RAG

Prompt -> policy -> retrieval -> reranking -> minimización -> modelo -> respuesta con fuentes -> auditoría.

Generación de SOW

Input comercial -> plantilla -> RAG metodológico -> generación -> revisión humana -> export PDF/DOCX.

Diagnóstico cyber

Cuestionario -> scoring -> riesgos -> controles -> roadmap -> reporte ejecutivo.

Centro de mando

Conectores -> normalización -> KPIs -> insights AI -> alertas -> recomendaciones.

Fine-tuning ligero

Dataset -> anonimización -> versionado -> entrenamiento LoRA -> evals -> red team -> despliegue.

10. Roadmap para programarlo

Fase

Duración sugerida

Entregables

Fase 0: Diseño

1 semana

PRD, arquitectura, decisiones de stack, políticas de privacidad, wireframes.

Fase 1: MVP Base

3-4 semanas

Auth, tenants, dashboard, upload, chat básico, auditoría mínima.

Fase 2: RAG seguro

3-4 semanas

Clasificación, PII, chunking, Qdrant, citas, reranking, storage cifrado.

Fase 3: Router multi-modelo

2-3 semanas

Rutas local/VPC/external, costos, fallback, límites, logs completos.

Fase 4: Agentes verticales

3-6 semanas

Document Intelligence, Cyber Diagnostic, Proposal/SOW Agent.

Fase 5: Enterprise hardening

4-8 semanas

SSO, KMS, SIEM, private endpoints, DLP avanzado, QA seguridad.

11. Backlog para VS Code / Cursor

Este backlog está redactado para convertirlo en issues o prompts de Cursor/Claude Code. La recomendación es desarrollar por vertical slice: una funcionalidad completa de extremo a extremo antes de ampliar módulos.

Épica

Tarea concreta

Repositorio y base

Crear monorepo con apps/web, apps/api, packages/shared, packages/ui, infra/docker.

Auth multi-tenant

Implementar login, tenant_id en sesión, middleware de permisos y roles básicos.

Document upload

Endpoint de carga con storage local/S3, hash SHA-256, metadata y registro en DB.

Classifier service

Servicio que detecte sensibilidad y PII; guardar classification_result y pii_score.

Vector indexing

Chunking configurable, embeddings, Qdrant collection por tenant o namespace.

Chat endpoint

Implementar /chat con retrieval, policy engine, model router y respuesta con fuentes.

Privacy badges

Mostrar en frontend la ruta usada: local, VPC, external, blocked.

Audit log

Registrar cada evento relevante con user_id, tenant_id, object_id, route, cost, risk.

Model adapters

Crear adapters para OpenAI-compatible, Ollama, vLLM, NaN/OpenRouter y proveedor premium.

Cost meter

Calcular tokens/costo estimado por mensaje, conversación, agente y tenant.

Agent builder

Wizard para crear agente con nombre, área, fuentes, tools, política y límites.

Export reports

Generar DOCX/PDF de respuestas, diagnósticos o SOWs usando plantillas.

Security tests

Pruebas de prompt injection, exfiltración, PII leakage y autorización entre tenants.

Prompt sugerido para Cursor:"Implementa un endpoint POST /chat en FastAPI. Debe recibir tenant_id, agent_id, prompt y document_ids. Antes de llamar al modelo debe ejecutar: auth check, policy check, PII detection, retrieval en Qdrant, minimización de contexto, selección de modelo con route_request(), llamada al adapter seleccionado y escritura de audit_events. Usa tipos Pydantic y pruebas unitarias."

12. Checklist de aceptación

Categoría

Criterio de aceptación

Seguridad

Un usuario de tenant A no puede ver documentos, agentes, conversaciones ni auditoría de tenant B.

Privacidad

Documentos con PII se clasifican y no salen a proveedor externo salvo política explícita.

RAG

Toda respuesta basada en documentos muestra fuentes y fragmentos usados.

Auditoría

Cada llamada a modelo registra usuario, tenant, modelo, ruta, tokens, costo, sensibilidad y resultado.

Costo

El dashboard muestra costo estimado por tenant, agente, usuario y modelo.

UX

Un usuario no técnico puede subir documento, crear consulta y exportar resultado sin configurar modelos.

Calidad

Evals mínimas: accuracy, formato, alucinación, latency y seguridad.

Resiliencia

Si un proveedor falla, el router usa fallback permitido o informa bloqueo seguro.

Compliance

Existe política de retención, borrado de documentos y exportación de auditoría.

13. Referencias técnicas y regulatorias

Estas referencias deben revisarse durante diseño legal, seguridad y arquitectura. No sustituyen asesoría legal ni auditoría formal.

Ley Federal de Protección de Datos Personales en Posesión de los Particulares - Cámara de Diputados: https://www.diputados.gob.mx/LeyesBiblio/pdf/LFPDPPP.pdf

OWASP Top 10 for LLM Applications 2025: https://genai.owasp.org/llm-top-10/

NIST AI Risk Management Framework: https://www.nist.gov/itl/ai-risk-management-framework

OpenAI Enterprise Privacy: https://openai.com/enterprise-privacy/

NVIDIA Confidential Computing for AI: https://www.nvidia.com/en-sg/data-center/solutions/confidential-computing/

Siguiente paso recomendado: tomar este documento como PRD v0.1, cerrar decisiones de stack/cloud/legal y definir el primer cliente piloto con un caso de uso acotado.