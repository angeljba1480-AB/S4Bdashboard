"""/spaces — espacios (proyectos del cliente): contenedores de entregables/módulos.

Un cliente crea un espacio y dentro viven sus módulos (hoy: Tablero Financiero). Sirve
para demostrar la plataforma 'como lo haría un cliente', con el trabajo aislado por proyecto.
"""
from __future__ import annotations

import json

from fastapi import APIRouter, Depends, HTTPException
from pydantic import BaseModel
from sqlmodel import Session, select

from ..auth import get_current_tenant, get_current_user
from ..db import get_session
from ..models import Space, Tenant, User

router = APIRouter(prefix="/spaces", tags=["spaces"])

# Catálogo de módulos disponibles dentro de un espacio.
MODULES = {
    "finance": {"key": "finance", "title": "Tablero Financiero", "href": "/tablero-financiero",
                "icon": "line-chart", "desc": "KPIs directivos, P&L, clientes y preguntar (RAG)."},
}


def _out(s: Space) -> dict:
    keys = json.loads(s.modules or "[]")
    return {"id": s.id, "name": s.name, "client": s.client, "description": s.description,
            "modules": [MODULES[k] for k in keys if k in MODULES],
            "created_at": s.created_at.isoformat()}


@router.get("")
def list_spaces(tenant: Tenant = Depends(get_current_tenant), user: User = Depends(get_current_user),
                session: Session = Depends(get_session)) -> list[dict]:
    rows = session.exec(select(Space).where(Space.tenant_id == tenant.id)
                        .order_by(Space.created_at.desc())).all()
    # Si no hay espacios, sembramos uno demo para que el Tablero Financiero sea visible
    # de inmediato (el cliente lo puede renombrar o borrar).
    if not rows:
        demo = Space(tenant_id=tenant.id, owner_id=user.id,
                     name="Proyecto demo · Tablero Financiero",
                     client=tenant.name, description="Espacio de ejemplo para probar el tablero.",
                     modules='["finance"]')
        session.add(demo); session.commit(); session.refresh(demo)
        rows = [demo]
    return [_out(s) for s in rows]


class SpaceIn(BaseModel):
    name: str
    client: str = ""
    description: str = ""
    modules: list[str] = ["finance"]


@router.post("", status_code=201)
def create_space(body: SpaceIn, tenant: Tenant = Depends(get_current_tenant),
                 user: User = Depends(get_current_user), session: Session = Depends(get_session)) -> dict:
    if not body.name.strip():
        raise HTTPException(status_code=422, detail="El nombre del espacio es obligatorio")
    mods = [m for m in body.modules if m in MODULES] or ["finance"]
    s = Space(tenant_id=tenant.id, owner_id=user.id, name=body.name.strip(),
              client=body.client.strip(), description=body.description.strip(),
              modules=json.dumps(mods))
    session.add(s); session.commit(); session.refresh(s)
    return _out(s)


def _owned(session, tenant, sid) -> Space:
    s = session.get(Space, sid)
    if not s or s.tenant_id != tenant.id:
        raise HTTPException(status_code=404, detail="Espacio no encontrado")
    return s


@router.get("/{sid}")
def get_space(sid: str, tenant: Tenant = Depends(get_current_tenant),
              _: User = Depends(get_current_user), session: Session = Depends(get_session)) -> dict:
    return _out(_owned(session, tenant, sid))


@router.delete("/{sid}")
def delete_space(sid: str, tenant: Tenant = Depends(get_current_tenant),
                 _: User = Depends(get_current_user), session: Session = Depends(get_session)) -> dict:
    s = _owned(session, tenant, sid)
    session.delete(s); session.commit()
    return {"ok": True}
