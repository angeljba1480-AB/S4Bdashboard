"""Database entities — mirrors the data model from the blueprint (section 8.1)."""
from __future__ import annotations

import uuid
from datetime import datetime
from enum import Enum

from sqlmodel import Field, SQLModel


def _uuid(prefix: str) -> str:
    return f"{prefix}_{uuid.uuid4().hex[:16]}"


# --- Enumerations -----------------------------------------------------------
class Sensitivity(str, Enum):
    PUBLIC = "public"
    INTERNAL = "internal"
    CONFIDENTIAL = "confidential"
    RESTRICTED = "restricted"


class Role(str, Enum):
    SUPER_ADMIN = "super_admin"
    ADMIN = "admin"          # Admin Empresa
    USER = "user"            # Usuario Negocio
    SECURITY = "security"    # Security / Compliance
    DEVOPS = "devops"        # Developer / Ops


class ModelRoute(str, Enum):
    LOCAL = "local"
    VPC = "vpc"
    OPEN = "open"
    PREMIUM = "premium"
    BLOCKED = "blocked"


# --- Tables -----------------------------------------------------------------
class Tenant(SQLModel, table=True):
    __tablename__ = "tenants"
    id: str = Field(default_factory=lambda: _uuid("tnt"), primary_key=True)
    name: str
    plan: str = "starter"
    country: str = "MX"            # ISO code; LATAM localization (default México)
    region: str = "mx-central"
    kms_key_id: str = Field(default_factory=lambda: _uuid("kms"))
    retention_days: int = 365
    allows_external: bool = True
    allows_vpc: bool = True
    # White-label branding (per tenant). Empty -> platform defaults.
    brand_name: str = ""
    brand_logo_url: str = ""
    brand_color: str = ""          # primary hex, e.g. #7c3aed
    brand_tagline: str = ""
    custom_domain: str = ""        # dominio propio del cliente, e.g. plataforma.sucliente.com
    # Remitente de soporte por tenant: el buzón desde el que SALEN los correos de
    # las automatizaciones (no la cuenta personal de quien conectó). Vacío -> usa
    # la conexión del usuario que ejecuta.
    support_account_id: str = ""   # OAuthToken.id del buzón de soporte
    support_from: str = ""         # alias "From" opcional (requiere send-as verificado)
    support_from_name: str = ""    # nombre para mostrar del remitente
    # Subscription: platform is sold as setup + annual prepaid by seats. App
    # Studio production deploys are charged separately (pay-to-prod).
    seats_licensed: int = 5
    subscription_status: str = "trial"   # trial | active | expired
    subscription_renews_at: str = ""     # ISO date
    setup_fee_paid: bool = False
    annual_fee_mxn: int = 0
    # Per-tenant n8n override (advanced/BYO). Empty base_url -> managed n8n.
    n8n_webhook_base_url: str = ""
    n8n_api_key_enc: str = ""        # encrypted at rest (AES-256-GCM per tenant)
    n8n_auth_header: str = ""        # optional; falls back to global header
    n8n_provisioned: bool = False    # managed workflows auto-created for tenant
    created_at: datetime = Field(default_factory=datetime.utcnow)


class CompanyProfile(SQLModel, table=True):
    """Per-company configuration captured in an onboarding workflow.

    Pre-loads the business context (who they are, their areas/org chart, the
    tech they use, tone) so every use case runs pre-configured and integrated —
    the user gives less and the output lands closer to ready. One row per tenant.
    """
    __tablename__ = "company_profiles"
    id: str = Field(default_factory=lambda: _uuid("cprof"), primary_key=True)
    tenant_id: str = Field(index=True, foreign_key="tenants.id")
    industry: str = ""             # giro / sector (ej. retail, fintech, salud)
    company_size: str = ""         # micro | pequeña | mediana | grande
    org_type: str = "privada"      # privada (IP) | gobierno — define si aplica lo de gobierno
    gov_tramites: str = ""         # "1" si una empresa IP opta por trámites/licitaciones de gobierno
    description: str = ""          # contexto: a qué se dedica la empresa
    audience: str = ""             # clientes / mercado objetivo
    value_prop: str = ""           # propuesta de valor / diferenciadores
    goals: str = ""                # objetivos del negocio
    tone: str = ""                 # tono de comunicación (formal, cercano, ...)
    website: str = ""
    areas: str = "[]"              # JSON list [{name, responsible, email}]
    tech_stack: str = "[]"         # JSON list of tools/systems they use
    completed: bool = False        # onboarding workflow finished
    created_at: datetime = Field(default_factory=datetime.utcnow)
    updated_at: datetime = Field(default_factory=datetime.utcnow)


