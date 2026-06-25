"""Navigable flowcharts — the blueprint's 3 base flows (§3) encoded as data, plus
a generic "how a use case runs" flow. Served read-only so the frontend can render
them as step-through, clickable diagrams. Users can also build free ones client-side.

Node shape:
    {id, type, title, detail?, next?, branches?: [{label, to}]}
    type: start | step | decision | end | danger
A `step`/`start` node advances via `next`; a `decision` node via `branches`.
"""
from __future__ import annotations

FLOWCHARTS: list[dict] = [
    {
        "id": "arquitectura_segura",
        "title": "Arquitectura Segura para AI",
        "description": "Primero se clasifica la sensibilidad; luego se decide si el procesamiento es local, privado, anonimizado o externo.",
        "note": "Regla de oro: si no es indispensable enviar el dato, no se envía.",
        "start": "datos",
        "nodes": [
            {"id": "datos", "type": "start", "title": "Datos / Documentos",
             "detail": "PDFs, contratos, tickets, correos, CRM.", "next": "clasificar"},
            {"id": "clasificar", "type": "decision", "title": "Clasificar sensibilidad",
             "detail": "El clasificador decide la ruta de procesamiento.",
             "branches": [{"label": "Alta", "to": "alta"}, {"label": "Media", "to": "media"}, {"label": "Baja", "to": "baja"}]},
            {"id": "alta", "type": "danger", "title": "Alta sensibilidad → Local / Self-hosted",
             "detail": "PII, financiero, salud, secretos. Procesar local/VPC; RAG local o fine-tuning en entorno privado. Sin salida externa.", "next": "respuesta"},
            {"id": "media", "type": "step", "title": "Media → Anonimizar y minimizar",
             "detail": "Documentos internos. Anonimizar/minimizar; enviar solo lo mínimo necesario.", "next": "respuesta"},
            {"id": "baja", "type": "step", "title": "Baja → Proveedor externo permitido",
             "detail": "Contenido público. Se puede usar un proveedor externo.", "next": "respuesta"},
            {"id": "respuesta", "type": "step", "title": "Respuesta / Resultado",
             "detail": "Se entrega el resultado al usuario.", "next": "monitoreo"},
            {"id": "monitoreo", "type": "end", "title": "Monitoreo y auditoría",
             "detail": "Logs, alertas, revisiones, redacción de PII y trazabilidad de la decisión."},
        ],
    },
    {
        "id": "prompt_rag_finetuning",
        "title": "¿Prompt, RAG o Fine-Tuning?",
        "description": "Usar RAG para conocimiento cambiante; fine-tuning solo para comportamiento, formato o tareas repetitivas.",
        "note": "Si el proveedor necesita leer el contenido, no basta con cifrado: usa entorno privado o VPC.",
        "start": "objetivo",
        "nodes": [
            {"id": "objetivo", "type": "start", "title": "Objetivo de negocio",
             "detail": "¿Qué quieres mejorar? Calidad, costo, velocidad o privacidad.", "next": "cambia"},
            {"id": "cambia", "type": "decision", "title": "¿El conocimiento cambia seguido?",
             "branches": [{"label": "Sí", "to": "rag"}, {"label": "No", "to": "repetitivo"}]},
            {"id": "rag", "type": "step", "title": "Prefiere RAG (local)",
             "detail": "Manuales, contratos, políticas, bases de conocimiento.", "next": "sensible"},
            {"id": "repetitivo", "type": "decision", "title": "¿Comportamiento / formato / tarea repetitiva?",
             "branches": [{"label": "Sí", "to": "finetuning"}, {"label": "No", "to": "prompting"}]},
            {"id": "finetuning", "type": "step", "title": "Considera Fine-Tuning ligero",
             "detail": "LoRA / QLoRA para formato y comportamiento estables.", "next": "sensible"},
            {"id": "prompting", "type": "step", "title": "Prompting (sin fine-tuning)",
             "detail": "Plantillas, reglas y tools.", "next": "sensible"},
            {"id": "sensible", "type": "decision", "title": "¿Es dato altamente sensible?",
             "branches": [{"label": "Sí", "to": "privado"}, {"label": "No", "to": "externo"}]},
            {"id": "privado", "type": "danger", "title": "Entrena/procesa en entorno privado",
             "detail": "Self-hosted, VPC privada o modelo abierto en tu infraestructura.", "next": "evaluacion"},
            {"id": "externo", "type": "step", "title": "Puedes usar proveedor externo",
             "detail": "Con minimización y configuración de no-retención.", "next": "evaluacion"},
            {"id": "evaluacion", "type": "step", "title": "Evaluación obligatoria",
             "detail": "Accuracy, formato, latencia, costo, alucinación y seguridad.", "next": "produccion"},
            {"id": "produccion", "type": "end", "title": "Producción",
             "detail": "Monitoreo + versionado + rollback."},
        ],
    },
    {
        "id": "pipeline_finetuning",
        "title": "Pipeline Seguro de Fine-Tuning",
        "description": "Datasets versionados, anonimizados, cifrados y evaluados antes de producción.",
        "note": "Empieza con un caso pequeño (70–140 ejemplos) y evalúa antes de escalar.",
        "start": "definir",
        "nodes": [
            {"id": "definir", "type": "start", "title": "1. Definir caso de uso",
             "detail": "Clasificación, extracción, tono, SOW, diagnóstico.", "next": "inventario"},
            {"id": "inventario", "type": "step", "title": "2. Inventario y clasificación de datos",
             "detail": "Etiqueta alta / media / baja sensibilidad.", "next": "pii"},
            {"id": "pii", "type": "decision", "title": "3. ¿Hay PII / datos sensibles?",
             "branches": [{"label": "Sí", "to": "redactar"}, {"label": "No", "to": "dataset"}]},
            {"id": "redactar", "type": "danger", "title": "Redactar / anonimizar",
             "detail": "DLP masking, hashing, seudonimización.", "next": "dataset"},
            {"id": "dataset", "type": "step", "title": "4. Dataset versionado y cifrado",
             "detail": "JSONL, DVC/Git LFS, AES-256, KMS.", "next": "generar"},
            {"id": "generar", "type": "step", "title": "5. Generar datos",
             "detail": "Sintéticos opcionales; valida calidad antes de entrenar.", "next": "donde"},
            {"id": "donde", "type": "decision", "title": "6. ¿Dónde entrenar?",
             "branches": [{"label": "Local / Self-hosted", "to": "ligero"}, {"label": "VPC privada", "to": "ligero"}, {"label": "Proveedor abierto (riesgo bajo)", "to": "ligero"}]},
            {"id": "ligero", "type": "step", "title": "7. Fine-tuning ligero",
             "detail": "LoRA / QLoRA.", "next": "evaluacion"},
            {"id": "evaluacion", "type": "step", "title": "8. Evaluación / red team",
             "detail": "Sesgos, fuga de datos, calidad.", "next": "produccion"},
            {"id": "produccion", "type": "end", "title": "9. Producción + monitoreo continuo",
             "detail": "Controles: TLS, AES-256, RBAC+MFA, KMS, VPN, retención mínima, borrado seguro, aprobación legal/compliance."},
        ],
    },
    {
        "id": "caso_de_uso",
        "title": "Cómo funciona un caso de uso",
        "description": "El flujo estándar que sigue cualquier caso de uso de la plataforma: tú das lo mínimo y apruebas.",
        "note": "El contenido sensible se procesa de forma privada y todo queda auditado.",
        "start": "objetivo",
        "nodes": [
            {"id": "objetivo", "type": "start", "title": "Objetivo + notas",
             "detail": "Dices qué quieres lograr, notas y el formato de salida.", "next": "datos"},
            {"id": "datos", "type": "step", "title": "Datos mínimos del caso",
             "detail": "Solo los campos indispensables; el resto lo pone tu perfil de empresa.", "next": "clasifica"},
            {"id": "clasifica", "type": "decision", "title": "¿El contenido es sensible?",
             "detail": "Se clasifica la sensibilidad y se detecta PII.",
             "branches": [{"label": "Sí", "to": "privada"}, {"label": "No", "to": "abierta"}]},
            {"id": "privada", "type": "danger", "title": "Ruta privada",
             "detail": "Local / VPC; sin exponer el dato a terceros.", "next": "borrador"},
            {"id": "abierta", "type": "step", "title": "Ruta abierta / premium",
             "detail": "Modelo abierto o premium, con minimización.", "next": "borrador"},
            {"id": "borrador", "type": "step", "title": "Borrador con RAG de tu empresa",
             "detail": "Se apoya en tus documentos del área/categoría correspondiente.", "next": "aprueba"},
            {"id": "aprueba", "type": "decision", "title": "Revisas y apruebas",
             "branches": [{"label": "Aprobar", "to": "entregable"}, {"label": "Ajustar", "to": "objetivo"}]},
            {"id": "entregable", "type": "end", "title": "Entregable + auditoría",
             "detail": "Se genera en el formato elegido y queda registrado en la auditoría."},
        ],
    },
]

_BY_ID = {f["id"]: f for f in FLOWCHARTS}


def list_flowcharts() -> list[dict]:
    return [{"id": f["id"], "title": f["title"], "description": f["description"]} for f in FLOWCHARTS]


def get_flowchart(flow_id: str) -> dict | None:
    return _BY_ID.get(flow_id)
