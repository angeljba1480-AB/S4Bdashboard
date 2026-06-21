"""/regional — browse procedures/problems by estado + development axis, and turn
one into a use-case proposal (which an admin curates into a runnable recipe)."""
from __future__ import annotations

from fastapi import APIRouter, Depends, HTTPException
from sqlmodel import Session

from ..auth import get_current_tenant, get_current_user
from ..db import get_session
from ..models import AuditEvent, RecipeProposal, Tenant, User
from ..regional.catalog import EJES, PROCEDURES, filter_procedures, get_procedure
from ..regional.countries import COUNTRIES, get_country

router = APIRouter(prefix="/regional", tags=["regional"])


@router.get("/countries")
def list_countries(_: User = Depends(get_current_user)) -> list[dict]:
    return [{"code": c["code"], "name": c["name"], "division_label": c["division_label"]}
            for c in COUNTRIES]


@router.get("/ejes")
def list_ejes(_: User = Depends(get_current_user)) -> list[dict]:
    counts: dict[str, int] = {}
    for p in PROCEDURES:
        counts[p["eje"]] = counts.get(p["eje"], 0) + 1
    return [{**e, "count": counts.get(e["id"], 0)} for e in EJES]


@router.get("/divisions")
def list_divisions(
    country: str | None = None,
    tenant: Tenant = Depends(get_current_tenant),
    _: User = Depends(get_current_user),
) -> dict:
    c = get_country(country or tenant.country)
    return {"country": c["code"], "division_label": c["division_label"], "divisions": c["divisions"]}


@router.get("/procedures")
def list_procedures(
    estado: str | None = None,
    eje: str | None = None,
    q: str | None = None,
    country: str | None = None,
    tenant: Tenant = Depends(get_current_tenant),
    _: User = Depends(get_current_user),
) -> list[dict]:
    country = country or tenant.country
    eje_label = {e["id"]: e["label"] for e in EJES}
    return [
        {"id": p["id"], "title": p["title"], "problem": p["problem"],
         "eje": p["eje"], "eje_label": eje_label.get(p["eje"], p["eje"]),
         "category": p["category"], "suggested_recipe": p["suggested_recipe"],
         "scope": "nacional" if not p["estados"] else ", ".join(p["estados"])}
        for p in filter_procedures(estado, eje, q, country)
    ]


@router.post("/procedures/{procedure_id}/propose")
def procedure_to_proposal(
    procedure_id: str,
    tenant: Tenant = Depends(get_current_tenant),
    user: User = Depends(get_current_user),
    session: Session = Depends(get_session),
) -> dict:
    """Create a use-case proposal from a regional procedure (feeds curation)."""
    proc = get_procedure(procedure_id)
    if not proc:
        raise HTTPException(status_code=404, detail="Trámite no encontrado")
    prop = RecipeProposal(
        tenant_id=tenant.id, user_id=user.id,
        title=proc["title"], description=proc["problem"], category=proc["category"],
    )
    session.add(prop)
    session.add(AuditEvent(
        tenant_id=tenant.id, user_id=user.id, event_type="recipe_proposal",
        object_type="regional_procedure", object_id=procedure_id, risk_level="low",
        reason=f"caso de uso propuesto desde trámite regional: {proc['title']}",
    ))
    session.commit()
    session.refresh(prop)
    return {"id": prop.id, "title": prop.title, "category": prop.category, "status": prop.status}
