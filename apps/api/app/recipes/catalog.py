"""Use-case recipes ("Casos de uso") — a data-driven, scalable catalog.

Goal: thousands of use cases for businesses of every size (including the
informal economy), grouped by category. Adding a use case is *data*, not code:
a declarative recipe (inputs + optional connections + a prompt) runs through the
generic AI pre-fill. A few high-value cases keep custom handlers.

The non-technical user picks a case, gives the minimum, the platform pre-fills
and executes, and the user only approves (an action or a connection).
"""
from __future__ import annotations

from sqlmodel import Session

from ..ai.cost import estimate_cost, estimate_tokens
from ..ai.rag import retrieve
from ..ai.resilience import generate_with_fallback
from ..ai.router import route_request
from ..models import ModelRoute, Tenant

# --- Categories -------------------------------------------------------------
CATEGORIES: list[dict] = [
    {"id": "crecer", "label": "Crecer el negocio"},
    {"id": "abrir", "label": "Abrir / lanzar"},
    {"id": "cumplimiento", "label": "Cumplimiento (CEP / legal)"},
    {"id": "operaciones", "label": "Operaciones"},
    {"id": "dia_a_dia", "label": "Día a día"},
]

# Mexican states — used by region-aware recipes (trámites/impuestos vary by
# estado and municipio).
ESTADOS_MX = [
    "Aguascalientes", "Baja California", "Baja California Sur", "Campeche",
    "Chiapas", "Chihuahua", "Ciudad de México", "Coahuila", "Colima", "Durango",
    "Estado de México", "Guanajuato", "Guerrero", "Hidalgo", "Jalisco",
    "Michoacán", "Morelos", "Nayarit", "Nuevo León", "Oaxaca", "Puebla",
    "Querétaro", "Quintana Roo", "San Luis Potosí", "Sinaloa", "Sonora",
    "Tabasco", "Tamaulipas", "Tlaxcala", "Veracruz", "Yucatán", "Zacatecas",
]


def _estado_input() -> dict:
    # Generic, country-aware region field (localized per tenant country at API time).
    return {"key": "region", "type": "region", "label": "Estado/Provincia/Región", "required": True}


def _municipio_input() -> dict:
    return {"key": "municipio", "type": "text", "label": "Municipio / localidad", "required": True}


_REGION_DISCLAIMER = ("⚠️ Los requisitos, costos y plazos cambian por región y localidad (y por país). "
                      "Esto es una guía; confirma siempre con tu autoridad local.")


def _r(**kw) -> dict:
    """Recipe with sensible defaults so the catalog stays terse and scalable."""
    kw.setdefault("icon", "sparkles")
    kw.setdefault("connections", [])
    kw.setdefault("approval", "draft")
    kw.setdefault("approve_label", "Aprobar y generar")
    kw.setdefault("handler", "generic")
    kw.setdefault("produces", "el resultado")
    kw.setdefault("prompt", "")
    return kw


