"""/chat endpoint — orchestrates policy, RAG, model router, adapter and audit.

This is the vertical slice the blueprint asks Cursor/Claude Code to build first
(backlog: "Chat endpoint").
"""
from __future__ import annotations

import uuid

from fastapi import APIRouter, Depends, HTTPException
from sqlmodel import Session

from ..ai.cost import estimate_cost, estimate_tokens
from ..ai.rag import retrieve
from ..ai.resilience import generate_with_fallback
from ..ai.router import route_request
from ..auth import get_current_tenant, get_current_user
from ..db import get_session
from ..models import (
    Agent,
    AuditEvent,
    Conversation,
    Message,
    ModelRoute,
    Tenant,
    User,
)
from ..schemas import ChatRequest, ChatResponse, CitationOut

router = APIRouter(prefix="/chat", tags=["chat"])


@router.post("", response_model=ChatResponse)
def chat(
    body: ChatRequest,
    tenant: Tenant = Depends(get_current_tenant),
    user: User = Depends(get_current_user),
    session: Session = Depends(get_session),
) -> ChatResponse:
    agent = session.get(Agent, body.agent_id)
    if not agent or agent.tenant_id != tenant.id:
        raise HTTPException(status_code=404, detail="Agente no encontrado")

    request_id = uuid.uuid4().hex

    # 1. Conversation
    conv = session.get(Conversation, body.conversation_id) if body.conversation_id else None
    if conv and conv.tenant_id != tenant.id:
        raise HTTPException(status_code=403, detail="Conversación de otro tenant")
    if not conv:
        conv = Conversation(
            tenant_id=tenant.id, user_id=user.id, agent_id=agent.id,
            title=body.prompt[:48] or "Nueva conversación",
        )
        session.add(conv)
        session.commit()
        session.refresh(conv)

    # 2. Retrieval (tenant-scoped RAG)
    citations = retrieve(session, tenant.id, body.prompt, body.document_ids or None)
    context_texts = [c.text for c in citations]

    # 3. Privacy Model Router
    decision = route_request(tenant, agent, body.prompt, context_texts, task="chat")

    # 4. Record the user message
    session.add(Message(
        conversation_id=conv.id, role="user",
        content_redacted=body.prompt[:4000], model_used="", route=decision.route,
    ))

    # 5. Generate (or block) — with privacy-safe provider fallback.
    used_route = decision.route
    if decision.route == ModelRoute.BLOCKED:
        content = f"⛔ Operación bloqueada por política: {decision.reason}"
        model_used = "—"
        tokens = estimate_tokens(body.prompt)
        cost = 0.0
    else:
        gen = generate_with_fallback(decision.route, agent.system_prompt, body.prompt, decision.context)
        used_route = gen.route
        if gen.route == ModelRoute.BLOCKED:
            content = f"⛔ Sin proveedor disponible (fallback agotado): {gen.error}"
            model_used = "—"
            tokens = estimate_tokens(body.prompt)
            cost = 0.0
        else:
            content = gen.response.content
            model_used = gen.response.model
            if gen.fell_back:
                content += f"\n\n_(Fallback a ruta `{gen.route.value}` por indisponibilidad del proveedor.)_"
            tokens = estimate_tokens(body.prompt + content)
            cost = estimate_cost(gen.route, tokens)

    # 6. Persist assistant message
    msg = Message(
        conversation_id=conv.id, role="assistant", content_redacted=content,
        model_used=model_used, route=used_route, token_count=tokens, cost_estimate=cost,
    )
    session.add(msg)

    blocked = used_route == ModelRoute.BLOCKED
    fell_back = used_route != decision.route and not blocked
    audit_reason = decision.reason + (f" → fallback a {used_route.value}" if fell_back else "")

    # 7. Audit (always)
    session.add(AuditEvent(
        tenant_id=tenant.id, user_id=user.id, request_id=request_id, event_type="chat",
        object_type="agent", object_id=agent.id, classification=decision.classification,
        selected_route=used_route, selected_model=model_used,
        risk_level="high" if blocked or decision.pii_score > 0.3 else "low",
        token_count=tokens, cost_estimate=cost, reason=audit_reason,
        event_metadata=str({"pii": decision.pii_types, "redacted": decision.redacted, "fell_back": fell_back}),
    ))
    session.commit()
    session.refresh(msg)

    return ChatResponse(
        conversation_id=conv.id, message_id=msg.id, content=content,
        route=used_route, model_used=model_used, classification=decision.classification,
        pii_types=decision.pii_types, pii_score=decision.pii_score, redacted=decision.redacted,
        blocked=blocked, reason=audit_reason,
        token_count=tokens, cost_estimate=cost,
        citations=[CitationOut(**c.__dict__) for c in citations],
    )