class User(SQLModel, table=True):
    __tablename__ = "users"
    id: str = Field(default_factory=lambda: _uuid("usr"), primary_key=True)
    tenant_id: str = Field(index=True, foreign_key="tenants.id")
    email: str = Field(index=True)
    name: str
    role: Role = Role.USER
    area: str = ""                 # área a la que pertenece ("" = sin área / general)
    license: str = "basic"        # nivel de licencia (basic | pro | enterprise)
    password_hash: str = ""
    mfa_enabled: bool = False
    mfa_secret_enc: str = ""        # secreto TOTP cifrado (pendiente hasta verificar)
    mfa_backup_codes: str = ""      # hashes de códigos de respaldo (un solo uso)
    callmebot_phone: str = ""       # WhatsApp vía CallMeBot: número en formato intl (+52...)
    callmebot_apikey_enc: str = ""  # apikey de CallMeBot, cifrada
    status: str = "active"
    created_at: datetime = Field(default_factory=datetime.utcnow)


class Agent(SQLModel, table=True):
    __tablename__ = "agents"
    id: str = Field(default_factory=lambda: _uuid("agt"), primary_key=True)
    tenant_id: str = Field(index=True, foreign_key="tenants.id")
    name: str
    type: str = "general"          # document_intelligence, cyber_diagnostic, ...
    area: str = "general"          # legal, ventas, ciberseguridad, finanzas, rh
    system_prompt: str = ""
    tools: str = ""                # comma separated tool ids
    privacy_mode: str = "auto"     # auto | local_only | no_external
    requires_premium_reasoning: bool = False
    status: str = "active"
    created_at: datetime = Field(default_factory=datetime.utcnow)


class Document(SQLModel, table=True):
    __tablename__ = "documents"
    id: str = Field(default_factory=lambda: _uuid("doc"), primary_key=True)
    tenant_id: str = Field(index=True, foreign_key="tenants.id")
    owner_id: str = Field(foreign_key="users.id")
    filename: str
    mime_type: str = "text/plain"
    area: str = ""                 # organizational area (Legal, Ventas, RH, …)
    category: str = ""            # document type key (catalog) — e.g. propuesta_comercial
    sensitivity: Sensitivity = Sensitivity.INTERNAL
    pii_score: float = 0.0
    pii_types: str = ""            # comma separated
    storage_uri: str = ""
    hash: str = ""
    text: str = ""                 # extracted text (MVP keeps it inline)
    indexed: bool = False
    created_at: datetime = Field(default_factory=datetime.utcnow)


class DocumentCategory(SQLModel, table=True):
    """Per-tenant catalog of document types (extensible). Built-in defaults are
    marked `system` and can't be deleted; users/recipes can add new ones."""
    __tablename__ = "document_categories"
    id: str = Field(default_factory=lambda: _uuid("dcat"), primary_key=True)
    tenant_id: str = Field(index=True, foreign_key="tenants.id")
    key: str = ""                  # slug, unique per tenant
    label: str = ""
    description: str = ""
    system: bool = False           # built-in default (protected from deletion)
    created_at: datetime = Field(default_factory=datetime.utcnow)


class DocumentChunk(SQLModel, table=True):
    __tablename__ = "document_chunks"
    id: str = Field(default_factory=lambda: _uuid("chk"), primary_key=True)
    tenant_id: str = Field(index=True, foreign_key="tenants.id")
    document_id: str = Field(index=True, foreign_key="documents.id")
    chunk_index: int = 0
    text: str = ""
    text_hash: str = ""
    sensitivity: Sensitivity = Sensitivity.INTERNAL
    embedding: str = ""            # JSON-encoded float vector


class ActionRequest(SQLModel, table=True):
    """A Google/Microsoft toolkit action. Read actions run immediately; write
    actions (send mail, create event, write a sheet…) are gated on human approval
    before execution, per the blueprint's 'tú apruebas' principle."""
    __tablename__ = "action_requests"
    id: str = Field(default_factory=lambda: _uuid("act"), primary_key=True)
    tenant_id: str = Field(index=True, foreign_key="tenants.id")
    user_id: str = Field(index=True, foreign_key="users.id")
    provider: str = ""             # google | microsoft
    action: str = ""              # action id from the catalog
    params: str = "{}"            # JSON
    status: str = "pending"        # pending | executed | failed | rejected
    result: str = ""
    created_at: datetime = Field(default_factory=datetime.utcnow)


class MemoryItem(SQLModel, table=True):
    """Persistent memory of past work (chat answers, recipe outputs, notebook
    artifacts, manual notes). Taggable (CMS-style) and semantically searchable so
    the user can recall: '¿recuerdas el trabajo C?'. Area-scoped like documents."""
    __tablename__ = "memory_items"
    id: str = Field(default_factory=lambda: _uuid("mem"), primary_key=True)
    tenant_id: str = Field(index=True, foreign_key="tenants.id")
    user_id: str = Field(index=True, foreign_key="users.id")
    title: str = ""
    content: str = ""
    source: str = "manual"         # chat | recipe | notebook | manual
    source_id: str = ""
    tags: str = "[]"              # JSON list
    area: str = ""
    embedding: str = ""            # JSON float vector for semantic recall
    created_at: datetime = Field(default_factory=datetime.utcnow)