# --- Catalog (curated seed; grows over time + with user proposals) ----------
RECIPES: list[dict] = [
    # ---- Custom-handler, high-value cases ---------------------------------
    _r(
        id="licitacion", category="crecer", handler="licitacion", icon="file-check",
        name="Revisar licitación y pre-llenar respuesta",
        description="Sube la licitación; extraigo los requisitos y pre-lleno tu respuesta. Tú apruebas.",
        inputs=[
            {"key": "document_id", "type": "document", "label": "Documento de la licitación", "required": True},
            {"key": "empresa", "type": "text", "label": "Nombre de tu empresa", "required": True},
        ],
        approval="draft", approve_label="Aprobar respuesta pre-llenada",
        produces="una respuesta de licitación pre-llenada",
    ),
    _r(
        id="correo_agenda", category="dia_a_dia", handler="correo_agenda", icon="mail",
        name="Resumen de correo y agenda",
        description="Pon tu correo y elige el resumen; lo genero solo. Tú apruebas la conexión.",
        inputs=[
            {"key": "email", "type": "email", "label": "Tu correo", "required": True},
            {"key": "output", "type": "choice", "label": "Tipo de salida",
             "options": ["Resumen diario", "Horario del día", "Pendientes por responder"], "required": True},
        ],
        connections=[{"provider": "email", "label": "Correo"}, {"provider": "calendar", "label": "Calendario"}],
        approval="connection", approve_label="Aprobar conexión y ejecutar",
        produces="un resumen de tu correo y agenda",
    ),

    # ---- Crecer el negocio ------------------------------------------------
    _r(id="propuesta_comercial", category="crecer", name="Propuesta comercial",
       description="Genero una propuesta lista para enviar a tu cliente.",
       inputs=[{"key": "cliente", "type": "text", "label": "Cliente", "required": True},
               {"key": "servicio", "type": "text", "label": "Producto o servicio", "required": True},
               {"key": "precio", "type": "text", "label": "Precio (aprox.)"}],
       produces="una propuesta comercial",
       prompt="Propuesta comercial para {cliente} sobre {servicio} (precio: {precio})."),
    _r(id="post_redes", category="crecer", name="Publicación para redes sociales",
       description="Creo el texto y hashtags para promocionar tu negocio.",
       inputs=[{"key": "negocio", "type": "text", "label": "Tu negocio", "required": True},
               {"key": "promo", "type": "text", "label": "Qué quieres promocionar", "required": True}],
       produces="una publicación para redes",
       prompt="Publicación atractiva para {negocio} promocionando {promo}."),

    # ---- Abrir / lanzar ---------------------------------------------------
    _r(id="plan_negocio", category="abrir", name="Plan de negocio express",
       description="Bosquejo un plan simple para arrancar tu idea.",
       inputs=[{"key": "idea", "type": "text", "label": "Tu idea de negocio", "required": True},
               {"key": "ciudad", "type": "text", "label": "Ciudad / zona"}],
       produces="un plan de negocio express",
       prompt="Plan de negocio express para: {idea} en {ciudad}."),
    _r(id="registro_tramites", category="abrir", name="Checklist de trámites para abrir",
       description="Lista de pasos y trámites para formalizar tu negocio.",
       inputs=[{"key": "giro", "type": "text", "label": "Giro del negocio", "required": True},
               {"key": "ciudad", "type": "text", "label": "Ciudad / estado"}],
       produces="un checklist de trámites",
       prompt="Checklist de trámites para abrir un negocio de {giro} en {ciudad}."),

    # ---- Cumplimiento (CEP / legal) ---------------------------------------
    _r(id="aviso_privacidad", category="cumplimiento", name="Aviso de privacidad",
       description="Genero un aviso de privacidad base para tu negocio.",
       inputs=[{"key": "empresa", "type": "text", "label": "Nombre del negocio", "required": True},
               {"key": "datos", "type": "text", "label": "Datos que recolectas"}],
       produces="un aviso de privacidad",
       prompt="Aviso de privacidad para {empresa} que recolecta {datos}."),
    _r(id="contrato_simple", category="cumplimiento", name="Contrato sencillo",
       description="Borrador de contrato de prestación de servicios.",
       inputs=[{"key": "parte_a", "type": "text", "label": "Tú / tu empresa", "required": True},
               {"key": "parte_b", "type": "text", "label": "Cliente", "required": True},
               {"key": "objeto", "type": "text", "label": "Objeto del contrato", "required": True}],
       produces="un contrato sencillo",
       prompt="Contrato de servicios entre {parte_a} y {parte_b} por {objeto}."),

    # ---- Operaciones ------------------------------------------------------
    _r(id="cotizacion", category="operaciones", name="Cotización rápida",
       description="Armo una cotización lista para mandar (ideal por WhatsApp).",
       inputs=[{"key": "cliente", "type": "text", "label": "Cliente", "required": True},
               {"key": "concepto", "type": "text", "label": "Concepto", "required": True},
               {"key": "monto", "type": "text", "label": "Monto"}],
       produces="una cotización",
       prompt="Cotización para {cliente}: {concepto} por {monto}."),
    _r(id="inventario_alerta", category="operaciones", name="Control de inventario",
       description="Registro y alerta de productos por agotarse.",
       inputs=[{"key": "productos", "type": "text", "label": "Productos y cantidades", "required": True}],
       produces="un control de inventario con alertas",
       prompt="Control de inventario y alertas de stock bajo para: {productos}."),

    # ---- Día a día (incluye economía informal) ----------------------------
    _r(id="precio_venta", category="dia_a_dia", name="Calcular precio de venta",
       description="Te digo a cuánto vender según tu costo y ganancia deseada.",
       inputs=[{"key": "costo", "type": "text", "label": "Costo del producto", "required": True},
               {"key": "ganancia", "type": "text", "label": "Ganancia que quieres (%)"}],
       produces="tu precio de venta sugerido",
       prompt="Calcula precio de venta con costo {costo} y ganancia {ganancia}%."),
    _r(id="corte_caja", category="dia_a_dia", name="Corte de caja del día",
       description="Resumo tus ventas y gastos del día.",
       inputs=[{"key": "ventas", "type": "text", "label": "Ventas del día", "required": True},
               {"key": "gastos", "type": "text", "label": "Gastos del día"}],
       produces="tu corte de caja",
       prompt="Corte de caja: ventas {ventas}, gastos {gastos}."),

    # ===== Más casos sembrados =====
    # ---- Crecer el negocio ----
    _r(id="guion_ventas", category="crecer", name="Guion de ventas",
       description="Un guion para vender por teléfono o en persona.",
       inputs=[{"key": "producto", "type": "text", "label": "Producto/servicio", "required": True},
               {"key": "cliente_tipo", "type": "text", "label": "Tipo de cliente"}],
       produces="un guion de ventas",
       prompt="Guion de ventas para vender {producto} a {cliente_tipo}."),
    _r(id="correo_frio", category="crecer", name="Correo de prospección",
       description="Correo en frío para conseguir una reunión.",
       inputs=[{"key": "prospecto", "type": "text", "label": "Empresa/persona objetivo", "required": True},
               {"key": "oferta", "type": "text", "label": "Qué ofreces", "required": True}],
       produces="un correo de prospección",
       prompt="Correo en frío a {prospecto} ofreciendo {oferta}, con llamada a la acción para reunión."),
    _r(id="promo_temporada", category="crecer", name="Promoción de temporada",
       description="Idea y texto de una promoción para fechas clave.",
       inputs=[{"key": "negocio", "type": "text", "label": "Tu negocio", "required": True},
               {"key": "fecha", "type": "text", "label": "Temporada/fecha (ej. Buen Fin)"}],
       produces="una promoción de temporada",
       prompt="Promoción para {negocio} en {fecha} con mensaje y mecánica."),

    # ---- Abrir / lanzar (REGIÓN) ----
    _r(id="licencia_funcionamiento", category="abrir", name="Licencia de funcionamiento",
       description="Requisitos y pasos para tu licencia municipal (varía por municipio).",
       inputs=[{"key": "giro", "type": "text", "label": "Giro del negocio", "required": True},
               _estado_input(), _municipio_input()],
       produces="la guía de licencia de funcionamiento",
       prompt="Requisitos y pasos de la licencia de funcionamiento para un negocio de {giro} en {municipio}, {region}."),
    _r(id="uso_de_suelo", category="abrir", name="Constancia de uso de suelo",
       description="Cómo tramitar el uso de suelo para tu local (por municipio).",
       inputs=[{"key": "actividad", "type": "text", "label": "Actividad/uso", "required": True},
               _estado_input(), _municipio_input()],
       produces="la guía de uso de suelo",
       prompt="Pasos para la constancia de uso de suelo para {actividad} en {municipio}, {region}."),
    _r(id="permiso_anuncio", category="abrir", name="Permiso de anuncio / letrero",
       description="Trámite del permiso para tu anuncio exterior (municipal).",
       inputs=[{"key": "tipo_anuncio", "type": "text", "label": "Tipo de anuncio", "required": True},
               _estado_input(), _municipio_input()],
       produces="la guía del permiso de anuncio",
       prompt="Requisitos del permiso de anuncio tipo {tipo_anuncio} en {municipio}, {region}."),
    _r(id="nombre_negocio", category="abrir", name="Ideas de nombre + disponibilidad",
       description="Propongo nombres para tu negocio y qué revisar antes de usarlo.",
       inputs=[{"key": "giro", "type": "text", "label": "Giro/idea", "required": True}],
       produces="ideas de nombre",
       prompt="Propón 8 nombres para un negocio de {giro} y cómo verificar disponibilidad (IMPI/dominio/redes)."),

    # ---- Cumplimiento (CEP / legal) (varios con REGIÓN) ----
    _r(id="rfc_alta", category="cumplimiento", name="Alta en el RFC (guía)",
       description="Pasos para darte de alta en el SAT según tu actividad.",
       inputs=[{"key": "actividad", "type": "text", "label": "Tu actividad", "required": True},
               {"key": "regimen", "type": "text", "label": "Régimen (si lo sabes, ej. RESICO)"}],
       produces="la guía de alta en el RFC",
       prompt="Guía para darse de alta en el RFC ante el SAT para {actividad} (régimen {regimen})."),
    _r(id="impuestos_locales", category="cumplimiento", name="Impuestos locales del negocio",
       description="Qué impuestos estatales/municipales aplican a tu negocio.",
       inputs=[{"key": "giro", "type": "text", "label": "Giro del negocio", "required": True},
               _estado_input(), _municipio_input()],
       produces="un resumen de impuestos locales",
       prompt="Impuestos estatales y municipales que aplican a un negocio de {giro} en {municipio}, {region}."),
    _r(id="reglamento_local", category="cumplimiento", name="Reglas para tu giro (local)",
       description="Reglamentos municipales aplicables a tu actividad.",
       inputs=[{"key": "giro", "type": "text", "label": "Giro/actividad", "required": True},
               _estado_input(), _municipio_input()],
       produces="un resumen de reglamentos locales",
       prompt="Reglamentos municipales aplicables a {giro} en {municipio}, {region} (verificación, horarios, sanidad)."),
    _r(id="politica_devoluciones", category="cumplimiento", name="Política de devoluciones",
       description="Texto de política de devoluciones y garantías para tu negocio.",
       inputs=[{"key": "negocio", "type": "text", "label": "Tu negocio", "required": True},
               {"key": "productos", "type": "text", "label": "Qué vendes"}],
       produces="una política de devoluciones",
       prompt="Política de devoluciones y garantías para {negocio} que vende {productos}, acorde a PROFECO."),

    # ---- Operaciones ----
    _r(id="orden_compra", category="operaciones", name="Orden de compra a proveedor",
       description="Genero una orden de compra lista para enviar.",
       inputs=[{"key": "proveedor", "type": "text", "label": "Proveedor", "required": True},
               {"key": "articulos", "type": "text", "label": "Artículos y cantidades", "required": True}],
       produces="una orden de compra",
       prompt="Orden de compra a {proveedor} por {articulos}."),
    _r(id="recordatorio_cobranza", category="operaciones", name="Recordatorio de cobranza",
       description="Mensaje amable para cobrar a un cliente.",
       inputs=[{"key": "cliente", "type": "text", "label": "Cliente", "required": True},
               {"key": "monto", "type": "text", "label": "Monto/adeudo", "required": True}],
       produces="un recordatorio de cobranza",
       prompt="Mensaje cordial de cobranza a {cliente} por {monto}, con opciones de pago."),
    _r(id="horario_turnos", category="operaciones", name="Rol de turnos del personal",
       description="Arma un rol de turnos simple para tu equipo.",
       inputs=[{"key": "personas", "type": "text", "label": "Personas y disponibilidad", "required": True},
               {"key": "horario", "type": "text", "label": "Horario del negocio"}],
       produces="un rol de turnos",
       prompt="Rol de turnos para {personas} con horario {horario}."),

    # ---- Día a día (incluye economía informal) ----
    _r(id="carta_precios", category="dia_a_dia", name="Carta / lista de precios",
       description="Arma una lista de precios presentable para mostrar o imprimir.",
       inputs=[{"key": "productos", "type": "text", "label": "Productos y precios", "required": True},
               {"key": "negocio", "type": "text", "label": "Nombre del negocio"}],
       produces="una lista de precios",
       prompt="Lista de precios presentable para {negocio} con: {productos}."),
    _r(id="mensaje_whatsapp", category="dia_a_dia", name="Mensaje para clientes (WhatsApp)",
       description="Mensaje listo para difundir promociones o avisos.",
       inputs=[{"key": "aviso", "type": "text", "label": "Qué quieres avisar", "required": True}],
       produces="un mensaje para clientes",
       prompt="Mensaje breve y amable para WhatsApp/redes avisando: {aviso}."),
    _r(id="control_gastos", category="dia_a_dia", name="Control de gastos semanal",
       description="Ordena tus gastos de la semana y detecta dónde ahorrar.",
       inputs=[{"key": "gastos", "type": "text", "label": "Tus gastos de la semana", "required": True}],
       produces="un control de gastos",
       prompt="Organiza estos gastos semanales por categoría y sugiere ahorros: {gastos}."),
    _r(id="agradecimiento_cliente", category="dia_a_dia", name="Mensaje de agradecimiento",
       description="Detalle para fidelizar a un cliente después de su compra.",
       inputs=[{"key": "cliente", "type": "text", "label": "Cliente", "required": True},
               {"key": "compra", "type": "text", "label": "Qué compró"}],
       produces="un mensaje de agradecimiento",
       prompt="Mensaje de agradecimiento a {cliente} por comprar {compra}, invitando a regresar."),
]


