"""Seed demo data so the platform is usable immediately after `init_db`."""
from __future__ import annotations

from sqlmodel import Session, select

from .auth import hash_password
from .db import engine
from .models import Agent, Role, Tenant, User

DEMO_PASSWORD = "demo1234"


def seed() -> None:
    from .config import settings

    # En producción no sembramos credenciales demo conocidas (admin@maestroai.mx /
    # demo1234) salvo que se active explícitamente con SEED_DEMO_DATA=true.
    if not settings.should_seed_demo:
        return

    with Session(engine) as session:
        if session.exec(select(Tenant)).first():
            return  # already seeded

        tenant = Tenant(name="MaestroAI", plan="enterprise", region="mx-central",
                        country="MX", brand_name="MaestroAI", brand_tagline="Agentes y casos para LATAM",
                        subscription_status="active", seats_licensed=25)
        session.add(tenant)
        session.commit()
        session.refresh(tenant)

        users = [
            User(tenant_id=tenant.id, email="admin@maestroai.mx", name="Layla Delgadillo",
                 role=Role.ADMIN, password_hash=hash_password(DEMO_PASSWORD), mfa_enabled=False),
            User(tenant_id=tenant.id, email="user@maestroai.mx", name="Usuario Negocio",
                 role=Role.USER, password_hash=hash_password(DEMO_PASSWORD)),
            User(tenant_id=tenant.id, email="security@maestroai.mx", name="Roberto Silva",
                 role=Role.SECURITY, password_hash=hash_password(DEMO_PASSWORD)),
        ]
        session.add_all(users)

        agents = [
            Agent(tenant_id=tenant.id, name="Document Intelligence", type="document_intelligence",
                  area="general", system_prompt="Analiza documentos y responde con citas.",
                  tools="rag,export", privacy_mode="auto"),
            Agent(tenant_id=tenant.id, name="Cyber Diagnostic Agent", type="cyber_diagnostic",
                  area="ciberseguridad", system_prompt="Evalúa riesgos y controles de ciberseguridad.",
                  tools="rag,scoring", privacy_mode="no_external"),
            Agent(tenant_id=tenant.id, name="Proposal / SOW Agent", type="proposal_sow",
                  area="ventas", system_prompt="Genera SOWs y propuestas comerciales.",
                  tools="rag,export", privacy_mode="auto", requires_premium_reasoning=True),
            Agent(tenant_id=tenant.id, name="Executive Copilot", type="executive_copilot",
                  area="finanzas", system_prompt="Síntesis ejecutiva y razonamiento estratégico.",
                  tools="rag", privacy_mode="auto", requires_premium_reasoning=True),
        ]
        session.add_all(agents)
        session.commit()

        # Seed the default document-category catalog so the repository is ready to
        # organize uploads by type. We intentionally do NOT seed sample documents
        # anymore — they polluted the RAG index (showing up as chat sources) and
        # users couldn't tell them apart from real company files.
        from . import doc_categories
        doc_categories.ensure_defaults(session, tenant.id)


def ensure_super_admin() -> None:
    """Guarantee a super admin exists (idempotent). If none, promote the oldest
    admin so the platform owner can see and govern everything across tenants."""
    from .models import Role

    with Session(engine) as session:
        if session.exec(select(User).where(User.role == Role.SUPER_ADMIN)).first():
            return
        admin = session.exec(
            select(User).where(User.role == Role.ADMIN).order_by(User.created_at)
        ).first()
        if admin:
            admin.role = Role.SUPER_ADMIN
            session.add(admin)
            session.commit()


if __name__ == "__main__":
    from .db import init_db

    init_db()
    seed()
    print("Seed complete. Login: admin@maestroai.mx / demo1234")
