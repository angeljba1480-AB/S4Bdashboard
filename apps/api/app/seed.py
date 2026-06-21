"""Seed demo data so the platform is usable immediately after `init_db`."""
from __future__ import annotations

from sqlmodel import Session, select

from .ai.rag import index_document
from .auth import hash_password
from .db import engine
from .models import Agent, Document, Role, Sensitivity, Tenant, User
from .security.classifier import classify_data

DEMO_PASSWORD = "demo1234"


def seed() -> None:
    with Session(engine) as session:
        if session.exec(select(Tenant)).first():
            return  # already seeded

        tenant = Tenant(name="Silent4Business", plan="enterprise", region="mx-central")
        session.add(tenant)
        session.commit()
        session.refresh(tenant)

        users = [
            User(tenant_id=tenant.id, email="admin@s4b.mx", name="Layla Delgadillo",
                 role=Role.ADMIN, password_hash=hash_password(DEMO_PASSWORD), mfa_enabled=True),
            User(tenant_id=tenant.id, email="user@s4b.mx", name="Usuario Negocio",
                 role=Role.USER, password_hash=hash_password(DEMO_PASSWORD)),
            User(tenant_id=tenant.id, email="security@s4b.mx", name="Roberto Silva",
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

        owner = users[0]
        session.refresh(owner)
        sample_docs = [
            ("politica_seguridad.txt",
             "Política de seguridad de la información de uso interno. Define controles "
             "de acceso, respaldo y continuidad. Documento interno borrador."),
            ("contrato_bbva.txt",
             "Contrato confidencial de servicios administrados con BBVA México. "
             "Acuerdo de confidencialidad (NDA). Contacto: andres.romo@bbva.mx, "
             "RFC BBM930101XYZ. Montos y estados financieros restringidos."),
            ("comunicado_prensa.txt",
             "Comunicado público: Silent4Business anuncia nuevo centro de operaciones "
             "de seguridad para el mercado mexicano. Para marketing y prensa."),
        ]
        for filename, text in sample_docs:
            cls = classify_data(text)
            doc = Document(
                tenant_id=tenant.id, owner_id=owner.id, filename=filename,
                mime_type="text/plain", sensitivity=cls.sensitivity,
                pii_score=cls.pii.score, pii_types=",".join(cls.pii.types),
                text=text, storage_uri=f"local://{filename}",
            )
            session.add(doc)
            session.commit()
            session.refresh(doc)
            index_document(session, doc)


if __name__ == "__main__":
    from .db import init_db

    init_db()
    seed()
    print("Seed complete. Login: admin@s4b.mx / demo1234")