class ActionGrant(SQLModel, table=True):
    """Standing authorization: a user opted to auto-approve a given action so it
    runs without asking each time. Revocable. (Set via 'Permitir siempre'.)"""
    __tablename__ = "action_grants"
    id: str = Field(default_factory=lambda: _uuid("agr"), primary_key=True)
    tenant_id: str = Field(index=True, foreign_key="tenants.id")
    user_id: str = Field(index=True, foreign_key="users.id")
    action: str = ""
    created_at: datetime = Field(default_factory=datetime.utcnow)


class AgentPlaybook(SQLModel, table=True):
    """Receta de acciones guardada: una instrucción en lenguaje natural (posible
    multi-paso, con encadenamiento {{stepN}}) que el agente vuelve a ejecutar a
    demanda. Ej.: 'Cierre semanal: lee la hoja X, resume y publica en Teams'."""
    __tablename__ = "agent_playbooks"
    id: str = Field(default_factory=lambda: _uuid("pbk"), primary_key=True)
    tenant_id: str = Field(index=True, foreign_key="tenants.id")
    user_id: str = Field(index=True, foreign_key="users.id")
    name: str = ""
    instruction: str = ""
    auto_approve: bool = False
    created_at: datetime = Field(default_factory=datetime.utcnow)


class N8nRecipe(SQLModel, table=True):
    """Receta de automatización a la medida: un workflow propio (DB, SOAP, app interna)
    expuesto como webhook. Soporta **n8n** (webhook_path sobre el n8n del tenant) y
    **Zapier** (webhook_url completo del Catch Hook del Zap). MaestroAI lo dispara con
    un payload y lo ofrece al agente como herramienta. La gobernanza (clasificación/
    PII/auditoría) sigue en la API; el motor solo recibe el payload parametrizado."""
    __tablename__ = "n8n_recipes"
    id: str = Field(default_factory=lambda: _uuid("rcp"), primary_key=True)
    tenant_id: str = Field(index=True, foreign_key="tenants.id")
    provider: str = "n8n"          # n8n | zapier
    name: str = ""
    description: str = ""
    category: str = "custom"       # db | soap | app | custom
    webhook_path: str = ""        # n8n: ruta del webhook (p. ej. "erp-clientes")
    webhook_url: str = ""         # zapier: URL completa del Catch Hook
    params: str = "[]"            # JSON list de nombres de parámetro esperados
    enabled: bool = True
    created_at: datetime = Field(default_factory=datetime.utcnow)


class AlertRule(SQLModel, table=True):
    """Regla de alerta configurable: cuando ocurre un evento (event_type) la plataforma
    notifica por los canales elegidos. Canales: 'popup' (in-app) y/o 'webhook' (POST a
    una URL — sirve para Slack/Teams/correo vía n8n o Zapier). Por usuario y tenant."""
    __tablename__ = "alert_rules"
    id: str = Field(default_factory=lambda: _uuid("alr"), primary_key=True)
    tenant_id: str = Field(index=True, foreign_key="tenants.id")
    user_id: str = Field(index=True, foreign_key="users.id")
    name: str = ""
    event_type: str = "test"       # test | finetune | workflow | recipe | action | antivirus | ingest
    channels: str = '["popup"]'   # JSON list: popup | webhook | telegram | whatsapp
    webhook_url: str = ""         # destino del canal webhook (y de whatsapp vía proveedor/Zapier)
    telegram_token: str = ""      # canal telegram: token del bot
    telegram_chat_id: str = ""    # canal telegram: chat/grupo destino
    schedule: str = ""            # "" = tiempo real | "daily" | "weekly" (digest programado)
    last_digest_at: str = ""      # ISO del último digest enviado (solo reglas programadas)
    enabled: bool = True
    created_at: datetime = Field(default_factory=datetime.utcnow)


class Notification(SQLModel, table=True):
    """Notificación in-app (pop-up): una alerta entregada a un usuario. Se marca leída."""
    __tablename__ = "notifications"
    id: str = Field(default_factory=lambda: _uuid("ntf"), primary_key=True)
    tenant_id: str = Field(index=True, foreign_key="tenants.id")
    user_id: str = Field(index=True, foreign_key="users.id")
    title: str = ""
    body: str = ""
    level: str = "info"            # info | warn | error
    event_type: str = ""
    read: bool = False
    created_at: datetime = Field(default_factory=datetime.utcnow)


