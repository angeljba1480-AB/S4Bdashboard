"""/kedb — Known-Error Database (operación de ciberseguridad/SOC).

Módulo gateado: solo disponible para tenants con **perfil de ciberseguridad**
(industry del CompanyProfile con keywords cyber/seguridad/soc/security).

Alcances (`scope`):
- 'tenant': errores conocidos propios del cliente.
- 'shared': errores conocidos cross-cliente, curados y **sanitizados** por el
  operador (sin datos del cliente origen), visibles para todos los tenants cyber.
"""
from __future__ import annotations

from datetime import datetime

from fastapi import APIRouter, Depends, HTTPException
from pydantic import BaseModel
from sqlmodel import Session, or_, select

from ..auth import get_current_tenant, get_current_user, require_roles
from ..db import get_session
from ..models import AuditEvent, CompanyProfile, KnownError, Role, Tenant, User

router = APIRouter(prefix="/kedb", tags=["kedb"])

_CYBER_KEYWORDS = ("ciber", "cyber", "seguridad", "security", "soc", "infosec", "ciso")
_SEVERITY = ("low", "medium", "high", "critical")


def kedb_enabled(session: Session, tenant: Tenant) -> bool:
    """El módulo se habilita solo para empresas con perfil de ciberseguridad."""
    prof = session.exec(
        select(CompanyProfile).where(CompanyProfile.tenant_id == tenant.id)).first()
    industry = (prof.industry if prof else "").lower()
    return any(k in industry for k in _CYBER_KEYWORDS)


def _require_kedb(session: Session, tenant: Tenant) -> None:
    if not kedb_enabled(session, tenant):
        raise HTTPException(
            status_code=403,
            detail="Módulo KEDB disponible solo para perfil de ciberseguridad. "
                   "Define el giro en Configuración de empresa (industria).")


def _out(k: KnownError) -> dict:
    return {"id": k.id, "scope": k.scope, "title": k.title, "symptom": k.symptom,
            "cause": k.cause, "resolution": k.resolution, "product": k.product,
            "severity": k.severity, "tags": [t for t in k.tags.split(",") if t],
            "status": k.status, "source": k.source, "created_at": k.created_at.isoformat()}


class KnownErrorIn(BaseModel):
    title: str
    symptom: str = ""
    cause: str = ""
    resolution: str = ""
    product: str = ""
    severity: str = "medium"
    tags: list[str] = []
    scope: str = "tenant"          # tenant | shared (shared requiere ADMIN)
    status: str = "published"
    source: str = ""


@router.get("/status")
def status(tenant: Tenant = Depends(get_current_tenant),
           _: User = Depends(get_current_user), session: Session = Depends(get_session)) -> dict:
    return {"enabled": kedb_enabled(session, tenant)}


@router.get("")
def list_errors(q: str = "", severity: str = "", product: str = "",
                tenant: Tenant = Depends(get_current_tenant),
                _: User = Depends(get_current_user), session: Session = Depends(get_session)) -> list[dict]:
    _require_kedb(session, tenant)
    # Propios del tenant + los 'shared' (cross-cliente curados).
    rows = session.exec(
        select(KnownError).where(
            or_(KnownError.tenant_id == tenant.id, KnownError.scope == "shared"))
        .order_by(KnownError.created_at.desc())
    ).all()
    ql = q.lower().strip()
    out = []
    for k in rows:
        if severity and k.severity != severity:
            continue
        if product and product.lower() not in (k.product or "").lower():
            continue
        if ql and ql not in f"{k.title} {k.symptom} {k.cause} {k.resolution} {k.tags}".lower():
            continue
        out.append(_out(k))
    return out


@router.post("", status_code=201)
def create_error(body: KnownErrorIn, tenant: Tenant = Depends(get_current_tenant),
                 user: User = Depends(get_current_user), session: Session = Depends(get_session)) -> dict:
    _require_kedb(session, tenant)
    if not body.title.strip():
        raise HTTPException(status_code=422, detail="El título es obligatorio")
    scope = "shared" if (body.scope == "shared" and user.role == Role.ADMIN) else "tenant"
    k = KnownError(
        tenant_id=tenant.id, scope=scope, title=body.title.strip(), symptom=body.symptom.strip(),
        cause=body.cause.strip(), resolution=body.resolution.strip(), product=body.product.strip(),
        severity=body.severity if body.severity in _SEVERITY else "medium",
        tags=",".join(t.strip() for t in body.tags if t.strip()),
        status=body.status if body.status in ("draft", "published") else "published",
        source=body.source.strip(), created_by=user.id)
    session.add(k)
    session.add(AuditEvent(
        tenant_id=tenant.id, user_id=user.id, event_type="kedb", object_type="known_error",
        object_id=k.id, risk_level="low", reason=f"KEDB alta '{k.title}' ({scope})"))
    session.commit()
    session.refresh(k)
    return _out(k)


