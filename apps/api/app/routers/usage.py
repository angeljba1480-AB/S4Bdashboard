"""Usage / cost meter endpoint (blueprint: control económico, ROI)."""
from __future__ import annotations

from fastapi import APIRouter, Depends
from sqlmodel import Session, select

from ..auth import get_current_tenant
from ..db import get_session
from ..models import Agent, Message, Tenant
from ..schemas import UsageSummary

router = APIRouter(prefix="/usage", tags=["usage"])


@router.get("", response_model=UsageSummary)
def usage(
    tenant: Tenant = Depends(get_current_tenant),
    session: Session = Depends(get_session),
) -> UsageSummary:
    # Messages joined to tenant through their conversation's agent set.
    agents = {a.id: a.name for a in session.exec(
        select(Agent).where(Agent.tenant_id == tenant.id)
    ).all()}

    from ..models import Conversation  # local import to avoid cycle noise

    conv_agent = {c.id: c.agent_id for c in session.exec(
        select(Conversation).where(Conversation.tenant_id == tenant.id)
    ).all()}

    msgs = session.exec(
        select(Message).where(Message.conversation_id.in_(list(conv_agent.keys()) or [""]))
    ).all()

    total_tokens = sum(m.token_count for m in msgs)
    total_cost = round(sum(m.cost_estimate for m in msgs), 6)
    by_route: dict[str, float] = {}
    by_agent: dict[str, float] = {}
    for m in msgs:
        by_route[m.route.value] = round(by_route.get(m.route.value, 0.0) + m.cost_estimate, 6)
        aname = agents.get(conv_agent.get(m.conversation_id, ""), "—")
        by_agent[aname] = round(by_agent.get(aname, 0.0) + m.cost_estimate, 6)

    return UsageSummary(
        total_messages=len(msgs), total_tokens=total_tokens, total_cost=total_cost,
        by_route=by_route, by_agent=by_agent,
    )


@router.get("/operations")
def operations(
    tenant: Tenant = Depends(get_current_tenant),
    session: Session = Depends(get_session),
) -> dict:
    """Operations dashboard: cases running, searches, tokens burned and cost."""
    return compute_operations(session, tenant)


def compute_operations(session: Session, tenant: Tenant) -> dict:
    """Aggregate operations metrics (reused by /usage/operations and dashboards)."""
    from ..models import AppProject, Conversation, RecipeRun
    from .recipes import _resolve  # recipe id -> display name

    runs = session.exec(select(RecipeRun).where(RecipeRun.tenant_id == tenant.id)).all()
    apps = session.exec(select(AppProject).where(AppProject.tenant_id == tenant.id)).all()
    conv_ids = [c.id for c in session.exec(
        select(Conversation).where(Conversation.tenant_id == tenant.id)).all()]
    msgs = session.exec(
        select(Message).where(Message.conversation_id.in_(conv_ids or [""]))) .all()

    # Tokens burned across every AI surface (chat + recipe cases + app builds).
    chat_tokens = sum(m.token_count for m in msgs)
    case_tokens = sum(r.token_count for r in runs)
    app_tokens = sum(a.token_count for a in apps)
    total_tokens = chat_tokens + case_tokens + app_tokens
    total_cost = round(sum(m.cost_estimate for m in msgs)
                       + sum(r.cost_estimate for r in runs)
                       + sum(a.cost_estimate for a in apps), 6)

    tokens_by_source = {"chat": chat_tokens, "casos": case_tokens, "apps": app_tokens}

    cost_by_route: dict[str, float] = {}
    for m in msgs:
        cost_by_route[m.route.value] = round(cost_by_route.get(m.route.value, 0.0) + m.cost_estimate, 6)

    by_status: dict[str, int] = {}
    by_recipe: dict[str, int] = {}
    for r in runs:
        by_status[r.status] = by_status.get(r.status, 0) + 1
        name = (_resolve(session, tenant.id, r.recipe_id) or {}).get("name", r.recipe_id)
        by_recipe[name] = by_recipe.get(name, 0) + 1

    recent = sorted(runs, key=lambda r: r.created_at, reverse=True)[:10]
    recent_cases = [{
        "id": r.id,
        "recipe": (_resolve(session, tenant.id, r.recipe_id) or {}).get("name", r.recipe_id),
        "status": r.status, "tokens": r.token_count,
        "cost": round(r.cost_estimate, 6),
        "created_at": r.created_at.isoformat(),
    } for r in recent]

    return {
        "cases": {
            "total": len(runs),
            "completed": by_status.get("completed", 0),
            "in_progress": by_status.get("draft", 0) + by_status.get("needs_connection", 0),
            "by_status": by_status,
            "by_recipe": dict(sorted(by_recipe.items(), key=lambda x: -x[1])[:8]),
        },
        "searches": len([m for m in msgs if m.role == "assistant"]),
        "tokens": {"total": total_tokens, "by_source": tokens_by_source},
        "cost": {"total": total_cost, "by_route": cost_by_route},
        "apps": {"built": len(apps), "deployed": len([a for a in apps if a.status == "deployed"])},
        "recent_cases": recent_cases,
    }
