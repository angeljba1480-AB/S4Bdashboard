"""Document category catalog: built-in defaults + helpers to seed/extend it.

Categories organize uploaded company files by type (proposal templates, tender
master docs, contracts, ISO certs, …). The catalog is per-tenant and extensible:
recipes or users can add new categories, and uploading with an unknown category
auto-creates it so the taxonomy grows with the business.
"""
from __future__ import annotations

import re

from sqlmodel import Session, select

from .models import DocumentCategory

# (key, label, description) — order is the display order in the UI.
DEFAULT_CATEGORIES: list[tuple[str, str, str]] = [
    ("propuesta_comercial", "Propuesta comercial", "Formatos y plantillas de propuestas comerciales."),
    ("oferta_ip", "Oferta para IP", "Ofertas para iniciativa privada."),
    ("oferta_gob", "Oferta para Gobierno", "Ofertas y respuestas para gobierno / sector público."),
    ("licitacion_madre", "Documento madre de licitación", "Documento base/maestro para responder licitaciones."),
    ("contrato_empleado", "Contrato de empleado", "Contratos y plantillas laborales."),
    ("contrato_cliente", "Contrato de cliente", "Contratos y acuerdos con clientes."),
    ("entregable", "Entregable", "Tipos y plantillas de entregables."),
    ("certificacion_iso", "Certificación ISO", "Certificaciones, normas y políticas ISO."),
    ("conocimiento", "Base de conocimiento", "Información empresarial general para agilizar procesos."),
    ("otro", "Otro", "Sin categoría específica."),
]


def slugify(value: str) -> str:
    s = re.sub(r"[^a-z0-9]+", "_", (value or "").strip().lower()).strip("_")
    return s or "otro"


def ensure_defaults(session: Session, tenant_id: str) -> None:
    """Seed the built-in categories for a tenant once (idempotent)."""
    existing = {
        c.key for c in session.exec(
            select(DocumentCategory).where(DocumentCategory.tenant_id == tenant_id)
        ).all()
    }
    added = False
    for key, label, desc in DEFAULT_CATEGORIES:
        if key not in existing:
            session.add(DocumentCategory(
                tenant_id=tenant_id, key=key, label=label, description=desc, system=True))
            added = True
    if added:
        session.commit()


def list_categories(session: Session, tenant_id: str) -> list[DocumentCategory]:
    ensure_defaults(session, tenant_id)
    return session.exec(
        select(DocumentCategory).where(DocumentCategory.tenant_id == tenant_id)
    ).all()


def get_or_create(session: Session, tenant_id: str, key_or_label: str,
                  label: str = "", description: str = "") -> DocumentCategory | None:
    """Resolve a category by key or label; create it if missing. Returns None for
    empty input so 'sin categoría' stays valid."""
    raw = (key_or_label or "").strip()
    if not raw:
        return None
    ensure_defaults(session, tenant_id)
    rows = session.exec(
        select(DocumentCategory).where(DocumentCategory.tenant_id == tenant_id)
    ).all()
    key = slugify(raw)
    for c in rows:
        if c.key == key or c.label.lower() == raw.lower():
            return c
    cat = DocumentCategory(
        tenant_id=tenant_id, key=key, label=label or raw, description=description, system=False)
    session.add(cat)
    session.commit()
    session.refresh(cat)
    return cat
