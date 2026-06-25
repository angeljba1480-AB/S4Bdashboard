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


def _area_input() -> dict:
    # Filled from the company profile's areas (frontend turns it into a dropdown).
    return {"key": "area", "type": "area", "label": "Área responsable",
            "help": "Se llena con las áreas de tu empresa (configúralas en Configuración)."}


def _tono_input() -> dict:
    return {"key": "tono", "type": "choice", "label": "Tono",
            "options": ["Formal", "Cercano", "Persuasivo", "Directo", "Institucional"]}


_REGION_DISCLAIMER = ("⚠️ Los requisitos, costos y plazos cambian por región y localidad (y por país). "
                      "Esto es una guía; confirma siempre con tu autoridad local.")


def _report_template_labels() -> list[str]:
    from .. import report_templates
    return report_templates.template_labels()


def _r(**kw) -> dict:
    """Recipe with sensible defaults so the catalog stays terse and scalable."""
    kw.setdefault("icon", "sparkles")
    kw.setdefault("connections", [])
    kw.setdefault("approval", "draft")
    kw.setdefault("approve_label", "Aprobar y generar")
    kw.setdefault("handler", "generic")
    kw.setdefault("produces", "el resultado")
    kw.setdefault("prompt", "")
    kw.setdefault("rag_category", "")   # document category this recipe grounds in
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
        produces="una respuesta de licitación pre-llenada", rag_category="licitacion_madre",
    ),
    _r(
        id="correo_agenda", category="dia_a_dia", handler="correo_agenda", icon="mail",
        name="Resumen de correo y agenda",
        description="Conecta tu correo (Outlook/Gmail) y genero el resumen del día. Tú apruebas.",
        inputs=[
            {"key": "account", "type": "mailbox", "label": "Cuenta a resumir",
             "help": "Elige una de tus cuentas conectadas. ¿No aparece? Conéctala en Integraciones → «Conectar correo»."},
            {"key": "output", "type": "choice", "label": "Tipo de salida",
             "options": ["Resumen diario", "Horario del día", "Pendientes por responder"], "required": True},
        ],
        approve_label="Generar resumen",
        produces="un resumen de tu correo y agenda",
    ),

    _r(
        id="reporte_industria", category="operaciones", handler="reporte", icon="bar-chart",
        name="Reporte por industria",
        description="Genero un reporte profesional con la estructura de tu industria. Exporta a PDF/Word/PPT/Excel.",
        inputs=[
            {"key": "plantilla", "type": "choice", "label": "Plantilla de industria", "required": True,
             "options": _report_template_labels()},
            {"key": "tema", "type": "text", "label": "Tema del reporte", "required": True,
             "placeholder": "Ej. Resultados del Q2, diagnóstico de operaciones…"},
            {"key": "periodo", "type": "text", "label": "Periodo", "placeholder": "Ej. Q2 2026"},
            _area_input()],
        produces="un reporte por industria", rag_category="conocimiento",
        approve_label="Generar reporte",
    ),

    # ---- Crecer el negocio ------------------------------------------------
    _r(id="propuesta_comercial", category="crecer", name="Propuesta comercial",
       description="Genero una propuesta lista para enviar a tu cliente.",
       inputs=[{"key": "cliente", "type": "text", "label": "Cliente", "required": True,
                "placeholder": "Ej. Grupo Bimbo"},
               {"key": "contacto", "type": "text", "label": "Persona de contacto",
                "placeholder": "Nombre y puesto"},
               {"key": "servicio", "type": "text", "label": "Producto o servicio", "required": True,
                "placeholder": "Ej. Implementación de CRM"},
               {"key": "necesidad", "type": "textarea", "label": "Necesidad o problema del cliente",
                "placeholder": "¿Qué dolor resuelves? Contexto del cliente…"},
               {"key": "alcance", "type": "textarea", "label": "Alcance / entregables",
                "placeholder": "Qué incluye: fases, entregables, soporte…"},
               {"key": "precio", "type": "text", "label": "Precio (aprox.)", "placeholder": "Ej. $250,000 MXN"},
               {"key": "plazo", "type": "text", "label": "Plazo de entrega", "placeholder": "Ej. 8 semanas"},
               {"key": "diferenciadores", "type": "textarea", "label": "Por qué elegirte",
                "placeholder": "Ventajas, casos de éxito, garantías…"},
               {"key": "vigencia", "type": "text", "label": "Vigencia de la oferta", "placeholder": "Ej. 30 días"},
               _tono_input(), _area_input()],
       produces="una propuesta comercial", rag_category="propuesta_comercial",
       prompt=("Propuesta comercial para {cliente} (contacto: {contacto}) sobre {servicio}. "
               "Necesidad del cliente: {necesidad}. Alcance/entregables: {alcance}. "
               "Precio: {precio}. Plazo: {plazo}. Diferenciadores: {diferenciadores}. "
               "Vigencia: {vigencia}. Tono: {tono}. Incluye introducción, alcance, "
               "inversión, beneficios y siguiente paso.")),
    _r(id="post_redes", category="crecer", name="Publicación para redes sociales",
       description="Creo el texto y hashtags para promocionar tu negocio.",
       inputs=[{"key": "negocio", "type": "text", "label": "Tu negocio", "required": True},
               {"key": "promo", "type": "text", "label": "Qué quieres promocionar", "required": True,
                "placeholder": "Producto, oferta o anuncio"},
               {"key": "red", "type": "choice", "label": "Red social",
                "options": ["Instagram", "Facebook", "TikTok", "LinkedIn", "X (Twitter)", "WhatsApp"]},
               {"key": "objetivo", "type": "choice", "label": "Objetivo",
                "options": ["Vender", "Dar a conocer", "Interacción", "Atraer seguidores"]},
               {"key": "cta", "type": "text", "label": "Llamada a la acción",
                "placeholder": "Ej. Escríbenos por DM / Visita la tienda"},
               _tono_input()],
       produces="una publicación para redes",
       prompt=("Publicación para {red} de {negocio} promocionando {promo}. Objetivo: {objetivo}. "
               "Llamada a la acción: {cta}. Tono: {tono}. Incluye copy + 5 a 8 hashtags relevantes.")),

    # ---- Abrir / lanzar ---------------------------------------------------
    _r(id="plan_negocio", category="abrir", name="Plan de negocio express",
       description="Bosquejo un plan simple para arrancar tu idea.",
       inputs=[{"key": "idea", "type": "textarea", "label": "Tu idea de negocio", "required": True,
                "placeholder": "Describe qué vas a vender y a quién"},
               {"key": "ciudad", "type": "text", "label": "Ciudad / zona"},
               {"key": "clientes", "type": "text", "label": "Clientes objetivo",
                "placeholder": "¿A quién le vendes?"},
               {"key": "inversion", "type": "text", "label": "Inversión disponible",
                "placeholder": "Ej. $50,000 MXN"},
               {"key": "modelo", "type": "choice", "label": "Modelo de venta",
                "options": ["Local físico", "En línea", "Mixto", "A domicilio", "Por catálogo"]}],
       produces="un plan de negocio express",
       prompt=("Plan de negocio express para: {idea} en {ciudad}. Clientes objetivo: {clientes}. "
               "Inversión: {inversion}. Modelo de venta: {modelo}. Incluye propuesta de valor, "
               "mercado, costos/ingresos estimados, primeros pasos y riesgos.")),
    _r(id="registro_tramites", category="abrir", name="Checklist de trámites para abrir",
       description="Lista de pasos y trámites para formalizar tu negocio.",
       inputs=[{"key": "giro", "type": "text", "label": "Giro del negocio", "required": True},
               {"key": "ciudad", "type": "text", "label": "Ciudad / estado"},
               {"key": "figura", "type": "choice", "label": "Figura legal",
                "options": ["Persona física", "Persona moral (S.A. / S. de R.L.)", "Aún no sé"]},
               {"key": "empleados", "type": "choice", "label": "¿Tendrás empleados?",
                "options": ["Sí", "No", "Más adelante"]}],
       produces="un checklist de trámites",
       prompt=("Checklist de trámites para abrir un negocio de {giro} en {ciudad} como {figura}. "
               "Empleados: {empleados}. Ordena por etapa (SAT, municipio, IMSS si aplica) con tiempos.")),

    # ---- Cumplimiento (CEP / legal) ---------------------------------------
    _r(id="aviso_privacidad", category="cumplimiento", name="Aviso de privacidad",
       description="Genero un aviso de privacidad base para tu negocio.",
       inputs=[{"key": "empresa", "type": "text", "label": "Nombre del negocio", "required": True},
               {"key": "datos", "type": "textarea", "label": "Datos que recolectas",
                "placeholder": "Ej. nombre, correo, teléfono, dirección, RFC…"},
               {"key": "finalidad", "type": "textarea", "label": "Para qué los usas",
                "placeholder": "Ej. facturación, envíos, contacto, marketing"},
               {"key": "canal", "type": "choice", "label": "Dónde se publicará",
                "options": ["Sitio web", "Local físico", "App", "Redes sociales"]},
               {"key": "contacto_arco", "type": "email", "label": "Correo para derechos ARCO",
                "placeholder": "privacidad@tunegocio.com"}],
       produces="un aviso de privacidad",
       prompt=("Aviso de privacidad para {empresa} que recolecta {datos} con finalidad {finalidad}, "
               "publicado en {canal}, contacto ARCO {contacto_arco}. Conforme a la LFPDPPP de México.")),
    _r(id="contrato_simple", category="cumplimiento", name="Contrato sencillo",
       description="Borrador de contrato de prestación de servicios.",
       inputs=[{"key": "parte_a", "type": "text", "label": "Tú / tu empresa", "required": True},
               {"key": "parte_b", "type": "text", "label": "Cliente", "required": True},
               {"key": "objeto", "type": "textarea", "label": "Objeto del contrato", "required": True,
                "placeholder": "Qué servicio/producto se entrega"},
               {"key": "monto", "type": "text", "label": "Monto y forma de pago",
                "placeholder": "Ej. $30,000 MXN, 50% anticipo"},
               {"key": "plazo", "type": "text", "label": "Plazo / vigencia", "placeholder": "Ej. 3 meses"},
               {"key": "lugar", "type": "text", "label": "Ciudad de firma"}],
       produces="un contrato sencillo", rag_category="contrato_cliente",
       prompt=("Contrato de prestación de servicios entre {parte_a} (prestador) y {parte_b} (cliente) "
               "por {objeto}. Monto y pago: {monto}. Plazo: {plazo}. Lugar: {lugar}. Incluye cláusulas "
               "de objeto, contraprestación, obligaciones, confidencialidad, vigencia y terminación.")),

    # ---- Operaciones ------------------------------------------------------
    _r(id="cotizacion", category="operaciones", name="Cotización rápida",
       description="Armo una cotización lista para mandar (ideal por WhatsApp).",
       inputs=[{"key": "cliente", "type": "text", "label": "Cliente", "required": True},
               {"key": "concepto", "type": "textarea", "label": "Conceptos (uno por línea)", "required": True,
                "placeholder": "Producto/servicio — cantidad — precio unitario"},
               {"key": "descuento", "type": "text", "label": "Descuento", "placeholder": "Ej. 10% o $500"},
               {"key": "iva", "type": "choice", "label": "¿Incluye IVA?", "options": ["Sí", "No"]},
               {"key": "validez", "type": "text", "label": "Vigencia", "placeholder": "Ej. 15 días"},
               {"key": "pago", "type": "text", "label": "Condiciones de pago", "placeholder": "Ej. 50% anticipo"}],
       produces="una cotización",
       prompt=("Cotización para {cliente} con conceptos: {concepto}. Descuento: {descuento}. "
               "IVA: {iva}. Vigencia: {validez}. Pago: {pago}. Incluye tabla con subtotal, IVA y total.")),
    _r(id="inventario_alerta", category="operaciones", name="Control de inventario",
       description="Registro y alerta de productos por agotarse.",
       inputs=[{"key": "productos", "type": "textarea", "label": "Productos y cantidades", "required": True,
                "placeholder": "Producto — existencia actual (uno por línea)"},
               {"key": "minimo", "type": "number", "label": "Stock mínimo de alerta", "placeholder": "Ej. 5"}],
       produces="un control de inventario con alertas",
       prompt=("Control de inventario y alertas de stock bajo para: {productos}. "
               "Marca en rojo lo que esté por debajo de {minimo} unidades y sugiere reorden.")),

    # ---- Día a día (incluye economía informal) ----------------------------
    _r(id="precio_venta", category="dia_a_dia", name="Calcular precio de venta",
       description="Te digo a cuánto vender según tu costo y ganancia deseada.",
       inputs=[{"key": "costo", "type": "number", "label": "Costo del producto", "required": True,
                "placeholder": "Ej. 120"},
               {"key": "ganancia", "type": "number", "label": "Ganancia que quieres (%)", "placeholder": "Ej. 40"},
               {"key": "gastos_extra", "type": "text", "label": "Gastos extra por unidad",
                "placeholder": "Envío, empaque, comisión…"}],
       produces="tu precio de venta sugerido",
       prompt=("Calcula precio de venta con costo {costo} y ganancia {ganancia}%, considerando "
               "gastos extra {gastos_extra}. Muestra el desglose y el margen final.")),
    _r(id="corte_caja", category="dia_a_dia", name="Corte de caja del día",
       description="Resumo tus ventas y gastos del día.",
       inputs=[{"key": "fecha", "type": "date", "label": "Fecha"},
               {"key": "ventas", "type": "textarea", "label": "Ventas del día", "required": True,
                "placeholder": "Concepto — monto (uno por línea), o total"},
               {"key": "gastos", "type": "textarea", "label": "Gastos del día",
                "placeholder": "Concepto — monto (uno por línea)"},
               {"key": "fondo", "type": "number", "label": "Fondo de caja inicial"}],
       produces="tu corte de caja",
       prompt=("Corte de caja del {fecha}: fondo inicial {fondo}, ventas {ventas}, gastos {gastos}. "
               "Calcula total de ventas, total de gastos, efectivo esperado y utilidad del día.")),

    # ===== Más casos sembrados =====
    # ---- Crecer el negocio ----
    _r(id="guion_ventas", category="crecer", name="Guion de ventas",
       description="Un guion para vender por teléfono o en persona.",
       inputs=[{"key": "producto", "type": "text", "label": "Producto/servicio", "required": True},
               {"key": "cliente_tipo", "type": "text", "label": "Tipo de cliente",
                "placeholder": "Ej. dueños de restaurantes"},
               {"key": "canal", "type": "choice", "label": "Canal",
                "options": ["Teléfono", "En persona", "Videollamada", "WhatsApp"]},
               {"key": "objeciones", "type": "textarea", "label": "Objeciones comunes",
                "placeholder": "Ej. precio alto, ya tienen proveedor…"},
               _tono_input()],
       produces="un guion de ventas",
       prompt=("Guion de ventas para vender {producto} a {cliente_tipo} por {canal}. Tono: {tono}. "
               "Incluye apertura, descubrimiento, pitch, manejo de objeciones ({objeciones}) y cierre.")),
    _r(id="correo_frio", category="crecer", name="Correo de prospección",
       description="Correo en frío para conseguir una reunión.",
       inputs=[{"key": "prospecto", "type": "text", "label": "Empresa/persona objetivo", "required": True},
               {"key": "oferta", "type": "text", "label": "Qué ofreces", "required": True},
               {"key": "gancho", "type": "textarea", "label": "Gancho / por qué ahora",
                "placeholder": "Dato, logro o dolor del prospecto"},
               {"key": "cta", "type": "text", "label": "Llamada a la acción",
                "placeholder": "Ej. ¿15 min el jueves?"},
               _tono_input()],
       produces="un correo de prospección",
       prompt=("Correo en frío a {prospecto} ofreciendo {oferta}. Gancho: {gancho}. Tono: {tono}. "
               "Asunto atractivo + cuerpo breve + llamada a la acción: {cta}.")),
    _r(id="promo_temporada", category="crecer", name="Promoción de temporada",
       description="Idea y texto de una promoción para fechas clave.",
       inputs=[{"key": "negocio", "type": "text", "label": "Tu negocio", "required": True},
               {"key": "fecha", "type": "text", "label": "Temporada/fecha", "placeholder": "Ej. Buen Fin"},
               {"key": "productos", "type": "text", "label": "Qué entra en promoción"},
               {"key": "tipo_promo", "type": "choice", "label": "Tipo de promoción",
                "options": ["Descuento %", "2x1", "Regalo por compra", "Envío gratis", "Paquete"]},
               {"key": "vigencia", "type": "text", "label": "Vigencia", "placeholder": "Ej. 13–18 nov"}],
       produces="una promoción de temporada",
       prompt=("Promoción para {negocio} en {fecha} sobre {productos}, tipo {tipo_promo}, vigencia {vigencia}. "
               "Incluye mecánica clara, mensaje de difusión y condiciones.")),

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
       inputs=[{"key": "giro", "type": "text", "label": "Giro/idea", "required": True},
               {"key": "estilo", "type": "choice", "label": "Estilo del nombre",
                "options": ["Moderno", "Clásico", "Divertido", "Profesional", "Corto/pegajoso"]},
               {"key": "palabras", "type": "text", "label": "Palabras que te gustan o evitar",
                "placeholder": "Opcional"}],
       produces="ideas de nombre",
       prompt=("Propón 8 nombres estilo {estilo} para un negocio de {giro} (considera: {palabras}) "
               "y cómo verificar disponibilidad (IMPI/dominio/redes).")),

    # ---- Cumplimiento (CEP / legal) (varios con REGIÓN) ----
    _r(id="rfc_alta", category="cumplimiento", name="Alta en el RFC (guía)",
       description="Pasos para darte de alta en el SAT según tu actividad.",
       inputs=[{"key": "actividad", "type": "text", "label": "Tu actividad", "required": True},
               {"key": "persona", "type": "choice", "label": "Tipo de contribuyente",
                "options": ["Persona física", "Persona moral"]},
               {"key": "regimen", "type": "text", "label": "Régimen (si lo sabes, ej. RESICO)"},
               {"key": "ingresos", "type": "text", "label": "Ingresos anuales estimados",
                "placeholder": "Ayuda a sugerir el régimen"}],
       produces="la guía de alta en el RFC",
       prompt=("Guía para darse de alta en el RFC ante el SAT para {actividad} como {persona} "
               "(régimen {regimen}, ingresos {ingresos}). Incluye documentos, citas y pasos.")),
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
               {"key": "productos", "type": "text", "label": "Qué vendes"},
               {"key": "plazo", "type": "text", "label": "Plazo para devoluciones", "placeholder": "Ej. 30 días"},
               {"key": "condiciones", "type": "textarea", "label": "Condiciones",
                "placeholder": "Ej. con ticket, producto sin uso…"},
               {"key": "reembolso", "type": "choice", "label": "Tipo de reembolso",
                "options": ["Devolución de dinero", "Cambio de producto", "Nota de crédito", "Según el caso"]}],
       produces="una política de devoluciones",
       prompt=("Política de devoluciones y garantías para {negocio} que vende {productos}. "
               "Plazo: {plazo}. Condiciones: {condiciones}. Reembolso: {reembolso}. Acorde a PROFECO.")),

    # ---- Operaciones ----
    _r(id="orden_compra", category="operaciones", name="Orden de compra a proveedor",
       description="Genero una orden de compra lista para enviar.",
       inputs=[{"key": "proveedor", "type": "text", "label": "Proveedor", "required": True},
               {"key": "articulos", "type": "textarea", "label": "Artículos y cantidades", "required": True,
                "placeholder": "Artículo — cantidad — precio (uno por línea)"},
               {"key": "fecha_entrega", "type": "date", "label": "Fecha de entrega requerida"},
               {"key": "lugar_entrega", "type": "text", "label": "Lugar de entrega"},
               {"key": "pago", "type": "text", "label": "Condiciones de pago", "placeholder": "Ej. 30 días"}],
       produces="una orden de compra",
       prompt=("Orden de compra a {proveedor} por: {articulos}. Entrega {fecha_entrega} en {lugar_entrega}. "
               "Pago: {pago}. Incluye folio, tabla de artículos con totales y datos de entrega.")),
    _r(id="recordatorio_cobranza", category="operaciones", name="Recordatorio de cobranza",
       description="Mensaje amable para cobrar a un cliente.",
       inputs=[{"key": "cliente", "type": "text", "label": "Cliente", "required": True},
               {"key": "monto", "type": "text", "label": "Monto/adeudo", "required": True},
               {"key": "vencimiento", "type": "date", "label": "Fecha de vencimiento"},
               {"key": "factura", "type": "text", "label": "Folio de factura", "placeholder": "Ej. F-1024"},
               {"key": "etapa", "type": "choice", "label": "Etapa del recordatorio",
                "options": ["Primer aviso (amable)", "Segundo aviso", "Vencido (firme)"]},
               {"key": "pagos", "type": "text", "label": "Opciones de pago", "placeholder": "Transferencia, link…"}],
       produces="un recordatorio de cobranza",
       prompt=("Mensaje de cobranza a {cliente} por {monto} (factura {factura}, vence {vencimiento}). "
               "Etapa: {etapa}. Opciones de pago: {pagos}. Cordial pero claro.")),
    _r(id="horario_turnos", category="operaciones", name="Rol de turnos del personal",
       description="Arma un rol de turnos simple para tu equipo.",
       inputs=[{"key": "personas", "type": "textarea", "label": "Personas y disponibilidad", "required": True,
                "placeholder": "Nombre — días/horas disponibles (uno por línea)"},
               {"key": "horario", "type": "text", "label": "Horario del negocio", "placeholder": "Ej. 9–21h"},
               {"key": "dias", "type": "text", "label": "Días de operación", "placeholder": "Ej. Lun a Sáb"},
               {"key": "min_por_turno", "type": "number", "label": "Personas mínimas por turno"}],
       produces="un rol de turnos",
       prompt=("Rol de turnos semanal para {personas}. Horario {horario}, días {dias}, "
               "mínimo {min_por_turno} por turno. Devuélvelo como tabla por día.")),

    # ---- Día a día (incluye economía informal) ----
    _r(id="carta_precios", category="dia_a_dia", name="Carta / lista de precios",
       description="Arma una lista de precios presentable para mostrar o imprimir.",
       inputs=[{"key": "productos", "type": "textarea", "label": "Productos y precios", "required": True,
                "placeholder": "Producto — precio (uno por línea)"},
               {"key": "negocio", "type": "text", "label": "Nombre del negocio"},
               {"key": "moneda", "type": "choice", "label": "Moneda",
                "options": ["MXN", "USD", "Otra"]},
               {"key": "notas", "type": "text", "label": "Notas", "placeholder": "Ej. precios sujetos a cambio"}],
       produces="una lista de precios",
       prompt=("Lista de precios presentable para {negocio} en {moneda} con: {productos}. "
               "Agrúpala por categoría y añade nota: {notas}.")),
    _r(id="mensaje_whatsapp", category="dia_a_dia", name="Mensaje para clientes (WhatsApp)",
       description="Mensaje listo para difundir promociones o avisos.",
       inputs=[{"key": "aviso", "type": "textarea", "label": "Qué quieres avisar", "required": True,
                "placeholder": "Promoción, horario especial, nuevo producto…"},
               {"key": "publico", "type": "text", "label": "A quién va dirigido",
                "placeholder": "Ej. clientes frecuentes"},
               {"key": "cta", "type": "text", "label": "Qué quieres que hagan",
                "placeholder": "Ej. aparta por DM"},
               _tono_input()],
       produces="un mensaje para clientes",
       prompt=("Mensaje breve para WhatsApp/redes dirigido a {publico} avisando: {aviso}. "
               "Llamada a la acción: {cta}. Tono: {tono}. Incluye emojis con moderación.")),
    _r(id="control_gastos", category="dia_a_dia", name="Control de gastos semanal",
       description="Ordena tus gastos de la semana y detecta dónde ahorrar.",
       inputs=[{"key": "gastos", "type": "textarea", "label": "Tus gastos de la semana", "required": True,
                "placeholder": "Concepto — monto (uno por línea)"},
               {"key": "presupuesto", "type": "number", "label": "Presupuesto semanal", "placeholder": "Ej. 5000"}],
       produces="un control de gastos",
       prompt=("Organiza estos gastos semanales por categoría y sugiere ahorros: {gastos}. "
               "Compara contra un presupuesto de {presupuesto} y marca desviaciones.")),
    _r(id="agradecimiento_cliente", category="dia_a_dia", name="Mensaje de agradecimiento",
       description="Detalle para fidelizar a un cliente después de su compra.",
       inputs=[{"key": "cliente", "type": "text", "label": "Cliente", "required": True},
               {"key": "compra", "type": "text", "label": "Qué compró"},
               {"key": "incentivo", "type": "text", "label": "Incentivo para que regrese",
                "placeholder": "Ej. 10% en su próxima compra"},
               _tono_input()],
       produces="un mensaje de agradecimiento",
       prompt=("Mensaje de agradecimiento a {cliente} por comprar {compra}, con incentivo {incentivo} "
               "para que regrese. Tono: {tono}.")),
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
            "connections", "approval", "approve_label", "rag_category")
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


