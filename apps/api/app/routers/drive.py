"""/drive — pick Google Drive files/folders as RAG context.

Reuses the user's Google OAuth connection (requires the drive.readonly scope, so
the user may need to reconnect Google once). Imported files go through the same
classify → PII → index pipeline as uploads, tagged with an area/category.
"""
from __future__ import annotations

import hashlib

import httpx
from fastapi import APIRouter, Depends, HTTPException
from pydantic import BaseModel
from sqlmodel import Session

from .. import doc_categories
from ..ai.rag import index_document
from ..auth import get_current_tenant, get_current_user
from ..db import get_session
from ..integrations import token_store
from ..models import AuditEvent, Document, Tenant, User
from ..security.classifier import classify_data

router = APIRouter(prefix="/drive", tags=["drive"])

DRIVE_FILES = "https://www.googleapis.com/drive/v3/files"
# Google-native types we export to text; everything else is downloaded as-is.
_EXPORT = {
    "application/vnd.google-apps.document": "text/plain",
    "application/vnd.google-apps.spreadsheet": "text/csv",
    "application/vnd.google-apps.presentation": "text/plain",
}


def _token(session: Session, tenant: Tenant, user: User) -> str:
    tok = token_store.get_valid_access_token(session, tenant, user.id, "google")
    if not tok:
        raise HTTPException(status_code=400, detail="Conecta Google primero en Integraciones.")
    return tok


@router.get("/files")
def list_files(
    query: str = "",
    folder: str = "",
    tenant: Tenant = Depends(get_current_tenant),
    user: User = Depends(get_current_user),
    session: Session = Depends(get_session),
) -> dict:
    """List Drive files (optionally filtered by name or parent folder)."""
    token = _token(session, tenant, user)
    clauses = ["trashed = false"]
    if folder:
        clauses.append(f"'{folder.replace(chr(39), ' ')}' in parents")
    elif not query:
        clauses.append("'root' in parents")   # vista inicial = nivel superior (no volcado plano)
    if query:
        safe = query.replace("'", " ")
        clauses.append(f"name contains '{safe}'")
    params = {
        "q": " and ".join(clauses),
        "pageSize": 50,
        "fields": "files(id,name,mimeType,modifiedTime,iconLink)",
        "orderBy": "folder,modifiedTime desc",
    }
    r = httpx.get(DRIVE_FILES, headers={"Authorization": f"Bearer {token}"}, params=params, timeout=20)
    if r.status_code == 403:
        raise HTTPException(status_code=400, detail=(
            "Falta el permiso de Drive. Reconecta Google en Integraciones para autorizar el acceso de solo lectura."))
    r.raise_for_status()
    out = []
    for f in r.json().get("files", []):
        out.append({
            "id": f["id"], "name": f.get("name", "(sin nombre)"),
            "mime_type": f.get("mimeType", ""),
            "is_folder": f.get("mimeType") == "application/vnd.google-apps.folder",
            "modified": f.get("modifiedTime", ""),
        })
    return {"files": out}


def _download_text(token: str, file_id: str, mime: str) -> str:
    headers = {"Authorization": f"Bearer {token}"}
    if mime in _EXPORT:
        r = httpx.get(f"{DRIVE_FILES}/{file_id}/export",
                      headers=headers, params={"mimeType": _EXPORT[mime]}, timeout=40)
    else:
        r = httpx.get(f"{DRIVE_FILES}/{file_id}", headers=headers, params={"alt": "media"}, timeout=40)
    r.raise_for_status()
    return r.content.decode("utf-8", errors="ignore")


class ImportBody(BaseModel):
    file_id: str
    name: str = ""
    mime_type: str = ""
    area: str = ""
    category: str = ""


@router.post("/import", status_code=201)
def import_file(
    body: ImportBody,
    tenant: Tenant = Depends(get_current_tenant),
    user: User = Depends(get_current_user),
    session: Session = Depends(get_session),
) -> dict:
    """Import a Drive file into the company repository + RAG index."""
    token = _token(session, tenant, user)
    if body.mime_type == "application/vnd.google-apps.folder":
        raise HTTPException(status_code=400, detail="Selecciona un archivo, no una carpeta.")
    try:
        content = _download_text(token, body.file_id, body.mime_type)
    except Exception:
        raise HTTPException(status_code=400, detail="No se pudo descargar el archivo de Drive.")
    if not content.strip():
        raise HTTPException(status_code=400, detail="El archivo está vacío o no es de texto.")

    name = body.name or "drive-import.txt"
    cls = classify_data(content)
    cat = doc_categories.get_or_create(session, tenant.id, body.category or "")
    doc = Document(
        tenant_id=tenant.id, owner_id=user.id, filename=name, mime_type="text/plain",
        area=(body.area or "").strip(), category=cat.key if cat else "",
        sensitivity=cls.sensitivity, pii_score=cls.pii.score, pii_types=",".join(cls.pii.types),
        storage_uri=f"gdrive://{body.file_id}", hash=hashlib.sha256(content.encode()).hexdigest(),
        text=content,
    )
    session.add(doc)
    session.commit()
    session.refresh(doc)
    chunks = index_document(session, doc)
    session.add(AuditEvent(
        tenant_id=tenant.id, user_id=user.id, event_type="upload", object_type="document",
        object_id=doc.id, classification=doc.sensitivity, risk_level="low",
        reason=f"importado de Google Drive ({name}); {chunks} chunks",
    ))
    session.commit()
    return {"id": doc.id, "filename": doc.filename, "sensitivity": doc.sensitivity.value,
            "category": doc.category, "area": doc.area}
