"""Agent endpoints (tenant-scoped)."""
from __future__ import annotations

from fastapi import APIRouter, Depends, HTTPException
from sqlmodel import Session, select

from ..auth import get_current_tenant, get_current_user
from ..db import get_session
from ..models import Agent, Tenant, User
from ..schemas import AgentCreate, AgentOut

router = APIRouter(prefix="/agents", tags=["agents"])


def _out(a: Agent) -> AgentOut:
    return AgentOut(
        id=a.id, name=a.name, type=a.type, area=a.area, privacy_mode=a.privacy_mode,
        requires_premium_reasoning=a.requires_premium_reasoning, status=a.status,
    )


@router.get("", response_model=list[AgentOut])
def list_agents(
    tenant: Tenant = Depends(get_current_tenant),
    session: Session = Depends(get_session),
) -> list[AgentOut]:
    agents = session.exec(select(Agent).where(Agent.tenant_id == tenant.id)).all()
    return [_out(a) for a in agents]


@router.post("", response_model=AgentOut, status_code=201)
def create_agent(
    body: AgentCreate,
    tenant: Tenant = Depends(get_current_tenant),
    user: User = Depends(get_current_user),
    session: Session = Depends(get_session),
) -> AgentOut:
    agent = Agent(tenant_id=tenant.id, **body.model_dump())
    session.add(agent)
    session.commit()
    session.refresh(agent)
    return _out(agent)


@router.get("/{agent_id}", response_model=AgentOut)
def get_agent(
    agent_id: str,
    tenant: Tenant = Depends(get_current_tenant),
    session: Session = Depends(get_session),
) -> AgentOut:
    agent = session.get(Agent, agent_id)
    if not agent or agent.tenant_id != tenant.id:
        raise HTTPException(status_code=404, detail="Agente no encontrado")
    return _out(agent)