def get_recipe(recipe_id: str) -> dict | None:
    return next((r for r in RECIPES if r["id"] == recipe_id), None)


def db_recipe_to_dict(row) -> dict:
    """Convert a curated CatalogRecipe DB row into a runnable recipe dict."""
    import json
    try:
        fields = json.loads(row.inputs) if row.inputs else []
    except (ValueError, TypeError):
        fields = []
    if not fields:  # default: one free-text field
        fields = [{"key": "detalle", "type": "text", "label": "Detalle", "required": True}]
    return _r(
        id=row.slug, category=row.category, name=row.name, icon=row.icon or "sparkles",
        description=row.description, inputs=fields, handler="generic",
        produces=row.produces or "el resultado",
        prompt=row.prompt or f"{row.name}: {{detalle}}",
    )


def public_recipe(r: dict) -> dict:
    keys = ("id", "category", "name", "icon", "description", "inputs",
            "connections", "approval", "approve_label")
    return {k: r[k] for k in keys}


def validate_inputs(recipe: dict, inputs: dict) -> list[str]:
    return [f["label"] for f in recipe["inputs"]
            if f.get("required") and not str(inputs.get(f["key"], "")).strip()]


class _SafeDict(dict):
    def __missing__(self, key):  # leave unknown placeholders readable
        return "(por definir)"


