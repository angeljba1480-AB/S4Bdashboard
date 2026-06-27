"""/voice — TTS (kokoro) y STT (whisper) vía el proveedor abierto (NaN)."""
from __future__ import annotations

from fastapi import APIRouter, Depends, File, Form, HTTPException, UploadFile
from fastapi.responses import Response
from pydantic import BaseModel
from sqlmodel import Session

from ..ai import voice
from ..auth import get_current_tenant, get_current_user
from ..db import get_session
from ..models import AuditEvent, Tenant, User

router = APIRouter(prefix="/voice", tags=["voice"])


@router.get("/config")
def voice_config(_: User = Depends(get_current_user)) -> dict:
    return {"configured": voice.is_configured(),
            "voices": [{"id": k, "label": v} for k, v in voice.VOICES.items()]}


class TTSIn(BaseModel):
    text: str
    voice: str = ""
    format: str = "mp3"


@router.post("/tts")
def tts(
    body: TTSIn,
    tenant: Tenant = Depends(get_current_tenant),
    user: User = Depends(get_current_user),
    session: Session = Depends(get_session),
) -> Response:
    text = (body.text or "").strip()
    if not text:
        raise HTTPException(status_code=422, detail="Escribe el texto a narrar.")
    try:
        audio, mime = voice.tts(text, voice=body.voice, fmt=body.format)
    except Exception as exc:
        raise HTTPException(status_code=400, detail=f"No se pudo sintetizar: {exc}")
    session.add(AuditEvent(
        tenant_id=tenant.id, user_id=user.id, event_type="voice", object_type="tts",
        object_id="", risk_level="low", reason=f"TTS ({body.voice or 'default'}) {len(text)} chars"))
    session.commit()
    return Response(content=audio, media_type=mime)


@router.post("/transcribe")
def transcribe(
    file: UploadFile = File(...),
    language: str = Form(""),
    tenant: Tenant = Depends(get_current_tenant),
    user: User = Depends(get_current_user),
    session: Session = Depends(get_session),
) -> dict:
    raw = file.file.read()
    if not raw:
        raise HTTPException(status_code=422, detail="Sube un archivo de audio.")
    if len(raw) > 25 * 1024 * 1024:
        raise HTTPException(status_code=422, detail="El audio supera el límite de 25 MB.")
    try:
        result = voice.stt(raw, filename=file.filename or "audio.mp3", language=language.strip())
    except Exception as exc:
        raise HTTPException(status_code=400, detail=f"No se pudo transcribir: {exc}")
    session.add(AuditEvent(
        tenant_id=tenant.id, user_id=user.id, event_type="voice", object_type="stt",
        object_id="", risk_level="low", reason=f"STT {file.filename or ''} → {len(result.get('text',''))} chars"))
    session.commit()
    return result
