"""/images — text-to-image generation (NaN / FLUX) with a governed gallery.

Generation runs through the open provider (OpenAI-compatible). PII in the prompt is
redacted before the external call; each image is stored (copy in the tenant) and
audited. The gallery is area-scoped like documents.
"""
from __future__ import annotations

import base64

from fastapi import APIRouter, Depends, File, Form, HTTPException, UploadFile
from fastapi.responses import Response
from pydantic import BaseModel
from sqlmodel import Session, select

from ..ai import images as imagegen
from ..auth import get_current_tenant, get_current_user
from ..db import get_session
from ..models import AuditEvent, GeneratedImage, Tenant, User
from ..permissions import can_view_area, visible_areas

router = APIRouter(prefix="/images", tags=["images"])


def _out(img: GeneratedImage) -> dict:
    return {"id": img.id, "prompt": img.prompt, "model": img.model, "size": img.size,
            "provider": img.provider, "area": img.area or "", "has_data": bool(img.data_b64),
            "source_url": img.source_url, "created_at": img.created_at.isoformat()}


class GenerateIn(BaseModel):
    prompt: str
    aspect_ratio: str = "1:1"
    variants: int = 1
    model: str | None = None


@router.get("/config")
def image_config(
    _: User = Depends(get_current_user),
) -> dict:
    """Whether a real image provider is configured + the available aspect ratios."""
    return {"configured": imagegen.is_configured(),
            "aspect_ratios": list(imagegen.ASPECT_SIZES.keys()),
            "default_model": imagegen.DEFAULT_IMAGE_MODEL}


@router.post("/generate", status_code=201)
def generate_images(
    body: GenerateIn,
    tenant: Tenant = Depends(get_current_tenant),
    user: User = Depends(get_current_user),
    session: Session = Depends(get_session),
) -> dict:
    prompt = (body.prompt or "").strip()
    if not prompt:
        raise HTTPException(status_code=422, detail="Escribe una descripción (prompt).")
    size = imagegen.ASPECT_SIZES.get(body.aspect_ratio, imagegen.ASPECT_SIZES["1:1"])
    n = max(1, min(int(body.variants or 1), 4))
    try:
        results = imagegen.generate(prompt, n=n, size=size, model=body.model)
    except Exception as exc:
        raise HTTPException(status_code=400, detail=f"No se pudo generar: {exc}")

    saved = []
    for g in results:
        img = GeneratedImage(
            tenant_id=tenant.id, owner_id=user.id, prompt=prompt,
            model=body.model or "", size=size, provider="open",
            source_url=g.url, data_b64=g.data_b64, mime_type=g.mime_type,
            area=user.area or "",
        )
        session.add(img)
        saved.append(img)
    session.add(AuditEvent(
        tenant_id=tenant.id, user_id=user.id, event_type="generate", object_type="image",
        object_id=saved[0].id if saved else "", risk_level="low",
        reason=f"generó {len(saved)} imagen(es) ({size}) con prompt: {prompt[:60]}",
    ))
    session.commit()
    for img in saved:
        session.refresh(img)
    return {"images": [_out(i) for i in saved]}


@router.post("/edit", status_code=201)
def edit_images(
    prompt: str = Form(...),
    aspect_ratio: str = Form("1:1"),
    variants: int = Form(1),
    files: list[UploadFile] = File(...),
    tenant: Tenant = Depends(get_current_tenant),
    user: User = Depends(get_current_user),
    session: Session = Depends(get_session),
) -> dict:
    """Image-to-image: edita/transforma con hasta 4 imágenes de referencia."""
    prompt = (prompt or "").strip()
    if not prompt:
        raise HTTPException(status_code=422, detail="Escribe qué edición aplicar (prompt).")
    refs: list[tuple[str, bytes]] = []
    for f in files[:4]:
        raw = f.file.read()
        if raw:
            if len(raw) > 25 * 1024 * 1024:
                raise HTTPException(status_code=422, detail="Cada imagen debe pesar < 25 MB.")
            refs.append((f.filename or "ref.png", raw))
    if not refs:
        raise HTTPException(status_code=422, detail="Sube al menos una imagen de referencia.")
    size = imagegen.ASPECT_SIZES.get(aspect_ratio, imagegen.ASPECT_SIZES["1:1"])
    n = max(1, min(int(variants or 1), 4))
    try:
        results = imagegen.edit(prompt, refs, n=n, size=size)
    except Exception as exc:
        raise HTTPException(status_code=400, detail=f"No se pudo editar: {exc}")

    saved = []
    for g in results:
        img = GeneratedImage(
            tenant_id=tenant.id, owner_id=user.id, prompt=prompt, model="",
            size=size, provider="open", source_url=g.url, data_b64=g.data_b64,
            mime_type=g.mime_type, area=user.area or "",
        )
        session.add(img)
        saved.append(img)
    session.add(AuditEvent(
        tenant_id=tenant.id, user_id=user.id, event_type="generate", object_type="image",
        object_id=saved[0].id if saved else "", risk_level="low",
        reason=f"editó {len(saved)} imagen(es) desde {len(refs)} ref(s): {prompt[:50]}"))
    session.commit()
    for img in saved:
        session.refresh(img)
    return {"images": [_out(i) for i in saved]}


@router.get("")
def list_images(
    tenant: Tenant = Depends(get_current_tenant),
    user: User = Depends(get_current_user),
    session: Session = Depends(get_session),
) -> list[dict]:
    rows = session.exec(
        select(GeneratedImage).where(GeneratedImage.tenant_id == tenant.id)
        .order_by(GeneratedImage.created_at.desc()).limit(100)
    ).all()
    areas = visible_areas(user)  # None = all
    visible = [r for r in rows if areas is None or (r.area or "") in areas or not r.area]
    return [_out(r) for r in visible]


def _owned(session: Session, tenant: Tenant, user: User, img_id: str) -> GeneratedImage:
    img = session.get(GeneratedImage, img_id)
    if not img or img.tenant_id != tenant.id or not can_view_area(user, img.area or ""):
        raise HTTPException(status_code=404, detail="Imagen no encontrada")
    return img


@router.get("/{img_id}/data")
def image_data(
    img_id: str,
    tenant: Tenant = Depends(get_current_tenant),
    user: User = Depends(get_current_user),
    session: Session = Depends(get_session),
) -> Response:
    img = _owned(session, tenant, user, img_id)
    if not img.data_b64:
        raise HTTPException(status_code=404, detail="Sin copia almacenada de la imagen")
    return Response(content=base64.b64decode(img.data_b64), media_type=img.mime_type)


@router.delete("/{img_id}")
def delete_image(
    img_id: str,
    tenant: Tenant = Depends(get_current_tenant),
    user: User = Depends(get_current_user),
    session: Session = Depends(get_session),
) -> dict:
    img = _owned(session, tenant, user, img_id)
    session.delete(img)
    session.commit()
    return {"ok": True}