class DataSource(SQLModel, table=True):
    """Conector a sistemas a la medida sin API: una fuente de datos (hoy base de
    datos de SOLO LECTURA). Guarda una consulta SELECT y, al importar, vuelca el
    resultado al repositorio + índice RAG. Credenciales cifradas."""
    __tablename__ = "data_sources"
    id: str = Field(default_factory=lambda: _uuid("ds"), primary_key=True)
    tenant_id: str = Field(index=True, foreign_key="tenants.id")
    name: str = ""
    kind: str = "db"              # db (SQLAlchemy DSN) · futuro: sftp/csv
    dsn_enc: str = ""             # SQLAlchemy URL cifrada
    query: str = ""              # SELECT … (solo lectura)
    area: str = ""
    category: str = ""
    created_at: datetime = Field(default_factory=datetime.utcnow)


class SftpConnector(SQLModel, table=True):
    """Conector SFTP (solo lectura) para sistemas legados sin API: trae archivos de un
    servidor SFTP (un archivo o un directorio), extrae su texto (PDF/DOCX/CSV/txt) y los
    importa al repositorio + índice RAG. Credenciales (password o llave privada) cifradas."""
    __tablename__ = "sftp_connectors"
    id: str = Field(default_factory=lambda: _uuid("sftp"), primary_key=True)
    tenant_id: str = Field(index=True, foreign_key="tenants.id")
    name: str = ""
    host: str = ""
    port: int = 22
    username: str = ""
    auth_type: str = "password"    # password | key
    secret_enc: str = ""          # password o llave privada PEM, cifrada
    remote_path: str = ""         # archivo o directorio remoto
    area: str = ""
    category: str = ""
    created_at: datetime = Field(default_factory=datetime.utcnow)


class SharepointSource(SQLModel, table=True):
    """Conector SharePoint (solo lectura) vía Microsoft Graph con la cuenta MS
    conectada del usuario (delegado): lista archivos de un sitio/carpeta y los
    importa al repositorio + RAG. Útil para Finanzas (carpeta 'Proyectos Finanzas')."""
    __tablename__ = "sharepoint_sources"
    id: str = Field(default_factory=lambda: _uuid("sp"), primary_key=True)
    tenant_id: str = Field(index=True, foreign_key="tenants.id")
    name: str = ""
    site_url: str = ""             # https://contoso.sharepoint.com/sites/Finanzas
    folder: str = ""              # ruta relativa dentro del drive (ej. "Proyectos Finanzas")
    area: str = ""
    category: str = ""
    created_at: datetime = Field(default_factory=datetime.utcnow)


class KnownError(SQLModel, table=True):
    """KEDB — base de errores conocidos (operación de ciberseguridad/SOC).

    Módulo gateado por perfil cyber. `scope`:
    - 'tenant': error conocido propio del cliente.
    - 'shared': error conocido cross-cliente, curado y SANITIZADO por el operador
      (sin datos del cliente origen), visible para todos los tenants cyber.
    """
    __tablename__ = "known_errors"
    id: str = Field(default_factory=lambda: _uuid("kerr"), primary_key=True)
    tenant_id: str = Field(index=True, foreign_key="tenants.id")
    scope: str = "tenant"          # tenant | shared
    title: str = ""
    symptom: str = ""             # síntoma observado
    cause: str = ""               # causa raíz
    resolution: str = ""          # solución / workaround
    product: str = ""             # sistema/herramienta afectada (firewall, SIEM, EDR…)
    severity: str = "medium"       # low | medium | high | critical
    tags: str = ""                # csv
    status: str = "published"      # draft | published
    source: str = ""              # nota de origen (sanitizada)
    created_by: str = ""
    created_at: datetime = Field(default_factory=datetime.utcnow)
    updated_at: datetime = Field(default_factory=datetime.utcnow)


class OdataSource(SQLModel, table=True):
    """Fuente OData de SOLO lectura (SAP S/4HANA y compatibles): hace GET a un Entity
    Set, trae las filas y las importa al repositorio + RAG. Credencial cifrada.
    Las lecturas no requieren X-CSRF-Token (eso es solo para escrituras)."""
    __tablename__ = "odata_sources"
    id: str = Field(default_factory=lambda: _uuid("odata"), primary_key=True)
    tenant_id: str = Field(index=True, foreign_key="tenants.id")
    name: str = ""
    base_url: str = ""             # URL del Entity Set, e.g. https://host/sap/opu/odata/sap/SRV/Set
    auth_type: str = "basic"       # basic | bearer
    username: str = ""
    secret_enc: str = ""          # password (basic) o token (bearer), cifrado
    odata_filter: str = ""         # $filter opcional
    select: str = ""              # $select opcional
    top: int = 0                   # $top opcional (0 = por defecto)
    area: str = ""
    category: str = ""
    created_at: datetime = Field(default_factory=datetime.utcnow)


