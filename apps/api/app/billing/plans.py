"""Recommended licensing scheme + indicative pricing (MXN).

Model: the platform is sold as a setup fee + an annual prepaid license per seat.
Pushing App Studio projects to production is charged separately (pay-to-prod).
Prices are industry-aligned ESTIMATES for the Mexican market and are meant to be
tuned per deal — they are data, not hard-coded business rules.
"""
from __future__ import annotations

CURRENCY = "MXN"

PLANS: list[dict] = [
    {
        "id": "emprende",
        "name": "Emprende",
        "audience": "Micronegocio / economía informal",
        "setup_fee": 0,
        "annual_per_seat": 1200,          # ~$100 MXN/mes por asiento
        "seats_range": "1–3",
        "min_seats": 1,
        "prod_deploy_price": 499,
        "includes": [
            "Casos de uso + pre-llenado por IA",
            "Alertas de ruta de privacidad",
            "Rutas local y abierto (volumen)",
            "RAG básico y auditoría",
        ],
        "recommended_for": ["comercio", "servicios", "freelance", "tianguis/abarrotes"],
    },
    {
        "id": "negocio",
        "name": "Negocio",
        "audience": "PyME",
        "setup_fee": 5000,
        "annual_per_seat": 3600,          # ~$300 MXN/mes por asiento
        "seats_range": "3–25",
        "min_seats": 3,
        "prod_deploy_price": 999,
        "includes": [
            "Todo lo de Emprende",
            "Workflows n8n gestionado (as-a-service)",
            "White-label (marca propia)",
            "Ruta VPC privada + cifrado en reposo",
            "Catálogo regional y curación de casos",
        ],
        "recommended_for": ["retail", "manufactura ligera", "despachos", "salud privada", "educación"],
    },
    {
        "id": "empresa",
        "name": "Empresa",
        "audience": "Corporativo / Enterprise",
        "setup_fee": 25000,
        "annual_per_seat": 7200,          # ~$600 MXN/mes por asiento (negociable)
        "seats_range": "25+",
        "min_seats": 25,
        "prod_deploy_price": 0,           # incluido / por volumen
        "includes": [
            "Todo lo de Negocio",
            "SSO/OIDC + MFA",
            "VPC dedicada y modelos premium",
            "BYO n8n y conectores propios",
            "Auditoría avanzada y SLA",
        ],
        "recommended_for": ["banca/seguros", "energía", "gobierno corporativo", "grandes cadenas"],
    },
    {
        "id": "gobierno",
        "name": "Gobierno / Sector público",
        "audience": "Dependencias y municipios",
        "setup_fee": None,                # por licitación / convenio
        "annual_per_seat": None,
        "seats_range": "Por proyecto",
        "min_seats": 0,
        "prod_deploy_price": None,
        "includes": [
            "Casos por ejes de desarrollo",
            "Catálogo de trámites por estado/municipio",
            "Despliegue en infraestructura del cliente",
            "Cumplimiento y residencia de datos en México",
        ],
        "recommended_for": ["municipios", "secretarías estatales", "programas sociales"],
    },
]


def estimate(plan_id: str, seats: int) -> dict | None:
    """First-year estimate = setup + (annual_per_seat * seats)."""
    plan = next((p for p in PLANS if p["id"] == plan_id), None)
    if not plan or plan["annual_per_seat"] is None:
        return None
    seats = max(seats, plan["min_seats"])
    annual = plan["annual_per_seat"] * seats
    setup = plan["setup_fee"] or 0
    return {
        "plan": plan_id, "seats": seats, "currency": CURRENCY,
        "setup_fee": setup, "annual_total": annual,
        "first_year_total": setup + annual,
        "monthly_equivalent": round(annual / 12),
    }
