"""Audit log endpoint — filterable, tenant-scoped (blueprint section 12)."""
from __future__ import annotations

from fastapi import APIRouter, Depends
from sqlmodel import Session, select

from ..auth import get_current_tenant
from ..db import get_session
from ..models import AuditEvent, Tenant
from ..schemas import AuditOut

router = APIRouter(prefix="/audit", tags=["audit"])


@router.get("", response_model=list[AuditOut])
def list_audit(
    event_type: str | None = None,
    risk_level: str | None = None,
    limit: int = 100,
    tenant: Tenant = Depends(get_current_tenant),
    session: Session = Depends(get_session),
) -> list[AuditOut]:
    stmt = select(AuditEvent).where(AuditEvent.tenant_id == tenant.id)
    if event_type:
        stmt = stmt.where(AuditEvent.event_type == event_type)
    if risk_level:
        stmt = stmt.where(AuditEvent.risk_level == risk_level)
    stmt = stmt.order_by(AuditEvent.created_at.desc()).limit(limit)
    events = session.exec(stmt).all()
    return [
        AuditOut(
            id=e.id, event_type=e.event_type, object_type=e.object_type, object_id=e.object_id,
            classification=e.classification, selected_route=e.selected_route,
            selected_model=e.selected_model, risk_level=e.risk_level, token_count=e.token_count,
            cost_estimate=e.cost_estimate, reason=e.reason, user_id=e.user_id, created_at=e.created_at,
        )
        for e in events
    ]
