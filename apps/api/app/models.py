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
    region: str = "mx-central"
    kms_key_id: str = Field(default_factory=lambda: _uuid("kms"))
    retention_days: int = 365
    allows_external: bool = True
    allows_vpc: bool = True
    created_at: datetime = Field(default_factory=datetime.utcnow)


class User(SQLModel, table=True):
    __tablename__ = "users"
    id: str = Field(default_factory=lambda: _uuid("usr"), primary_key=True)
    tenant_id: str = Field(index=True, foreign_key="tenants.id")
    email: str = Field(index=True)
    name: str
    role: Role = Role.USER
    password_hash: str = ""
    mfa_enabled: bool = False
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
    sensitivity: Sensitivity = Sensitivity.INTERNAL
    pii_score: float = 0.0
    pii_types: str = ""            # comma separated
    storage_uri: str = ""
    hash: str = ""
    text: str = ""                 # extracted text (MVP keeps it inline)
    indexed: bool = False
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
    __tablename__ = "api_keys"
    id: str = Field(default_factory=lambda: _uuid("key"), primary_key=True)
    tenant_id: str = Field(index=True, foreign_key="tenants.id")
    provider: str = ""
    secret_ref: str = ""
    allowed_models: str = ""
    status: str = "active"
    created_at: datetime = Field(default_factory=datetime.utcnow)
