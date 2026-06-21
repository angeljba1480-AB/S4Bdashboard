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
from ..models import Document, Role, Tenant, TenantTramite, User
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


def _rag_matches(session: Session, tenant_id: str, q: str | None, limit: int = 3) -> list[dict]:
    """Company MCP knowledge from the tenant's own indexed documents (RAG)."""
    if not q:
        return []
    from ..ai.rag import retrieve
    try:
        cits = retrieve(session, tenant_id, q, None, top_k=limit)
    except Exception:
        return []
    return [{
        "id": f"rag_{c.document_id}_{c.chunk_index}", "title": c.filename,
        "authority": "Documento de la empresa", "text": c.text,
        "source": "empresa-rag", "scope": "empresa", "region": "", "municipio": "",
        "requisitos": [], "pasos": [], "fuente": "", "country": "",
    } for c in cits]


def layered_search(session: Session, tenant: Tenant, q: str | None = None,
                   region: str | None = None, municipio: str | None = None,
                   country: str | None = None, include_rag: bool = False) -> list[dict]:
    """Company layer (private trámites + RAG over the company's docs) first,
    then curated state/country."""
    country = country or tenant.country
    private = _tenant_matches(session, tenant.id, country, region, municipio, q)
    rag = _rag_matches(session, tenant.id, q) if include_rag else []
    curated = find_tramites(country, region, municipio, q)
    for c in curated:
        c.setdefault("source", "curado")
    return private + rag + curated


class ImportIn(BaseModel):
    document_id: str


_REQ_KW = ("requisito", "deberá", "debera", "presentar", "adjuntar", "acredit", "constancia",
           "identificación", "identificacion", "comprobante", "copia", "original", "vigente")
_PASO_KW = ("paso", "ingresa", "acude", "solicita", "registra", "tramita", "paga", "obtén", "obten",
            "descarga", "verifica", "llena", "completa")


def extract_tramite(doc: Document) -> dict:
    """Heuristically turn a document into a structured trámite draft (offline-safe)."""
    from ..security.crypto import decrypt
    text = decrypt(doc.text or "", doc.tenant_id)
    lines = [ln.strip(" -•\t") for ln in text.splitlines() if ln.strip()]
    title = (lines[0][:120] if lines else "") or doc.filename.rsplit(".", 1)[0]
    requisitos, pasos = [], []
    for ln in lines:
        low = ln.lower()
        if len(ln) > 8 and any(k in low for k in _REQ_KW):
            requisitos.append(ln[:200])
        if (ln[:2].rstrip(".").isdigit() or any(low.startswith(k) for k in _PASO_KW)):
            pasos.append(ln[:200])
    requisitos = list(dict.fromkeys(requisitos))[:12]
    pasos = list(dict.fromkeys(pasos))[:12] or lines[1:6]
    keywords = [w.lower() for w in title.split() if len(w) > 4][:6]
    return {"title": title, "requisitos": requisitos, "pasos": pasos, "keywords": keywords}


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
    rag: bool = True,
    tenant: Tenant = Depends(get_current_tenant),
    _: User = Depends(get_current_user),
    session: Session = Depends(get_session),
) -> list[dict]:
    return layered_search(session, tenant, q, region, municipio, country, include_rag=rag)


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


@router.post("/import", status_code=201)
def import_from_document(
    body: ImportIn,
    _: User = Depends(require_roles(Role.ADMIN, Role.DEVOPS)),
    tenant: Tenant = Depends(get_current_tenant),
    session: Session = Depends(get_session),
) -> dict:
    """Turn an uploaded document into a structured company trámite (MCP layer)."""
    if tenant.subscription_status not in ("active", "trial"):
        raise HTTPException(status_code=402, detail="Suscripción inactiva: renueva para tu MCP de empresa")
    doc = session.get(Document, body.document_id)
    if not doc or doc.tenant_id != tenant.id:
        raise HTTPException(status_code=404, detail="Documento no encontrado")
    draft = extract_tramite(doc)
    row = TenantTramite(
        tenant_id=tenant.id, country=tenant.country, title=draft["title"],
        authority=f"Importado de {doc.filename}",
        requisitos=json.dumps(draft["requisitos"]), pasos=json.dumps(draft["pasos"]),
        keywords=",".join(draft["keywords"]), fuente=doc.filename,
    )
    session.add(row)
    session.commit()
    session.refresh(row)
    return _tenant_entry_to_dict(row)
