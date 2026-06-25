"""Pydantic request/response schemas."""
from __future__ import annotations

from datetime import datetime

from pydantic import BaseModel

from .models import ModelRoute, Role, Sensitivity


# --- Auth -------------------------------------------------------------------
class LoginRequest(BaseModel):
    email: str
    password: str


class TokenResponse(BaseModel):
    access_token: str
    token_type: str = "bearer"


class MeResponse(BaseModel):
    id: str
    email: str
    name: str
    role: Role
    tenant_id: str
    tenant_name: str
    mfa_enabled: bool
    brand_name: str = ""
    brand_logo_url: str = ""
    brand_color: str = ""
    brand_tagline: str = ""
    country: str = "MX"
    country_name: str = "México"


# --- Agents -----------------------------------------------------------------
class AgentCreate(BaseModel):
    name: str
    type: str = "general"
    area: str = "general"
    system_prompt: str = ""
    tools: str = ""
    privacy_mode: str = "auto"
    requires_premium_reasoning: bool = False


class AgentOut(BaseModel):
    id: str
    name: str
    type: str
    area: str
    privacy_mode: str
    requires_premium_reasoning: bool
    status: str


# --- Documents --------------------------------------------------------------
class DocumentOut(BaseModel):
    id: str
    filename: str
    mime_type: str
    area: str = ""
    category: str = ""
    category_label: str = ""
    sensitivity: Sensitivity
    pii_score: float
    pii_types: list[str]
    indexed: bool
    created_at: datetime


class DocumentUpdate(BaseModel):
    area: str | None = None
    category: str | None = None
    sensitivity: Sensitivity | None = None


class DocumentCategoryOut(BaseModel):
    id: str
    key: str
    label: str
    description: str = ""
    system: bool = False


class DocumentCategoryCreate(BaseModel):
    label: str
    description: str = ""


# --- Chat -------------------------------------------------------------------
class ChatRequest(BaseModel):
    tenant_id: str | None = None
    agent_id: str
    conversation_id: str | None = None
    prompt: str
    document_ids: list[str] = []
    use_rag: bool = True          # False = "sin contexto" (pure model, no retrieval)
    use_memory: bool = False      # incluir memoria (trabajos previos) en el contexto
    precision: bool = False       # "máxima precisión": refinar con modelo premium
    approve_external: bool = False  # aprueba escalar contenido sensible a premium
    privacy_mode: str = "auto"
    response_format: str = "markdown"
    human_approval_required: bool = False


class CitationOut(BaseModel):
    document_id: str
    filename: str
    chunk_index: int
    text: str
    score: float
    sensitivity: Sensitivity


class ChatResponse(BaseModel):
    conversation_id: str
    message_id: str
    content: str
    route: ModelRoute
    model_used: str
    classification: Sensitivity
    pii_types: list[str]
    pii_score: float
    redacted: bool
    blocked: bool
    reason: str
    token_count: int
    cost_estimate: float
    citations: list[CitationOut]
    escalated: bool = False           # refinado con modelo premium (cascada)
    escalation_pending: bool = False  # sensible: requiere aprobación para escalar


class RoutePreview(BaseModel):
    """Preflight route advisory — what the router would do, without executing."""
    classification: Sensitivity
    route: ModelRoute
    pii_types: list[str]
    pii_score: float
    reason: str
    level: str            # info | warn | block
    message: str          # human-readable advisory (es-MX)
    requires_approval: bool
    sources_found: int


# --- Audit / Usage ----------------------------------------------------------
class AuditOut(BaseModel):
    id: str
    event_type: str
    object_type: str
    object_id: str
    classification: Sensitivity | None
    selected_route: ModelRoute | None
    selected_model: str
    risk_level: str
    token_count: int
    cost_estimate: float
    reason: str
    user_id: str | None
    created_at: datetime
    request_id: str = ""
    event_metadata: str = ""


class UsageSummary(BaseModel):
    total_messages: int
    total_tokens: int
    total_cost: float
    by_route: dict[str, float]
    by_agent: dict[str, float]