@router.patch("/{error_id}")
def update_error(error_id: str, body: KnownErrorIn, tenant: Tenant = Depends(get_current_tenant),
                 user: User = Depends(get_current_user), session: Session = Depends(get_session)) -> dict:
    _require_kedb(session, tenant)
    k = session.get(KnownError, error_id)
    if not k or (k.tenant_id != tenant.id and k.scope != "shared"):
        raise HTTPException(status_code=404, detail="Error conocido no encontrado")
    k.title = body.title.strip() or k.title
    k.symptom, k.cause, k.resolution = body.symptom.strip(), body.cause.strip(), body.resolution.strip()
    k.product = body.product.strip()
    k.severity = body.severity if body.severity in _SEVERITY else k.severity
    k.tags = ",".join(t.strip() for t in body.tags if t.strip())
    k.status = body.status if body.status in ("draft", "published") else k.status
    k.updated_at = datetime.utcnow()
    session.add(k)
    session.commit()
    session.refresh(k)
    return _out(k)


@router.delete("/{error_id}")
def delete_error(error_id: str, tenant: Tenant = Depends(get_current_tenant),
                 _: User = Depends(require_roles(Role.ADMIN, Role.SECURITY, Role.DEVOPS)),
                 session: Session = Depends(get_session)) -> dict:
    _require_kedb(session, tenant)
    k = session.get(KnownError, error_id)
    if not k or k.tenant_id != tenant.id:
        raise HTTPException(status_code=404, detail="Error conocido no encontrado (o es 'shared' del operador)")
    session.delete(k)
    session.commit()
    return {"ok": True}


class AnalyzeIn(BaseModel):
    symptom: str
    product: str = ""


@router.post("/analyze")
def analyze(body: AnalyzeIn, tenant: Tenant = Depends(get_current_tenant),
            _: User = Depends(get_current_user), session: Session = Depends(get_session)) -> dict:
    """Dado un síntoma, busca coincidencias en la KEDB (propias + shared) y, si hay
    proveedor, sugiere diagnóstico/resolución con IA basándose en esos casos."""
    _require_kedb(session, tenant)
    rows = session.exec(
        select(KnownError).where(
            or_(KnownError.tenant_id == tenant.id, KnownError.scope == "shared"))).all()
    terms = [t for t in body.symptom.lower().split() if len(t) > 2]

    def score(k: KnownError) -> int:
        hay = f"{k.title} {k.symptom} {k.cause} {k.resolution} {k.product} {k.tags}".lower()
        s = sum(1 for t in terms if t in hay)
        if body.product and body.product.lower() in (k.product or "").lower():
            s += 2
        return s

    ranked = sorted(((score(k), k) for k in rows), key=lambda x: -x[0])
    matches = [_out(k) for s, k in ranked if s > 0][:5]

    suggestion = ""
    try:
        from ..ai.resilience import generate_with_fallback
        from ..ai.router import route_request
        ctx = [f"{m['title']} — síntoma: {m['symptom']} · causa: {m['cause']} · solución: {m['resolution']}"
               for m in matches]
        system = ("Eres analista de SOC. Con los errores conocidos provistos, indica en español y en "
                  "texto plano si el síntoma coincide con un error conocido, la causa probable y la "
                  "resolución sugerida. Si no hay coincidencia clara, dilo y sugiere primeros pasos.")
        prompt = f"Síntoma: {body.symptom}. Producto: {body.product or 'N/D'}.\n\nErrores conocidos:\n" + "\n".join(ctx)
        decision = route_request(tenant, None, prompt, ctx, task="recipe")
        gen = generate_with_fallback(decision.route, system, prompt, decision.context or ctx)
        suggestion = (gen.response.content or "").strip()
    except Exception:
        suggestion = ""

    return {"matches": matches, "is_known": bool(matches), "suggestion": suggestion}