# --- AI pre-fill (draft) ----------------------------------------------------
_REQ_KEYWORDS = (
    "requisito", "deberá", "debera", "presentar", "acredit", "experiencia",
    "plazo", "garantía", "garantia", "propuesta", "criterio", "evaluación",
    "evaluacion", "documento", "anexo", "vigencia", "fianza", "constancia",
)


def prefill(recipe: dict, session: Session, tenant: Tenant, inputs: dict) -> dict:
    handler = recipe.get("handler", "generic")
    if handler == "licitacion":
        return _prefill_licitacion(session, tenant.id, inputs)
    if handler == "correo_agenda":
        return _prefill_correo_agenda(inputs)
    return _prefill_generic(recipe, session, tenant, inputs)


def _prefill_generic(recipe: dict, session: Session, tenant: Tenant, inputs: dict) -> dict:
    """Generate real content through the privacy router + model fallback.

    The instruction is classified and routed (local/VPC for sensitive inputs,
    open/premium otherwise). Offline, the MOCK adapter still returns content.
    """
    from ..regional.countries import get_country
    from ..regional.tramites import to_context
    from ..routers.tramites import layered_search

    country = get_country(getattr(tenant, "country", "MX"))
    instruction = recipe.get("prompt", "").format_map(_SafeDict(inputs)).strip() or recipe["name"]
    produces = recipe.get("produces", "el resultado")
    system = (f"Eres un asistente que genera {produces} para un negocio en {country['name']}. "
              f"Responde en español, claro y listo para usar. Usa el contexto de trámites "
              f"(empresa → estado → país) cuando aplique y cita la autoridad/fuente.")

    # Ground in the layered KB: company-private + state + country curated.
    matches = layered_search(session, tenant, q=f"{recipe.get('name', '')} {instruction}",
                             region=inputs.get("region"), municipio=inputs.get("municipio"),
                             country=country["code"])[:6]
    ground_context = [to_context(t) for t in matches]
    fuentes = [{"title": t["title"], "authority": t.get("authority", ""),
                "fuente": t.get("fuente", ""), "source": t.get("source", "curado")} for t in matches]

    decision = route_request(tenant, None, instruction, ground_context, task="recipe")
    if decision.route == ModelRoute.BLOCKED:
        return {"tipo": "generico", "plan": instruction, "contenido": "", "produces": produces,
                "route": "blocked", "blocked": True,
                "summary": f"⛔ No puedo continuar: {decision.reason}"}

    region_aware = bool(inputs.get("region") or inputs.get("municipio"))
    if region_aware:
        loc = ", ".join(x for x in (inputs.get("municipio"), inputs.get("region"), country["name"]) if x)
        system += (f" Adapta la respuesta a {loc} y advierte que los requisitos varían por "
                   f"localidad y país.")

    gen = generate_with_fallback(decision.route, system, instruction, decision.context or ground_context)
    contenido = gen.response.content if gen.route != ModelRoute.BLOCKED else ""
    tokens = estimate_tokens(instruction + contenido)
    cost = estimate_cost(gen.route, tokens)
    summary = (f"Generé {produces} con tus datos por la ruta «{gen.route.value}». "
               f"Revisa y aprueba; el dato se procesó de forma privada y queda auditado.")
    if region_aware:
        summary += "\n\n" + _REGION_DISCLAIMER
    return {
        "tipo": "generico",
        "plan": instruction,            # what I understood (transparency)
        "contenido": contenido,         # AI-generated draft to review
        "produces": produces,
        "route": gen.route.value,
        "region_aware": region_aware,
        "tokens": tokens,
        "cost": cost,
        "fuentes": fuentes,
        "summary": summary,
    }


