"""Marca blanca: utilidades de branding por tenant (correos, dominio)."""
from __future__ import annotations

from .models import Tenant


def base_url(tenant: Tenant, default: str = "") -> str:
    """Dominio del cliente si lo configuró (marca blanca), si no el default."""
    d = (tenant.custom_domain or "").strip()
    return f"https://{d}" if d else default


def email_footer(tenant: Tenant) -> str:
    """Firma/pie de correo con la marca del tenant (marca blanca). Vacío si no hay
    marca configurada — así no estampa 'MaestroAI' en correos del cliente."""
    name = (tenant.brand_name or "").strip()
    if not name:
        return ""
    parts = [f"— {name}"]
    tagline = (tenant.brand_tagline or "").strip()
    if tagline:
        parts.append(tagline)
    dom = (tenant.custom_domain or "").strip()
    if dom:
        parts.append(dom)
    return "\n".join(parts)


def with_signature(tenant: Tenant, body: str) -> str:
    """Agrega el pie de marca al cuerpo del correo, si hay marca configurada."""
    footer = email_footer(tenant)
    return f"{body}\n\n{footer}" if footer else body
