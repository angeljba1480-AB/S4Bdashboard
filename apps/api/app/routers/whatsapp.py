"""/whatsapp — envío de mensajes a WhatsApp vía CallMeBot (config por usuario).

Configura una vez tu número + apikey (cifrada) y luego puedes enviar a WhatsApp el
resultado de un caso de uso, una prueba, o recibir las alertas por este canal.
"""
from __future__ import annotations

from fastapi import APIRouter, Depends, HTTPException
from pydantic import BaseModel
from sqlmodel import Session

from ..auth import get_current_tenant, get_current_user
from ..db import get_session
from ..integrations import whatsapp as wa
from ..models import Tenant, User
from ..security.crypto import decrypt, encrypt

router = APIRouter(prefix="/whatsapp", tags=["whatsapp"])


def _apikey(tenant: Tenant, user: User) -> str:
    if not user.callmebot_apikey_enc:
        return ""
    try:
        return decrypt(user.callmebot_apikey_enc, tenant.kms_key_id)
    except Exception:
        return ""


@router.get("/config")
def get_config(tenant: Tenant = Depends(get_current_tenant),
               user: User = Depends(get_current_user)) -> dict:
    return {"phone": user.callmebot_phone or "", "configured": bool(user.callmebot_phone and user.callmebot_apikey_enc)}


class ConfigIn(BaseModel):
    phone: str = ""
    apikey: str = ""


@router.post("/config")
def set_config(body: ConfigIn, tenant: Tenant = Depends(get_current_tenant),
               user: User = Depends(get_current_user), session: Session = Depends(get_session)) -> dict:
    phone = body.phone.strip()
    if phone and not phone.startswith("+"):
        raise HTTPException(status_code=422, detail="El número debe ir en formato internacional, p. ej. +5215512345678")
    user.callmebot_phone = phone
    if body.apikey.strip():
        user.callmebot_apikey_enc = encrypt(body.apikey.strip(), tenant.kms_key_id)
    if not phone:
        user.callmebot_apikey_enc = ""  # limpiar = desconectar
    session.add(user); session.commit()
    return {"phone": user.callmebot_phone, "configured": bool(user.callmebot_phone and user.callmebot_apikey_enc)}


class SendIn(BaseModel):
    text: str


def _send_for_user(tenant: Tenant, user: User, text: str) -> tuple[bool, str]:
    return wa.send_callmebot(user.callmebot_phone, _apikey(tenant, user), text)


@router.post("/send")
def send(body: SendIn, tenant: Tenant = Depends(get_current_tenant),
         user: User = Depends(get_current_user)) -> dict:
    if not (user.callmebot_phone and user.callmebot_apikey_enc):
        raise HTTPException(status_code=400, detail="Configura WhatsApp (CallMeBot) primero en Alertas → WhatsApp.")
    ok, detail = _send_for_user(tenant, user, body.text)
    if not ok:
        raise HTTPException(status_code=502, detail=detail)
    return {"ok": True, "detail": detail}


@router.post("/test")
def test(tenant: Tenant = Depends(get_current_tenant),
         user: User = Depends(get_current_user)) -> dict:
    if not (user.callmebot_phone and user.callmebot_apikey_enc):
        raise HTTPException(status_code=400, detail="Configura tu número y apikey de CallMeBot primero.")
    ok, detail = _send_for_user(tenant, user, "✅ MaestroAI: WhatsApp configurado correctamente.")
    return {"ok": ok, "detail": detail}