def _prefill_licitacion(session: Session, tenant_id: str, inputs: dict) -> dict:
    doc_id = inputs.get("document_id") or None
    empresa = (inputs.get("empresa") or "Nuestra empresa").strip()
    citations = retrieve(
        session, tenant_id,
        "requisitos, requerimientos, criterios de evaluación, documentos a presentar, plazos",
        [doc_id] if doc_id else None, top_k=6,
    )

    requisitos: list[str] = []
    for c in citations:
        for raw in c.text.replace("•", "\n").splitlines():
            line = raw.strip(" -\t")
            if len(line) > 12 and any(k in line.lower() for k in _REQ_KEYWORDS):
                requisitos.append(line[:220])
    requisitos = list(dict.fromkeys(requisitos))[:12]
    if not requisitos:
        requisitos = [c.text.strip()[:200] for c in citations[:5] if c.text.strip()]

    campos = [
        {"requisito": r, "respuesta_sugerida": f"{empresa} cumple con este requisito. [Confirmar evidencia]",
         "estado": "pre-llenado"}
        for r in requisitos
    ]
    return {
        "tipo": "respuesta_licitacion", "empresa": empresa, "fuentes": len(citations), "campos": campos,
        "summary": (f"Detecté {len(campos)} requisitos y pre-llené las respuestas para {empresa}. "
                    f"Revisa y aprueba; el dato no salió de tu infraestructura."),
        "route": "local",
    }


