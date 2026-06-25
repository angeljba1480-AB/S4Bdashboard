"""Audit log endpoint — filterable, navigable, tenant-scoped (blueprint §12)."""
from __future__ import annotations

import json

from fastapi import APIRouter, Depends
from fastapi.responses import Response
from sqlmodel import Session, select

from ..auth import get_current_tenant
from ..db import get_session
from ..models import AuditEvent, ModelRoute, Sensitivity, Tenant
from ..schemas import AuditOut

router = APIRouter(prefix="/audit", tags=["audit"])


def _filtered(stmt, *, event_type, risk_level, classification, route, user_id, q):
    if event_type:
        stmt = stmt.where(AuditEvent.event_type == event_type)
    if risk_level:
        stmt = stmt.where(AuditEvent.risk_level == risk_level)
    if classification:
        try:
            stmt = stmt.where(AuditEvent.classification == Sensitivity(classification))
        except ValueError:
            pass
    if route:
        try:
            stmt = stmt.where(AuditEvent.selected_route == ModelRoute(route))
        except ValueError:
            pass
    if user_id:
        stmt = stmt.where(AuditEvent.user_id == user_id)
    if q:
        stmt = stmt.where(AuditEvent.reason.ilike(f"%{q}%"))
    return stmt


@router.get("", response_model=list[AuditOut])
def list_audit(
    event_type: str | None = None,
    risk_level: str | None = None,
    classification: str | None = None,
    route: str | None = None,
    user_id: str | None = None,
    q: str | None = None,
    limit: int = 100,
    offset: int = 0,
    tenant: Tenant = Depends(get_current_tenant),
    session: Session = Depends(get_session),
) -> list[AuditOut]:
    stmt = select(AuditEvent).where(AuditEvent.tenant_id == tenant.id)
    stmt = _filtered(stmt, event_type=event_type, risk_level=risk_level,
                     classification=classification, route=route, user_id=user_id, q=q)
    stmt = stmt.order_by(AuditEvent.created_at.desc()).offset(max(0, offset)).limit(min(limit, 500))
    events = session.exec(stmt).all()
    return [
        AuditOut(
            id=e.id, event_type=e.event_type, object_type=e.object_type, object_id=e.object_id,
            classification=e.classification, selected_route=e.selected_route,
            selected_model=e.selected_model, risk_level=e.risk_level, token_count=e.token_count,
            cost_estimate=e.cost_estimate, reason=e.reason, user_id=e.user_id, created_at=e.created_at,
            request_id=e.request_id, event_metadata=e.event_metadata,
        )
        for e in events
    ]


@router.get("/stats")
def audit_stats(
    tenant: Tenant = Depends(get_current_tenant),
    session: Session = Depends(get_session),
) -> dict:
    """Aggregates for the navigable audit view: totals + breakdowns + filter values."""
    events = session.exec(
        select(AuditEvent).where(AuditEvent.tenant_id == tenant.id)
    ).all()

    by_event: dict[str, int] = {}
    by_risk: dict[str, int] = {}
    by_route: dict[str, int] = {}
    by_classification: dict[str, int] = {}
    users: set[str] = set()
    total_cost = 0.0
    total_tokens = 0
    blocked = 0
    for e in events:
        by_event[e.event_type] = by_event.get(e.event_type, 0) + 1
        by_risk[e.risk_level] = by_risk.get(e.risk_level, 0) + 1
        if e.selected_route:
            by_route[e.selected_route.value] = by_route.get(e.selected_route.value, 0) + 1
            if e.selected_route == ModelRoute.BLOCKED:
                blocked += 1
        if e.classification:
            by_classification[e.classification.value] = by_classification.get(e.classification.value, 0) + 1
        if e.user_id:
            users.add(e.user_id)
        total_cost += e.cost_estimate
        total_tokens += e.token_count

    return {
        "total": len(events),
        "high_risk": by_risk.get("high", 0),
        "blocked": blocked,
        "total_cost": round(total_cost, 6),
        "total_tokens": total_tokens,
        "by_event": dict(sorted(by_event.items(), key=lambda x: -x[1])),
        "by_risk": by_risk,
        "by_route": by_route,
        "by_classification": by_classification,
        "event_types": sorted(by_event.keys()),
        "users": sorted(users),
    }


@router.get("/export")
def export_audit(
    tenant: Tenant = Depends(get_current_tenant),
    session: Session = Depends(get_session),
) -> Response:
    """SIEM-friendly JSON Lines export of the tenant's audit trail."""
    events = session.exec(
        select(AuditEvent).where(AuditEvent.tenant_id == tenant.id).order_by(AuditEvent.created_at)
    ).all()
    lines = []
    for e in events:
        lines.append(json.dumps({
            "ts": e.created_at.isoformat(), "tenant_id": e.tenant_id, "user_id": e.user_id,
            "request_id": e.request_id, "event_type": e.event_type, "object_type": e.object_type,
            "object_id": e.object_id, "classification": e.classification.value if e.classification else None,
            "route": e.selected_route.value if e.selected_route else None, "model": e.selected_model,
            "risk_level": e.risk_level, "tokens": e.token_count, "cost": e.cost_estimate, "reason": e.reason,
        }, ensure_ascii=False))
    return Response("\n".join(lines), media_type="application/x-ndjson",
                    headers={"Content-Disposition": 'attachment; filename="audit.jsonl"'})