class FinanceDataset(SQLModel, table=True):
    """Dataset del Tablero Financiero cargado por el cliente (self-service), por tenant.

    El usuario sube su dataset curado (JSON) o sus Excel/zip y la plataforma lo guarda
    aquí, **cifrado**. El tablero lee de este registro primero; si no existe, cae al
    dataset inyectado por entorno o al demo. Una fila por tenant (el último cargado)."""
    __tablename__ = "finance_datasets"
    tenant_id: str = Field(primary_key=True, foreign_key="tenants.id")
    payload_enc: str = ""          # JSON del dataset, cifrado
    source: str = ""              # "json" | "excel" | "excel+json"
    filename: str = ""            # nombre(s) del/los archivo(s) cargado(s)
    updated_at: datetime = Field(default_factory=datetime.utcnow)
    updated_by: str = ""


class GeneratedImage(SQLModel, table=True):
    """Imagen generada de texto (text-to-image) vía el proveedor abierto (NaN/FLUX).
    Se guarda una copia en la plataforma (b64) para gobernanza y para que la galería
    sobreviva aunque expire el enlace del proveedor. Por área + auditada."""
    __tablename__ = "generated_images"
    id: str = Field(default_factory=lambda: _uuid("img"), primary_key=True)
    tenant_id: str = Field(index=True, foreign_key="tenants.id")
    owner_id: str = Field(foreign_key="users.id")
    prompt: str = ""
    model: str = ""
    size: str = ""               # ej. 1024x1024
    provider: str = ""
    source_url: str = ""         # enlace devuelto por el proveedor (puede caducar)
    data_b64: str = ""           # copia almacenada (image/png base64)
    mime_type: str = "image/png"
    area: str = ""
    created_at: datetime = Field(default_factory=datetime.utcnow)


class PlatformSetting(SQLModel, table=True):
    """Runtime key/value config set from the admin UI (overrides env defaults).
    Used for token-efficiency controls (condensación, tope de gasto) y contadores."""
    __tablename__ = "platform_settings"
    key: str = Field(primary_key=True)
    value: str = ""
    updated_at: datetime = Field(default_factory=datetime.utcnow)


class ProviderSetting(SQLModel, table=True):
    """Runtime config for an external model route (premium / open), set from the
    admin UI instead of env vars. API key is encrypted at rest. Global (platform)."""
    __tablename__ = "provider_settings"
    id: str = Field(default_factory=lambda: _uuid("prov"), primary_key=True)
    route: str = Field(index=True)   # "premium" | "open"
    enabled: bool = False
    base_url: str = ""
    model: str = ""
    api_key_enc: str = ""
    updated_at: datetime = Field(default_factory=datetime.utcnow)


class Notebook(SQLModel, table=True):
    """A NotebookLM-style workspace: a named set of source documents the user can
    query and turn into artifacts (summary, FAQ, study guide…), grounded ONLY in
    those sources via the existing RAG index."""
    __tablename__ = "notebooks"
    id: str = Field(default_factory=lambda: _uuid("nb"), primary_key=True)
    tenant_id: str = Field(index=True, foreign_key="tenants.id")
    user_id: str = Field(index=True, foreign_key="users.id")
    name: str = "Nuevo notebook"
    document_ids: str = "[]"       # JSON list of Document ids (the sources)
    created_at: datetime = Field(default_factory=datetime.utcnow)
    updated_at: datetime = Field(default_factory=datetime.utcnow)


class Conversation(SQLModel, table=True):
    __tablename__ = "conversations"
    id: str = Field(default_factory=lambda: _uuid("conv"), primary_key=True)
    tenant_id: str = Field(index=True, foreign_key="tenants.id")
    user_id: str = Field(foreign_key="users.id")
    agent_id: str = Field(foreign_key="agents.id")
    title: str = "Nueva conversación"
    created_at: datetime = Field(default_factory=datetime.utcnow)


class Message(SQLModel, table=True):
    __tablename__ = "messages"
    id: str = Field(default_factory=lambda: _uuid("msg"), primary_key=True)
    conversation_id: str = Field(index=True, foreign_key="conversations.id")
    role: str = "user"            # user | assistant
    content_redacted: str = ""
    model_used: str = ""
    route: ModelRoute = ModelRoute.LOCAL
    token_count: int = 0
    cost_estimate: float = 0.0
    created_at: datetime = Field(default_factory=datetime.utcnow)


class AuditEvent(SQLModel, table=True):
    __tablename__ = "audit_events"
    id: str = Field(default_factory=lambda: _uuid("aud"), primary_key=True)
    tenant_id: str = Field(index=True, foreign_key="tenants.id")
    user_id: str | None = None
    request_id: str = ""
    event_type: str = ""          # chat, upload, classify, index, block, login
    object_type: str = ""
    object_id: str = ""
    classification: Sensitivity | None = None
    selected_route: ModelRoute | None = None
    selected_model: str = ""
    risk_level: str = "low"
    token_count: int = 0
    cost_estimate: float = 0.0
    reason: str = ""
    event_metadata: str = ""      # JSON blob
    created_at: datetime = Field(default_factory=datetime.utcnow)


