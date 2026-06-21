"""Ready-made automation templates (data-driven, expandable).

Each template wires a trigger to an action. Users create an automation from a
template in one click; schedules/events run via the workflows layer, and
"run now" executes immediately.
"""
from __future__ import annotations

TEMPLATES: list[dict] = [
    {
        "id": "resumen_diario",
        "name": "Resumen diario de correo y agenda",
        "description": "Cada mañana genera un resumen de tu bandeja y tu agenda.",
        "icon": "mail",
        "trigger": "schedule", "schedule": "daily", "event": "",
        "action_type": "recipe", "action_ref": "correo_agenda",
        "config": {"output": "Resumen diario"},
    },
    {
        "id": "cobranza_semanal",
        "name": "Cobranza semanal a clientes",
        "description": "Cada semana prepara recordatorios de cobro pendientes.",
        "icon": "coins",
        "trigger": "schedule", "schedule": "weekly", "event": "",
        "action_type": "recipe", "action_ref": "recordatorio_cobranza",
        "config": {},
    },
    {
        "id": "redes_semanal",
        "name": "Publicación semanal en redes",
        "description": "Genera una publicación para promocionar tu negocio cada semana.",
        "icon": "megaphone",
        "trigger": "schedule", "schedule": "weekly", "event": "",
        "action_type": "recipe", "action_ref": "post_redes",
        "config": {},
    },
    {
        "id": "reporte_operacion",
        "name": "Reporte de operación diario",
        "description": "Compila un reporte de mando con la operación del día.",
        "icon": "activity",
        "trigger": "schedule", "schedule": "daily", "event": "",
        "action_type": "workflow", "action_ref": "mando",
        "config": {},
    },
    {
        "id": "alerta_doc_sensible",
        "name": "Alerta de documento sensible",
        "description": "Avisa cuando se suba un documento confidencial o con PII.",
        "icon": "shield-alert",
        "trigger": "event", "schedule": "", "event": "document_uploaded",
        "action_type": "notify", "action_ref": "",
        "config": {"message": "Se subió un documento sensible; revísalo en Auditoría."},
    },
    {
        "id": "indexar_nuevos_docs",
        "name": "Indexar nuevos documentos (RAG)",
        "description": "Indexa automáticamente los documentos nuevos para búsqueda.",
        "icon": "file-text",
        "trigger": "event", "schedule": "", "event": "document_uploaded",
        "action_type": "workflow", "action_ref": "ingesta",
        "config": {},
    },
]


def get_template(tid: str) -> dict | None:
    return next((t for t in TEMPLATES if t["id"] == tid), None)
