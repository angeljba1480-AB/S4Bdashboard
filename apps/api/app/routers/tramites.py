"""/tramites — curated procedures KB in layers: company (tenant, private) on top
of state and country (curated). Same source the MCP server and use-case grounding
use.

Layers:
  1. País  (TRAMITES curated, scope nacional)
  2. Estado (TRAMITES curated, scope estatal/municipal)
  3. Empresa (TenantTramite, private — only paying tenants can add)
"""
from __future__ import annotations

import json

from fastapi import APIRouter, Depends, HTTPException
from pydantic import BaseModel
from sqlmodel import Session, select

from ..auth import get_current_tenant, get_current_user, require_roles
from ..db import get_session
from ..models import Role, Tenant, TenantTramite, User
from ..regional.tramites import find_tramites, get_tramite

router = APIRouter(prefix="/tramites", tags=["tramites"])


def _tenant_entry_to_dict(t: TenantTramite) -> dict:
    return {
        "id": t.id, "country": t.country, "region": t.region, "municipio": t.municipio,
        "title": t.title, "authority": t.authority,
        "requisitos": json.loads(t.requisitos or "[]"), "pasos": json.loads(t.pasos or "[]"),
        "costo_aprox": t.costo_aprox, "fuente": t.fuente,
        "keywords": [k.strip() for k in t.keywords.split(",") if k.strip()],
        "scope": "empresa", "source": "empresa",
    }


def _tenant_matches(session: Session, tenant_id: str, country: str | None,
                    region: str | None, municipio: str | None, q: str | None) -> list[dict]:
    rows = session.exec(select(TenantTramite).where(TenantTramite.tenant_id == tenant_id)).all()
    out = []
    for t in rows:
        if country and t.country.upper() != country.upper():
            continue
        if region and t.region and region.lower() != t.region.lower():
            continue
        if q:
            blob = f"{t.title} {t.keywords}".lower()
            if q.lower() not in blob and not any(k.strip() and k.strip() in q.lower() for k in t.keywords.split(",")):
                continue
        out.append(_tenant_entry_to_dict(t))
    return out


def layered_search(session: Session, tenant: Tenant, q: str | None = None,
                   region: str | None = None, municipio: str | None = None,
                   country: str | None = None) -> list[dict]:
    """Company-private entries first, then curated state/country."""
    country = country or tenant.country
    private = _tenant_matches(session, tenant.id, country, region, municipio, q)
    curated = find_tramites(country, region, municipio, q)
    for c in curated:
        c.setdefault("source", "curado")
    return private + curated


class TenantTramiteIn(BaseModel):
    title: str
    authority: str = ""
    region: str = ""
    municipio: str = ""
    requisitos: list[str] = []
    pasos: list[str] = []
    costo_aprox: str = ""
    fuente: str = ""
    keywords: list[str] = []


@router.get("")
def search(
    q: str | None = None,
    region: str | None = None,
    municipio: str | None = None,
    country: str | None = None,
    tenant: Tenant = Depends(get_current_tenant),
    _: User = Depends(get_current_user),
    session: Session = Depends(get_session),
) -> list[dict]:
    return layered_search(session, tenant, q, region, municipio, country)


@router.get("/{tramite_id}")
def detail(
    tramite_id: str,
    tenant: Tenant = Depends(get_current_tenant),
    _: User = Depends(get_current_user),
    session: Session = Depends(get_session),
) -> dict:
    row = session.get(TenantTramite, tramite_id)
    if row and row.tenant_id == tenant.id:
        return _tenant_entry_to_dict(row)
    t = get_tramite(tramite_id)
    if not t:
        raise HTTPException(status_code=404, detail="Trámite no encontrado")
    return t


@router.post("", status_code=201)
def add_company_tramite(
    body: TenantTramiteIn,
    _: User = Depends(require_roles(Role.ADMIN, Role.DEVOPS)),
    tenant: Tenant = Depends(get_current_tenant),
    session: Session = Depends(get_session),
) -> dict:
    """Add a company-private trámite (the tenant MCP layer). Paying tenants only."""
    if tenant.subscription_status not in ("active", "trial"):
        raise HTTPException(status_code=402, detail="Suscripción inactiva: renueva para tu MCP de empresa")
    if not body.title.strip():
        raise HTTPException(status_code=422, detail="El título es obligatorio")
    row = TenantTramite(
        tenant_id=tenant.id, country=tenant.country, region=body.region.strip(),
        municipio=body.municipio.strip(), title=body.title.strip(), authority=body.authority.strip(),
        requisitos=json.dumps(body.requisitos), pasos=json.dumps(body.pasos),
        costo_aprox=body.costo_aprox.strip(), fuente=body.fuente.strip(),
        keywords=",".join(body.keywords),
    )
    session.add(row)
    session.commit()
    session.refresh(row)
    return _tenant_entry_to_dict(row)
