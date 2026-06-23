"""Company profile helpers: onboarding state, completion and prompt context.

Kept separate from the router so the recipe engine can reuse the prompt-context
builder without importing FastAPI route handlers (avoids import cycles).
"""
from __future__ import annotations

import json

from sqlmodel import Session, select

from .models import CompanyProfile

# Fields that count toward the onboarding completion score (weight = 1 each).
_SCORED = ("industry", "company_size", "description", "audience", "value_prop", "tone")


def get_or_create(session: Session, tenant_id: str) -> CompanyProfile:
    profile = session.exec(
        select(CompanyProfile).where(CompanyProfile.tenant_id == tenant_id)
    ).first()
    if not profile:
        profile = CompanyProfile(tenant_id=tenant_id)
        session.add(profile)
        session.commit()
        session.refresh(profile)
    return profile


def _load_list(raw: str) -> list:
    try:
        value = json.loads(raw or "[]")
        return value if isinstance(value, list) else []
    except (ValueError, TypeError):
        return []


def areas_list(profile: CompanyProfile) -> list[dict]:
    """Normalized list of {name, responsible, email} for the company's areas."""
    out: list[dict] = []
    for a in _load_list(profile.areas):
        if isinstance(a, dict) and str(a.get("name", "")).strip():
            out.append({
                "name": str(a.get("name", "")).strip(),
                "responsible": str(a.get("responsible", "")).strip(),
                "email": str(a.get("email", "")).strip(),
            })
        elif isinstance(a, str) and a.strip():
            out.append({"name": a.strip(), "responsible": "", "email": ""})
    return out


def tech_list(profile: CompanyProfile) -> list[str]:
    return [str(t).strip() for t in _load_list(profile.tech_stack) if str(t).strip()]


def completion(profile: CompanyProfile) -> int:
    """0–100 score so the UI can show onboarding progress and nudge completion."""
    filled = sum(1 for f in _SCORED if str(getattr(profile, f, "")).strip())
    bonus = (1 if areas_list(profile) else 0) + (1 if tech_list(profile) else 0)
    total = len(_SCORED) + 2
    return round((filled + bonus) / total * 100)


def to_dict(profile: CompanyProfile) -> dict:
    return {
        "industry": profile.industry,
        "company_size": profile.company_size,
        "description": profile.description,
        "audience": profile.audience,
        "value_prop": profile.value_prop,
        "goals": profile.goals,
        "tone": profile.tone,
        "website": profile.website,
        "areas": areas_list(profile),
        "tech_stack": tech_list(profile),
        "completed": profile.completed,
        "completion": completion(profile),
    }


def context_block(profile: CompanyProfile, company_name: str = "") -> str:
    """Compact business context injected into use-case prompts so output is
    pre-configured to the company (no PII; only org-level descriptors)."""
    lines: list[str] = []
    if company_name:
        lines.append(f"Empresa: {company_name}")
    if profile.industry:
        lines.append(f"Giro/sector: {profile.industry}")
    if profile.company_size:
        lines.append(f"Tamaño: {profile.company_size}")
    if profile.description:
        lines.append(f"A qué se dedica: {profile.description}")
    if profile.audience:
        lines.append(f"Clientes/mercado: {profile.audience}")
    if profile.value_prop:
        lines.append(f"Propuesta de valor: {profile.value_prop}")
    if profile.goals:
        lines.append(f"Objetivos: {profile.goals}")
    if profile.tone:
        lines.append(f"Tono de comunicación: {profile.tone}")
    areas = areas_list(profile)
    if areas:
        lines.append("Áreas/responsables: " + "; ".join(
            a["name"] + (f" ({a['responsible']})" if a["responsible"] else "") for a in areas))
    tech = tech_list(profile)
    if tech:
        lines.append("Tecnología que usa: " + ", ".join(tech))
    if not lines:
        return ""
    return "Contexto de la empresa (úsalo para personalizar el resultado):\n" + "\n".join(lines)
