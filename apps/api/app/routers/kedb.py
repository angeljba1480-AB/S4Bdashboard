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
from sqlmodel import Session, and_, or_, select

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
    # Propios del tenant (cualquier estado) + 'shared' PUBLICADOS (cross-cliente
    # curados/aprobados). Los 'shared' pendientes solo se ven en /proposals.
    rows = session.exec(
        select(KnownError).where(
            or_(KnownError.tenant_id == tenant.id,
                and_(KnownError.scope == "shared", KnownError.status == "published")))
        .order_by(KnownError.created_at.desc())
    ).all()
    ql = q.lower().strip()
    out = []
    for k in rows:
        # Propuestas cross-cliente pendientes viven en /proposals, no en la lista.
        if k.scope == "shared" and k.status != "published":
            continue
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


# --- Cross-cliente: promover (sanitizado) → aprobar (operador) ---------------
def _first_json(text: str) -> dict:
    import json
    import re
    m = re.search(r"\{.*\}", text or "", re.S)
    if not m:
        return {}
    try:
        return json.loads(m.group(0))
    except Exception:
        return {}


def _sanitize_fields(tenant: Tenant, k: KnownError) -> dict:
    """Quita datos identificables (cliente, IPs, hosts, usuarios) para compartir
    el error entre clientes. Best-effort con IA; el operador revisa antes de aprobar."""
    base = {"title": k.title, "symptom": k.symptom, "cause": k.cause,
            "resolution": k.resolution, "product": k.product, "tags": k.tags}
    try:
        from ..ai.resilience import generate_with_fallback
        from ..ai.router import route_request
        system = ("Sanitiza un error conocido para compartirlo ENTRE CLIENTES distintos: ELIMINA nombres "
                  "de cliente/empresa, IPs, hostnames, usuarios, correos, rutas internas y cualquier dato "
                  "identificable; conserva el patrón técnico. Devuelve SOLO un JSON con las claves "
                  "title, symptom, cause, resolution, product, tags (tags como texto separado por comas).")
        import json
        prompt = json.dumps(base, ensure_ascii=False)
        decision = route_request(tenant, None, prompt, [], task="recipe")
        gen = generate_with_fallback(decision.route, system, prompt, [])
        data = _first_json(gen.response.content or "")
        for key in base:
            v = data.get(key)
            if isinstance(v, list):
                v = ",".join(str(x) for x in v)
            if isinstance(v, str) and v.strip():
                base[key] = v.strip()
    except Exception:
        pass
    return base


@router.post("/{error_id}/promote", status_code=201)
def promote(error_id: str, tenant: Tenant = Depends(get_current_tenant),
            user: User = Depends(require_roles(Role.ADMIN, Role.SECURITY)),
            session: Session = Depends(get_session)) -> dict:
    """Propone un error propio como CROSS-CLIENTE: crea una copia sanitizada con
    scope='shared' y status='pending' que el operador (super admin) revisa y aprueba."""
    _require_kedb(session, tenant)
    k = session.get(KnownError, error_id)
    if not k or k.tenant_id != tenant.id or k.scope != "tenant":
        raise HTTPException(status_code=404, detail="Error propio no encontrado")
    s = _sanitize_fields(tenant, k)
    cand = KnownError(
        tenant_id=tenant.id, scope="shared", status="pending",
        title=s["title"], symptom=s["symptom"], cause=s["cause"], resolution=s["resolution"],
        product=s["product"], severity=k.severity, tags=s["tags"],
        source=f"propuesto desde {tenant.name} (sanitizado)", created_by=user.id)
    session.add(cand)
    session.add(AuditEvent(
        tenant_id=tenant.id, user_id=user.id, event_type="kedb", object_type="known_error",
        object_id=cand.id, risk_level="med",
        reason=f"propuesta cross-cliente '{cand.title}' (pendiente de aprobación)"))
    session.commit()
    session.refresh(cand)
    return _out(cand)


@router.get("/proposals")
def proposals(_: User = Depends(require_roles(Role.SUPER_ADMIN)),
              tenant: Tenant = Depends(get_current_tenant),
              session: Session = Depends(get_session)) -> list[dict]:
    """Propuestas cross-cliente pendientes (solo el operador/super admin)."""
    rows = session.exec(
        select(KnownError).where(KnownError.scope == "shared", KnownError.status == "pending")
        .order_by(KnownError.created_at.desc())).all()
    return [{**_out(k), "source": k.source} for k in rows]


@router.post("/proposals/{error_id}/approve")
def approve_proposal(error_id: str, user: User = Depends(require_roles(Role.SUPER_ADMIN)),
                     tenant: Tenant = Depends(get_current_tenant),
                     session: Session = Depends(get_session)) -> dict:
    """El operador publica la propuesta: queda visible para todos los tenants cyber."""
    k = session.get(KnownError, error_id)
    if not k or k.scope != "shared" or k.status != "pending":
        raise HTTPException(status_code=404, detail="Propuesta no encontrada")
    k.status = "published"
    k.updated_at = datetime.utcnow()
    session.add(k)
    session.add(AuditEvent(
        tenant_id=tenant.id, user_id=user.id, event_type="kedb", object_type="known_error",
        object_id=k.id, risk_level="med", reason=f"propuesta cross-cliente APROBADA '{k.title}'"))
    session.commit()
    return _out(k)


@router.post("/proposals/{error_id}/reject")
def reject_proposal(error_id: str, _: User = Depends(require_roles(Role.SUPER_ADMIN)),
                    session: Session = Depends(get_session)) -> dict:
    k = session.get(KnownError, error_id)
    if not k or k.scope != "shared" or k.status != "pending":
        raise HTTPException(status_code=404, detail="Propuesta no encontrada")
    session.delete(k)
    session.commit()
    return {"ok": True}


class ExtractIn(BaseModel):
    text: str


@router.post("/extract")
def extract(body: ExtractIn, tenant: Tenant = Depends(get_current_tenant),
            _: User = Depends(get_current_user), session: Session = Depends(get_session)) -> dict:
    """Extrae un error conocido ESTRUCTURADO desde texto libre (log/incidente) con IA.
    Devuelve un borrador (no lo guarda); el usuario lo revisa y da de alta."""
    _require_kedb(session, tenant)
    draft = {"title": "", "symptom": "", "cause": "", "resolution": "", "product": "", "tags": ""}
    try:
        from ..ai.resilience import generate_with_fallback
        from ..ai.router import route_request
        system = ("Eres analista de SOC. Del texto del incidente extrae un error conocido y devuelve SOLO "
                  "un JSON con: title, symptom, cause, resolution, product, tags (coma). Si algo no está, déjalo vacío.")
        prompt = f"Incidente:\n{body.text[:4000]}"
        decision = route_request(tenant, None, prompt, [], task="recipe")
        gen = generate_with_fallback(decision.route, system, prompt, [])
        data = _first_json(gen.response.content or "")
        for key in draft:
            v = data.get(key)
            if isinstance(v, list):
                v = ",".join(str(x) for x in v)
            if isinstance(v, str):
                draft[key] = v.strip()
    except Exception:
        pass
    return {"draft": draft}
