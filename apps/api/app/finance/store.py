"""Persistencia por tenant del dataset del Tablero Financiero (cifrado).

El tablero lee de aquí primero (lo que el cliente subió en la app); si no hay nada,
cae al dataset inyectado por entorno o al demo (ver ``dataset.py``).
"""
from __future__ import annotations

import json
from datetime import datetime

from sqlmodel import Session, select

from ..models import FinanceDataset, Tenant
from ..security.crypto import decrypt, encrypt


def get_dataset(session: Session, tenant: Tenant) -> dict | None:
    row = session.get(FinanceDataset, tenant.id)
    if not row or not row.payload_enc:
        return None
    try:
        data = json.loads(decrypt(row.payload_enc, tenant.kms_key_id))
    except Exception:
        return None
    data["_origin"] = f"tenant:{row.source}"
    data["_is_demo"] = False
    data["_updated_at"] = row.updated_at.isoformat()
    data["_filename"] = row.filename
    return data


def save_dataset(session: Session, tenant: Tenant, data: dict, *, source: str,
                 filename: str, user_id: str = "") -> FinanceDataset:
    clean = {k: v for k, v in data.items() if not k.startswith("_")}
    payload = encrypt(json.dumps(clean, ensure_ascii=False), tenant.kms_key_id)
    row = session.get(FinanceDataset, tenant.id)
    if row is None:
        row = FinanceDataset(tenant_id=tenant.id)
    row.payload_enc = payload
    row.source = source
    row.filename = filename[:300]
    row.updated_at = datetime.utcnow()
    row.updated_by = user_id
    session.add(row)
    session.commit()
    session.refresh(row)
    return row


def delete_dataset(session: Session, tenant: Tenant) -> bool:
    row = session.get(FinanceDataset, tenant.id)
    if not row:
        return False
    session.delete(row)
    session.commit()
    return True


def status(session: Session, tenant: Tenant) -> dict:
    row = session.get(FinanceDataset, tenant.id)
    if not row:
        return {"loaded": False}
    return {"loaded": True, "source": row.source, "filename": row.filename,
            "updated_at": row.updated_at.isoformat(), "updated_by": row.updated_by}
