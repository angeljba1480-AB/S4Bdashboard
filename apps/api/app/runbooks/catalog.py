"""Catálogo (semilla, en código) de **runbooks**: automatizaciones multi-paso por
**segmento** (PyME / Enterprise) y **sector**, desde áreas de servicio hasta planta de
producción. Un runbook se "instala" como un *playbook del agente* (instrucción en lenguaje
natural, posiblemente encadenada con {{stepN}}) que el agente ejecuta a demanda usando el
toolkit (correo, hojas, Teams, documentos) y los workflows. Agregar un runbook es **datos**.
"""
from __future__ import annotations

# Facetas para la UI.
SEGMENTS = [
    {"key": "pyme", "label": "PyME"},
    {"key": "enterprise", "label": "Enterprise"},
]
SECTORS = [
    {"key": "servicios", "label": "Servicios / Atención"},
    {"key": "manufactura", "label": "Manufactura / Producción"},
    {"key": "retail", "label": "Retail / Comercio"},
    {"key": "logistica", "label": "Logística / Distribución"},
]
_SEG_KEYS = {s["key"] for s in SEGMENTS}
_SEC_KEYS = {s["key"] for s in SECTORS}


def _rb(**kw) -> dict:
    kw.setdefault("segment", "ambos")   # pyme | enterprise | ambos
    kw.setdefault("icon", "workflow")
    kw.setdefault("benefit", "")
    return kw