class ApiKey(SQLModel, table=True):
    """Tenant API key for system-to-system integration (the public /v1 API)."""
    __tablename__ = "api_keys"
    id: str = Field(default_factory=lambda: _uuid("key"), primary_key=True)
    tenant_id: str = Field(index=True, foreign_key="tenants.id")
    name: str = ""
    key_prefix: str = ""           # shown for identification (e.g. mai_ab12…)
    key_hash: str = Field(default="", index=True)  # sha256 of the full key
    provider: str = ""
    secret_ref: str = ""
    allowed_models: str = ""
    status: str = "active"
    created_at: datetime = Field(default_factory=datetime.utcnow)


class Connector(SQLModel, table=True):
    """Outbound connector to an enterprise system (CRM / ERP / delivery / custom).
    MaestroAI pushes data to it via webhook/REST; used by automations."""
    __tablename__ = "connectors"
    id: str = Field(default_factory=lambda: _uuid("cnx"), primary_key=True)
    tenant_id: str = Field(index=True, foreign_key="tenants.id")
    kind: str = "crm"              # crm | erp | delivery | custom
    name: str = ""
    base_url: str = ""            # endpoint to POST to
    auth_header: str = "Authorization"
    token_enc: str = ""           # encrypted at rest
    enabled: bool = True
    created_at: datetime = Field(default_factory=datetime.utcnow)


class WebhookEndpoint(SQLModel, table=True):
    """Inbound signed webhook (HMAC) so external systems notify events securely."""
    __tablename__ = "webhook_endpoints"
    id: str = Field(default_factory=lambda: _uuid("whk"), primary_key=True)
    tenant_id: str = Field(index=True, foreign_key="tenants.id")
    name: str = ""
    secret_enc: str = ""           # HMAC secret, encrypted at rest
    default_event: str = "webhook"
    enabled: bool = True
    created_at: datetime = Field(default_factory=datetime.utcnow)


class Connection(SQLModel, table=True):
    """A user-approved connection to an external account (email, calendar, ...).

    The "solo aprueba conexión" gate: created pending, executed only once the
    user approves. Designed to back a real OAuth consent later.
    """
    __tablename__ = "connections"
    id: str = Field(default_factory=lambda: _uuid("con"), primary_key=True)
    tenant_id: str = Field(index=True, foreign_key="tenants.id")
    user_id: str = Field(foreign_key="users.id")
    provider: str = ""             # email | calendar | crm | ...
    identifier: str = ""           # e.g. the email address
    status: str = "pending"        # pending | approved | revoked
    scopes: str = ""               # comma separated
    prefs: str = ""                # JSON (output type, schedule, ...)
    created_at: datetime = Field(default_factory=datetime.utcnow)


class OAuthToken(SQLModel, table=True):
    """OAuth tokens for a user's connected mailbox/calendar (Microsoft / Google).

    Stored in its own table (auto-created by create_all) so we never alter the
    existing connections table. Access/refresh tokens are encrypted at rest.
    """
    __tablename__ = "oauth_tokens"
    id: str = Field(default_factory=lambda: _uuid("oat"), primary_key=True)
    tenant_id: str = Field(index=True, foreign_key="tenants.id")
    user_id: str = Field(index=True, foreign_key="users.id")
    provider: str = ""             # microsoft | google
    identifier: str = ""           # connected email address
    access_token_enc: str = ""     # encrypted at rest (AES-256-GCM per tenant)
    refresh_token_enc: str = ""    # encrypted at rest
    expires_at: float = 0.0        # unix epoch seconds
    scopes: str = ""
    status: str = "active"         # active | revoked
    created_at: datetime = Field(default_factory=datetime.utcnow)
    updated_at: datetime = Field(default_factory=datetime.utcnow)


class Automation(SQLModel, table=True):
    """A user automation: trigger (manual/schedule/event) -> action (workflow /
    recipe / notify). Schedules/events are executed by the workflows layer
    (n8n/Temporal); 'run now' executes immediately."""
    __tablename__ = "automations"
    id: str = Field(default_factory=lambda: _uuid("auto"), primary_key=True)
    tenant_id: str = Field(index=True, foreign_key="tenants.id")
    user_id: str = Field(foreign_key="users.id")
    name: str = ""
    description: str = ""
    trigger: str = "manual"        # manual | schedule | event
    schedule: str = ""             # daily | weekly | monthly ("" if not schedule)
    event: str = ""                # e.g. document_uploaded
    action_type: str = "workflow"  # workflow | recipe | notify
    action_ref: str = ""           # workflow id / recipe id
    config: str = "{}"             # JSON (recipe inputs, notify message, ...)
    enabled: bool = True
    status: str = ""               # last run status
    last_run: str = ""             # ISO timestamp
    created_at: datetime = Field(default_factory=datetime.utcnow)