def prefill(recipe: dict, session: Session, tenant: Tenant, inputs: dict, user_id: str | None = None) -> dict:
    handler = recipe.get("handler", "generic")
    if handler == "licitacion":
        return _prefill_licitacion(session, tenant.id, inputs, recipe)
    if handler == "correo_agenda":
        return _prefill_correo_agenda(session, tenant, user_id, inputs)
    if handler == "reporte":
        return _prefill_reporte(recipe, session, tenant, inputs, user_id)
    return _prefill_generic(recipe, session, tenant, inputs, user_id)


def _prefill_reporte(recipe: dict, session: Session, tenant: Tenant, inputs: dict,
                     user_id: str | None = None) -> dict:
    """Build a sectioned, industry-specific report prompt, then run it through the
    generic pipeline (privacy routing + company RAG + fallback)."""
    from .. import report_templates

    tpl = report_templates.get_by_key_or_label(inputs.get("plantilla", "")) \
        or report_templates.get_by_key_or_label("generico")
    sections = "\n".join(f"{i}. {s}" for i, s in enumerate(tpl["sections"], 1))
    tema = (inputs.get("tema") or "el tema solicitado").strip()
    periodo = (inputs.get("periodo") or "").strip()
    instruction = (
        f"Redacta un reporte profesional sobre «{tema}»"
        + (f" para el periodo {periodo}" if periodo else "")
        + f" para la industria «{tpl['label']}». "
        "Usa EXACTAMENTE estas secciones, en este orden, cada una con su encabezado Markdown (##):\n"
        f"{sections}\n"
        "Sé concreto y accionable; si faltan datos, indícalo como supuesto. "
        "Apóyate en el contexto de la empresa y sus documentos."
    )
    synth = {**recipe, "prompt": instruction, "produces": "un reporte por industria"}
    return _prefill_generic(synth, session, tenant, inputs, user_id)