def _prefill_correo_agenda(inputs: dict) -> dict:
    output = inputs.get("output") or "Resumen diario"
    plan = {
        "Resumen diario": "Leeré tu bandeja de hoy y tu agenda y generaré un resumen ejecutivo.",
        "Horario del día": "Compilaré tus eventos del día en orden y detectaré huecos libres.",
        "Pendientes por responder": "Identificaré correos que esperan tu respuesta y los priorizaré.",
    }.get(output, "Generaré el resumen solicitado.")
    return {
        "tipo": "correo_agenda", "email": inputs.get("email", ""), "output": output,
        "summary": f"{plan} Para hacerlo necesito que apruebes la conexión a tu correo y calendario.",
        "route": "vpc",
    }


# --- Execution (after approval) ---------------------------------------------
def execute(recipe: dict, session: Session, tenant_id: str, inputs: dict, draft: dict) -> dict:
    handler = recipe.get("handler", "generic")
    if handler == "licitacion":
        campos = draft.get("campos", [])
        cuerpo = "\n\n".join(f"Requisito: {c['requisito']}\nRespuesta: {c['respuesta_sugerida']}" for c in campos)
        return {"tipo": "respuesta_licitacion",
                "documento": f"RESPUESTA A LICITACIÓN — {draft.get('empresa', '')}\n\n{cuerpo}",
                "campos_completados": len(campos),
                "message": "Respuesta compilada y lista para descargar/enviar."}
    if handler == "correo_agenda":
        return {"tipo": "correo_agenda", "output": inputs.get("output"), "email": inputs.get("email"),
                "message": ("Conexión aprobada. El resumen se generará con tu proveedor de "
                            "correo/calendario y se entregará según la salida elegida."),
                "items": []}
    return {"tipo": "generico", "output": draft.get("contenido") or draft.get("plan"),
            "message": f"{recipe['name']}: {recipe.get('produces', 'resultado')} listo."}