class Dashboard(SQLModel, table=True):
    """A company dashboard built from widgets (KPIs/charts/tables) bound to live
    metrics or manual data, optionally linked to a workflow automation."""
    __tablename__ = "dashboards"
    id: str = Field(default_factory=lambda: _uuid("dsh"), primary_key=True)
    tenant_id: str = Field(index=True, foreign_key="tenants.id")
    user_id: str = Field(foreign_key="users.id")
    name: str = ""
    description: str = ""
    spec: str = "[]"               # JSON list of widgets
    workflow_id: str = ""          # optional linked automation (n8n)
    created_at: datetime = Field(default_factory=datetime.utcnow)
    updated_at: datetime = Field(default_factory=datetime.utcnow)


class TenantTramite(SQLModel, table=True):
    """Per-company (tenant) curated procedure — the private MCP layer. Only
    paying tenants can add these; they ground that company's agents on top of the
    country/state curated layers."""
    __tablename__ = "tenant_tramites"
    id: str = Field(default_factory=lambda: _uuid("ttr"), primary_key=True)
    tenant_id: str = Field(index=True, foreign_key="tenants.id")
    country: str = "MX"
    region: str = ""               # estado/provincia ("" = nacional)
    municipio: str = ""
    title: str = ""
    authority: str = ""
    requisitos: str = ""           # JSON list
    pasos: str = ""                # JSON list
    costo_aprox: str = ""
    fuente: str = ""
    keywords: str = ""             # comma separated
    created_at: datetime = Field(default_factory=datetime.utcnow)


class AppProject(SQLModel, table=True):
    """App Studio: a user-built app/automation. Building is free; pushing to
    production is gated behind payment (pay-to-prod)."""
    __tablename__ = "app_projects"
    id: str = Field(default_factory=lambda: _uuid("app"), primary_key=True)
    tenant_id: str = Field(index=True, foreign_key="tenants.id")
    user_id: str = Field(foreign_key="users.id")
    name: str = ""
    description: str = ""
    spec: str = ""                 # AI-generated build plan / scaffold
    status: str = "draft"          # draft | built | pending_payment | deployed
    paid: bool = False
    deploy_url: str = ""
    token_count: int = 0
    cost_estimate: float = 0.0
    created_at: datetime = Field(default_factory=datetime.utcnow)
    updated_at: datetime = Field(default_factory=datetime.utcnow)


class CatalogRecipe(SQLModel, table=True):
    """A curated, DB-backed use case (so the catalog scales without redeploys).

    Created when an admin curates a user proposal. Tenant-scoped; merged with the
    in-code seed catalog at read time.
    """
    __tablename__ = "catalog_recipes"
    id: str = Field(default_factory=lambda: _uuid("rcp"), primary_key=True)
    tenant_id: str = Field(index=True, foreign_key="tenants.id")
    slug: str = Field(index=True)   # public recipe id
    category: str = "dia_a_dia"
    name: str = ""
    description: str = ""
    icon: str = "sparkles"
    inputs: str = ""               # JSON list of input fields
    prompt: str = ""               # generic pre-fill template
    produces: str = "el resultado"
    proposal_id: str = ""
    created_at: datetime = Field(default_factory=datetime.utcnow)


class RecipeProposal(SQLModel, table=True):
    """A use case proposed by a user. Curated into the catalog over time."""
    __tablename__ = "recipe_proposals"
    id: str = Field(default_factory=lambda: _uuid("prop"), primary_key=True)
    tenant_id: str = Field(index=True, foreign_key="tenants.id")
    user_id: str = Field(foreign_key="users.id")
    title: str = ""
    description: str = ""
    category: str = "dia_a_dia"
    status: str = "proposed"       # proposed | curated | rejected
    votes: int = 0
    created_at: datetime = Field(default_factory=datetime.utcnow)


class RecipeRun(SQLModel, table=True):
    """An instance of a use-case recipe: collect inputs -> AI pre-fill -> approve."""
    __tablename__ = "recipe_runs"
    id: str = Field(default_factory=lambda: _uuid("run"), primary_key=True)
    tenant_id: str = Field(index=True, foreign_key="tenants.id")
    user_id: str = Field(foreign_key="users.id")
    recipe_id: str = ""
    status: str = "draft"          # draft | needs_connection | completed | failed
    inputs: str = ""               # JSON
    draft: str = ""                # JSON — AI pre-filled output awaiting approval
    result: str = ""               # JSON — after approval/execution
    token_count: int = 0           # tokens burned generating the draft
    cost_estimate: float = 0.0
    created_at: datetime = Field(default_factory=datetime.utcnow)
    updated_at: datetime = Field(default_factory=datetime.utcnow)