# --- Catálogo ---------------------------------------------------------------
RUNBOOKS: list[dict] = [
    # ===== Servicios / Atención =====
    _rb(
        id="triage_tickets", sector="servicios", area="Atención a cliente", segment="pyme",
        title="Triage de tickets de soporte",
        description="Clasifica los tickets nuevos por urgencia y tema y propone una respuesta para cada uno.",
        benefit="Responde más rápido y prioriza lo crítico sin revisar uno por uno.",
        steps=[
            "Lee los tickets nuevos de la fuente de soporte (hoja de cálculo o bandeja de entrada).",
            "Clasifica cada ticket por urgencia (alta/media/baja) y por tema.",
            "Redacta una respuesta sugerida para cada ticket usando el contexto de la empresa.",
            "Entrega un resumen priorizado con la respuesta propuesta de cada ticket.",
        ],
    ),
    _rb(
        id="sla_watch", sector="servicios", area="Atención a cliente", segment="enterprise",
        title="Vigilancia de SLA",
        description="Detecta tickets por incumplir el SLA y avisa a los responsables.",
        benefit="Evita penalizaciones por SLA avisando antes de que se venzan.",
        steps=[
            "Lee los tickets abiertos con su hora de creación y prioridad.",
            "Identifica los que están por incumplir el SLA según su prioridad.",
            "Arma la lista de tickets en riesgo con su responsable.",
            "Notifica a cada responsable por Teams o correo usando {{step3}}.",
        ],
    ),
    _rb(
        id="csat_encuesta", sector="servicios", area="Atención a cliente",
        title="Encuesta de satisfacción (CSAT)",
        description="Envía una encuesta a los clientes con servicios cerrados hoy.",
        benefit="Mide satisfacción de forma automática y constante.",
        steps=[
            "Lee los servicios/tickets cerrados de hoy con el correo del cliente.",
            "Redacta un correo breve de encuesta de satisfacción (escala 1-5 + comentario).",
            "Envía la encuesta por correo a cada cliente de {{step1}}.",
        ],
    ),
    _rb(
        id="cotiza_seguimiento", sector="servicios", area="Ventas", segment="pyme",
        title="Cotización y seguimiento",
        description="Genera la cotización a partir de la solicitud, la envía y agenda seguimiento.",
        benefit="Cierra más ventas: cotiza al momento y no se te olvida dar seguimiento.",
        steps=[
            "Toma la solicitud del cliente (producto/servicio, cantidad, datos de contacto).",
            "Genera una cotización con precios y condiciones de la empresa.",
            "Envía la cotización por correo al cliente usando {{step2}}.",
            "Agenda un recordatorio de seguimiento a 3 días en el calendario.",
        ],
    ),
    _rb(
        id="cobranza_vencidas", sector="servicios", area="Finanzas",
        title="Cobranza de facturas vencidas",
        description="Identifica facturas vencidas y envía recordatorios de pago corteses.",
        benefit="Recupera cartera vencida sin perseguir manualmente a cada cliente.",
        steps=[
            "Lee la hoja de cuentas por cobrar (cliente, monto, vencimiento, correo).",
            "Identifica las facturas vencidas y agrúpalas por cliente.",
            "Redacta un recordatorio de pago cortés con el detalle de cada factura.",
            "Envía el recordatorio por correo a cada cliente de {{step2}}.",
        ],
    ),
    _rb(
        id="onboarding_empleado", sector="servicios", area="Recursos Humanos",
        title="Onboarding de nuevo empleado",
        description="Arma el checklist de alta, solicita accesos y agenda la inducción.",
        benefit="Estandariza la incorporación y no se olvida ningún paso.",
        steps=[
            "Toma los datos del nuevo empleado (nombre, puesto, área, fecha de ingreso).",
            "Genera el checklist de alta (equipo, accesos, documentos) para su puesto.",
            "Crea un documento con el plan de inducción de su primera semana.",
            "Agenda la sesión de inducción y notifica a su responsable por correo/Teams.",
        ],
    ),

    # ===== Manufactura / Producción =====
    _rb(
        id="orden_trabajo", sector="manufactura", area="Producción", segment="pyme",
        title="Orden de trabajo de producción",
        description="Genera la orden de trabajo con materiales y avisa a planta.",
        benefit="Convierte un pedido en orden de producción lista para piso.",
        steps=[
            "Toma el pedido (producto, cantidad, fecha requerida).",
            "Genera la orden de trabajo con la lista de materiales y cantidades.",
            "Crea el documento de la orden de trabajo.",
            "Notifica a planta/supervisión la nueva orden por Teams o correo.",
        ],
    ),
    _rb(
        id="paros_oee", sector="manufactura", area="Producción", segment="enterprise",
        title="Reporte de paros y OEE del turno",
        description="Calcula disponibilidad/OEE a partir del registro de paros y lo publica.",
        benefit="Visibilidad de eficiencia de planta por turno, sin armar el reporte a mano.",
        steps=[
            "Lee el registro de paros de las líneas del turno (línea, causa, duración).",
            "Calcula el tiempo perdido por línea y la disponibilidad/OEE del turno.",
            "Redacta un resumen con las principales causas de paro y el OEE.",
            "Publica el resumen a supervisión por Teams usando {{step3}}.",
        ],
    ),
    _rb(
        id="mantenimiento_preventivo", sector="manufactura", area="Mantenimiento",
        title="Mantenimiento preventivo de la semana",
        description="Genera las órdenes de los equipos que toca mantener y avisa a técnicos.",
        benefit="Cumple el plan de mantenimiento y reduce fallas no planeadas.",
        steps=[
            "Lee el calendario de mantenimiento y filtra los equipos que tocan esta semana.",
            "Genera una orden de mantenimiento por equipo con sus tareas.",
            "Asigna y notifica a los técnicos responsables por correo/Teams.",
        ],
    ),
    _rb(
        id="no_conformidades", sector="manufactura", area="Calidad", segment="enterprise",
        title="No conformidades de calidad",
        description="Clasifica las no conformidades y arma el reporte 8D inicial.",
        benefit="Acelera la respuesta a calidad y deja trazabilidad.",
        steps=[
            "Lee las no conformidades registradas (producto, defecto, lote).",
            "Clasifícalas por severidad y recurrencia.",
            "Genera el reporte 8D inicial (D1-D3) para las críticas.",
            "Notifica al equipo de calidad las no conformidades críticas por correo.",
        ],
    ),
    _rb(
        id="reorden_inventario", sector="manufactura", area="Almacén",
        title="Reorden de inventario / almacén",
        description="Detecta materiales bajo el punto de reorden y genera la requisición.",
        benefit="Evita paros por falta de material anticipando las compras.",
        steps=[
            "Lee el inventario de materiales (material, existencia, punto de reorden).",
            "Detecta los materiales por debajo del punto de reorden.",
            "Genera una requisición de compra con las cantidades sugeridas.",
            "Notifica a compras la requisición usando {{step3}}.",
        ],
    ),
    _rb(
        id="requisicion_proveedores", sector="manufactura", area="Compras", segment="pyme",
        title="Solicitud de cotización a proveedores",
        description="Convierte una requisición aprobada en solicitudes a proveedores.",
        benefit="Compra mejor: cotiza con varios proveedores en un clic.",
        steps=[
            "Toma la requisición aprobada (materiales y cantidades).",
            "Arma la solicitud de cotización con el detalle requerido.",
            "Envía la solicitud por correo a los proveedores y agenda el seguimiento.",
        ],
    ),

    # ===== Retail / Comercio =====
    _rb(
        id="corte_caja", sector="retail", area="Operaciones", segment="pyme",
        title="Corte de caja diario",
        description="Resume ventas del día, detecta diferencias y avisa al encargado.",
        benefit="Cierra el día cuadrado y con un reporte claro.",
        steps=[
            "Lee las ventas y movimientos de caja del día.",
            "Calcula el total esperado y compáralo con el efectivo reportado.",
            "Genera el corte de caja con diferencias señaladas y notifica al encargado.",
        ],
    ),
    _rb(
        id="reorden_pos", sector="retail", area="Inventario",
        title="Reorden por punto de venta",
        description="Detecta productos por agotarse y genera el pedido de resurtido.",
        benefit="Evita quiebres de stock en el punto de venta.",
        steps=[
            "Lee el inventario por tienda/producto y su nivel mínimo.",
            "Detecta los productos por debajo del mínimo.",
            "Genera el pedido de resurtido por tienda y notifícalo a compras.",
        ],
    ),

    # ===== Logística / Distribución =====
    _rb(
        id="evidencia_entrega", sector="logistica", area="Distribución",
        title="Evidencia de entrega e incidencias",
        description="Consolida entregas del día, marca incidencias y notifica a clientes.",
        benefit="Cierra la operación del día con trazabilidad y avisa a tiempo.",
        steps=[
            "Lee las entregas del día con su estatus y evidencia.",
            "Identifica las incidencias (no entregado, daño, retraso).",
            "Genera el reporte de entregas e incidencias del día.",
            "Notifica a los clientes afectados por correo usando {{step2}}.",
        ],
    ),
]


