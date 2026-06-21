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