# Output-format presets shared by every use case (the "formato de salida" step).
# An empty/unknown value means "predeterminado" (no extra shaping).
FORMAT_GUIDE = {
    "documento_formal": "Formato: documento formal y bien estructurado, con secciones y encabezados.",
    "resumen_ejecutivo": "Formato: resumen ejecutivo breve, con viñetas y los puntos clave primero.",
    "tabla": "Formato: presenta la información en tablas cuando sea posible.",
    "presentacion": "Formato: esquema de presentación (diapositivas con título y viñetas).",
    "carta": "Formato: carta/comunicado profesional listo para enviar.",
}


def apply_intent(system: str, instruction: str, inputs: dict) -> tuple[str, str]:
    """Weave the universal 'objetivo + notas + formato' step into any prompt so
    every use case can be steered toward the user's goal and desired output."""
    objetivo = str(inputs.get("objetivo", "")).strip()
    notas = str(inputs.get("notas", "")).strip()
    formato = str(inputs.get("formato", "")).strip()
    formato_notas = str(inputs.get("formato_notas", "")).strip()

    extra: list[str] = []
    if objetivo:
        extra.append(f"Objetivo que busca el usuario: {objetivo}.")
    if notas:
        extra.append(f"Notas y preferencias a considerar: {notas}.")
    guide = FORMAT_GUIDE.get(formato)
    if guide:
        extra.append(guide)
    if formato == "personalizado" and formato_notas:
        extra.append(f"Formato solicitado por el usuario: {formato_notas}.")
    if extra:
        instruction = instruction + "\n\n" + " ".join(extra)
    return system, instruction