class FineTuneDataset(SQLModel, table=True):
    """Dataset versionado para fine-tuning ligero (LoRA) — comportamiento/formato,
    no conocimiento (eso va por RAG). Los ejemplos se anonimizan antes de guardarse."""
    __tablename__ = "finetune_datasets"
    id: str = Field(default_factory=lambda: _uuid("ftd"), primary_key=True)
    tenant_id: str = Field(index=True, foreign_key="tenants.id")
    name: str = ""
    area: str = ""
    base_model: str = ""
    status: str = "draft"          # draft | ready (pasó el gate de calidad/red-team)
    version: int = 1
    created_at: datetime = Field(default_factory=datetime.utcnow)


class FineTuneExample(SQLModel, table=True):
    """Par (prompt, completion) de un dataset. Texto anonimizado (PII redactada)."""
    __tablename__ = "finetune_examples"
    id: str = Field(default_factory=lambda: _uuid("fte"), primary_key=True)
    tenant_id: str = Field(index=True, foreign_key="tenants.id")
    dataset_id: str = Field(index=True, foreign_key="finetune_datasets.id")
    prompt: str = ""
    completion: str = ""
    source: str = "manual"         # manual | memory | recipe
    created_at: datetime = Field(default_factory=datetime.utcnow)


class FineTuneJob(SQLModel, table=True):
    """Trabajo de entrenamiento LoRA. Se despacha a un trainer externo (GPU/n8n) o
    queda 'simulado' (laboratorio) si no hay backend configurado."""
    __tablename__ = "finetune_jobs"
    id: str = Field(default_factory=lambda: _uuid("ftj"), primary_key=True)
    tenant_id: str = Field(index=True, foreign_key="tenants.id")
    dataset_id: str = Field(foreign_key="finetune_datasets.id")
    base_model: str = ""
    status: str = "queued"         # queued | running | completed | failed | simulado
    adapter_uri: str = ""          # ubicación del adapter LoRA resultante
    serve_base_url: str = ""       # endpoint OpenAI-compat donde se sirve (vLLM/Ollama)
    metrics: str = "{}"            # JSON de métricas/evals
    reason: str = ""
    created_at: datetime = Field(default_factory=datetime.utcnow)


class Space(SQLModel, table=True):
    """Espacio (proyecto del cliente): contenedor que agrupa los entregables/módulos de
    un proyecto (p. ej. el Tablero Financiero). Aísla el trabajo de cada cliente/proyecto
    dentro del tenant. Pensado para demostrar la capacidad de la plataforma 'como lo haría
    un cliente': crea un espacio y dentro construye sus tableros, fuentes y casos."""
    __tablename__ = "spaces"
    id: str = Field(default_factory=lambda: _uuid("spc"), primary_key=True)
    tenant_id: str = Field(index=True, foreign_key="tenants.id")
    owner_id: str = Field(foreign_key="users.id")
    name: str = ""
    client: str = ""              # cliente al que pertenece el proyecto
    description: str = ""
    modules: str = '["finance"]'  # JSON: módulos activos (finance | docs | chat | ...)
    created_at: datetime = Field(default_factory=datetime.utcnow)


class MailDigestConfig(SQLModel, table=True):
    """Configuración (por usuario) del resumen de correo automatizado: cada día clasifica
    el buzón conectado (categoría/prioridad, descarta propaganda, detecta pendientes) y lo
    entrega por los canales elegidos (pop-up / correo / WhatsApp). Inspirado en el patrón
    Apps Script, pero genérico y configurable. Aprende un perfil de remitentes con el tiempo."""
    __tablename__ = "mail_digest_configs"
    id: str = Field(default_factory=lambda: _uuid("mdg"), primary_key=True)
    tenant_id: str = Field(index=True, foreign_key="tenants.id")
    user_id: str = Field(index=True, foreign_key="users.id")
    enabled: bool = False
    account_id: str = ""           # OAuthToken id ("" = la cuenta conectada más reciente)
    schedule: str = "daily"        # daily | weekdays
    channels: str = '["popup"]'    # JSON: popup | email | whatsapp
    email_to: str = ""             # destinatarios (coma); vacío = la propia cuenta
    language: str = "es"           # es | bilingue
    notes: str = ""                # contexto configurable (reemplaza el "NOTAS_FAMILIA")
    discard_propaganda: bool = True
    pending_enabled: bool = True
    pending_days: int = 2
    sender_profile: str = "{}"     # JSON {email: {categoria, propaganda}} aprendido
    last_run_at: str = ""
    created_at: datetime = Field(default_factory=datetime.utcnow)