def _matches_segment(rb: dict, segment: str) -> bool:
    return rb.get("segment", "ambos") in ("ambos", segment)


def list_runbooks(segment: str = "", sector: str = "", q: str = "") -> list[dict]:
    out = []
    ql = (q or "").strip().lower()
    for rb in RUNBOOKS:
        if segment and not _matches_segment(rb, segment):
            continue
        if sector and rb.get("sector") != sector:
            continue
        if ql and ql not in (rb["title"] + " " + rb["description"] + " " + rb.get("area", "")).lower():
            continue
        out.append(rb)
    return out


def get_runbook(rb_id: str) -> dict | None:
    return next((rb for rb in RUNBOOKS if rb["id"] == rb_id), None)


def build_instruction(rb: dict) -> str:
    """Convierte los pasos del runbook en la instrucción del playbook del agente."""
    lines = [f"Runbook «{rb['title']}» ({rb.get('area', '')}). Ejecuta estos pasos en orden, "
             "encadenando el resultado de un paso al siguiente con {{stepN}} cuando aplique:"]
    for i, step in enumerate(rb.get("steps", []), start=1):
        lines.append(f"{i}. {step}")
    return "\n".join(lines)


def facets() -> dict:
    """Conteo de runbooks por sector y por segmento (para la UI)."""
    by_sector: dict[str, int] = {}
    for rb in RUNBOOKS:
        by_sector[rb["sector"]] = by_sector.get(rb["sector"], 0) + 1
    return {
        "segments": SEGMENTS,
        "sectors": [{**s, "count": by_sector.get(s["key"], 0)} for s in SECTORS],
        "total": len(RUNBOOKS),
    }