def _prefill_generic(recipe: dict, session: Session, tenant: Tenant, inputs: dict,
                     user_id: str | None = None) -> dict:
    """Generate real content through the privacy router + model fallback.

    The instruction is classified and routed (local/VPC for sensitive inputs,
    open/premium otherwise). Offline, the MOCK adapter still returns content.
    """
    from ..company_profile import context_block, get_or_create
    from ..regional.countries import get_country
    from ..regional.tramites import to_context
    from ..routers.tramites import layered_search

    country = get_country(getattr(tenant, "country", "MX"))
    instruction = recipe.get("prompt", "").format_map(_SafeDict(inputs)).strip() or recipe["name"]
    produces = recipe.get("produces", "el resultado")
    system = (f"Eres un asistente que genera {produces} para un negocio en {country['name']}. "
              f"Responde en español, claro y listo para usar. Usa el contexto de trámites "
              f"(empresa → estado → país) cuando aplique y cita la autoridad/fuente.")

    # Universal "objetivo + notas + formato" step: steer toward the user's goal.
    system, instruction = apply_intent(system, instruction, inputs)

    # Pre-configured company context (onboarding profile) personalizes the output.
    company_ctx = context_block(get_or_create(session, tenant.id),
                                getattr(tenant, "brand_name", "") or tenant.name)
    if company_ctx:
        system += "\n\n" + company_ctx
    if str(inputs.get("area", "")).strip():
        system += f"\n\nEsta solicitud proviene del área «{inputs['area']}»; adáptala a esa área."

    # Ground in the layered KB: company-private + state + country curated. When the
    # recipe declares a rag_category, the company-RAG layer is restricted to that
    # document type (e.g. "Propuesta comercial" → category propuesta_comercial).
    areas = None
    if user_id:
        from ..models import User
        from ..permissions import visible_areas
        u = session.get(User, user_id)
        if u:
            areas = visible_areas(u)
    matches = layered_search(session, tenant, q=f"{recipe.get('name', '')} {instruction}",
                             region=inputs.get("region"), municipio=inputs.get("municipio"),
                             country=country["code"], include_rag=True,
                             rag_category=recipe.get("rag_category") or None, areas=areas)[:6]
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


