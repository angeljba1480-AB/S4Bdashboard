"""Industry report templates: ordered sections that shape a professional report.

A recipe ('Reporte por industria') injects the chosen template's sections into the
prompt so the AI produces a structured, industry-appropriate deliverable that can
then be exported to PDF/DOCX/PPTX/XLSX.
"""
from __future__ import annotations

_BASE = [
    "Resumen ejecutivo",
    "Contexto y objetivo",
    "Hallazgos clave",
    "Análisis",
    "Recomendaciones",
    "Próximos pasos",
    "Riesgos y mitigaciones",
]

# key -> {label, industry, sections}
TEMPLATES: dict[str, dict] = {
    "generico": {"label": "General / ejecutivo", "sections": _BASE},
    "retail": {"label": "Retail / comercio", "sections": [
        "Resumen ejecutivo", "Desempeño de ventas", "Análisis por categoría y tienda",
        "Inventario y rotación", "Comportamiento del cliente", "Recomendaciones comerciales",
        "Plan de acción y metas"]},
    "fintech": {"label": "Fintech / servicios financieros", "sections": [
        "Resumen ejecutivo", "Indicadores financieros (KPIs)", "Riesgo y cumplimiento",
        "Crecimiento y adquisición", "Unit economics", "Recomendaciones", "Riesgos regulatorios"]},
    "manufactura": {"label": "Manufactura / industria", "sections": [
        "Resumen ejecutivo", "Producción y OEE", "Calidad y mermas", "Cadena de suministro",
        "Seguridad y mantenimiento", "Recomendaciones", "Plan de mejora continua"]},
    "salud": {"label": "Salud", "sections": [
        "Resumen ejecutivo", "Indicadores clínicos y operativos", "Calidad y seguridad del paciente",
        "Cumplimiento normativo", "Eficiencia de recursos", "Recomendaciones", "Riesgos y mitigaciones"]},
    "gobierno": {"label": "Gobierno / sector público", "sections": [
        "Resumen ejecutivo", "Contexto y marco normativo", "Indicadores del programa",
        "Transparencia y rendición de cuentas", "Impacto ciudadano", "Recomendaciones", "Próximos pasos"]},
    "tecnologia": {"label": "Tecnología / SaaS", "sections": [
        "Resumen ejecutivo", "Métricas de producto (MRR, churn, NPS)", "Adopción y uso",
        "Roadmap y entregas", "Confiabilidad y seguridad", "Recomendaciones", "Riesgos técnicos"]},
    "servicios": {"label": "Servicios profesionales", "sections": [
        "Resumen ejecutivo", "Pipeline y propuestas", "Entregables y utilización",
        "Satisfacción del cliente", "Rentabilidad por proyecto", "Recomendaciones", "Próximos pasos"]},
}


def list_templates() -> list[dict]:
    return [{"key": k, "label": v["label"], "sections": v["sections"]} for k, v in TEMPLATES.items()]


def template_labels() -> list[str]:
    return [v["label"] for v in TEMPLATES.values()]


def get_by_key_or_label(value: str) -> dict | None:
    raw = (value or "").strip().lower()
    if not raw:
        return None
    for k, v in TEMPLATES.items():
        if k == raw or v["label"].lower() == raw:
            return {"key": k, **v}
    return None