def _prefill_licitacion(session: Session, tenant_id: str, inputs: dict, recipe: dict | None = None) -> dict:
    doc_id = inputs.get("document_id") or None
    empresa = (inputs.get("empresa") or "Nuestra empresa").strip()
    # Use the uploaded tender when given; otherwise ground in the company's
    # "documento madre de licitación" category so reusable boilerplate is found.
    rag_category = (recipe or {}).get("rag_category") or None
    citations = retrieve(
        session, tenant_id,
        "requisitos, requerimientos, criterios de evaluación, documentos a presentar, plazos",
        [doc_id] if doc_id else None, top_k=6,
        category=None if doc_id else rag_category,
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


def _prefill_correo_agenda(session: Session, tenant: Tenant, user_id: str | None, inputs: dict) -> dict:
    from ..integrations import token_store
    output = inputs.get("output") or "Resumen diario"
    plan = {
        "Resumen diario": "Leeré tu bandeja de hoy y tu agenda y generaré un resumen ejecutivo.",
        "Horario del día": "Compilaré tus eventos del día en orden y detectaré huecos libres.",
        "Pendientes por responder": "Identificaré correos que esperan tu respuesta y los priorizaré.",
    }.get(output, "Generaré el resumen solicitado.")

    prefer = inputs.get("account") or inputs.get("email", "")
    conn = token_store.resolve_connection(session, tenant.id, user_id, prefer) if user_id else None
    if conn:
        return {
            "tipo": "correo_agenda", "account": conn.id, "output": output,
            "connected": True, "provider": conn.provider,
            "summary": f"{plan} Conectado como {conn.identifier} ({conn.provider}). "
                       f"Aprueba para generarlo ahora con tu correo real.",
            "route": "open",
        }
    return {
        "tipo": "correo_agenda", "account": prefer, "output": output,
        "connected": False, "needs_oauth": True,
        "summary": (f"{plan} Primero conecta tu correo en Integraciones → «Conectar correo». "
                    f"Aún no hay una cuenta conectada."),
        "route": "vpc",
    }


# --- Execution (after approval) ---------------------------------------------
def execute(recipe: dict, session: Session, tenant_id: str, inputs: dict, draft: dict,
            user_id: str | None = None) -> dict:
    handler = recipe.get("handler", "generic")
    if handler == "licitacion":
        campos = draft.get("campos", [])
        cuerpo = "\n\n".join(f"Requisito: {c['requisito']}\nRespuesta: {c['respuesta_sugerida']}" for c in campos)
        return {"tipo": "respuesta_licitacion",
                "documento": f"RESPUESTA A LICITACIÓN — {draft.get('empresa', '')}\n\n{cuerpo}",
                "campos_completados": len(campos),
                "message": "Respuesta compilada y lista para descargar/enviar."}
    if handler == "correo_agenda":
        return _execute_correo_agenda(session, tenant_id, user_id, inputs)
    return {"tipo": "generico", "output": draft.get("contenido") or draft.get("plan"),
            "message": f"{recipe['name']}: {recipe.get('produces', 'resultado')} listo."}


def _execute_correo_agenda(session: Session, tenant_id: str, user_id: str | None, inputs: dict) -> dict:
    from ..integrations import mailbox, token_store
    output = inputs.get("output") or "Resumen diario"
    prefer = inputs.get("account") or inputs.get("email", "")
    base = {"tipo": "correo_agenda", "output": output, "account": prefer, "items": []}

    conn = token_store.resolve_connection(session, tenant_id, user_id, prefer) if user_id else None
    if not conn:
        return {**base, "message": ("Conecta tu correo en Integraciones → «Conectar correo» y "
                                    "vuelve a ejecutar este caso.")}
    tenant = session.get(Tenant, tenant_id)
    access = token_store.access_token_for(session, tenant, conn)
    if not access:
        return {**base, "message": "La conexión expiró o fue revocada. Reconéctala en Integraciones."}

    data = mailbox.fetch(conn.provider, access)
    _, extra = apply_intent("", "", inputs)  # objetivo/notas/formato → afina el resumen
    summary = mailbox.summarize(session, tenant, data, output, extra_instruction=extra.strip())
    if summary.get("empty"):
        return {**base, "message": "No se encontraron correos ni eventos recientes para resumir."}
    counts = summary.get("counts", {})
    return {**base, "documento": summary["content"], "route": summary.get("route", ""),
            "message": (f"{output} generado desde {conn.identifier or conn.provider}: "
                        f"{counts.get('messages', 0)} correos, {counts.get('events', 0)} eventos.")}
