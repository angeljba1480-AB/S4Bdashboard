"""Curated knowledge base of government procedures (trámites) by country, state
and municipality. Pure data — shared by the platform (use-case grounding,
agents) and by the MCP server (app/mcp/tramites_server.py).

Each entry is a *curated guideline*: requisitos, pasos, autoridad, costo aprox.,
vigencia y fuente. Scope: "nacional" | "estatal" | "municipal". This is the
source of truth that grounds answers per país/estado/municipio.
"""
from __future__ import annotations


def _t(**kw) -> dict:
    kw.setdefault("region", "")        # estado/provincia/departamento ("" = nacional)
    kw.setdefault("municipio", "")     # "" = aplica a todo el estado/país
    kw.setdefault("category", "cumplimiento")
    kw.setdefault("eje", "economia")
    kw.setdefault("costo_aprox", "Variable")
    kw.setdefault("vigencia", "")
    kw.setdefault("fuente", "")
    kw.setdefault("keywords", [])
    return kw


TRAMITES: list[dict] = [
    # ===== México — nacional =====
    _t(id="mx_rfc", country="MX", scope="nacional", category="cumplimiento", eje="economia",
       title="Inscripción al RFC (SAT)",
       authority="Servicio de Administración Tributaria (SAT)",
       requisitos=["CURP", "Identificación oficial vigente", "Comprobante de domicilio",
                   "Correo y teléfono"],
       pasos=["Agenda cita en citas.sat.gob.mx", "Acude con tus documentos o usa SAT ID",
              "Define tu régimen (p. ej. RESICO)", "Obtén tu Constancia de Situación Fiscal"],
       costo_aprox="Gratuito", fuente="https://www.sat.gob.mx",
       keywords=["rfc", "sat", "alta", "régimen", "resico", "constancia fiscal", "impuestos"]),
    _t(id="mx_aviso_privacidad", country="MX", scope="nacional", category="cumplimiento", eje="gobierno_digital",
       title="Aviso de privacidad (LFPDPPP)",
       authority="INAI",
       requisitos=["Identidad y domicilio del responsable", "Datos personales que se recaban",
                   "Finalidades del tratamiento", "Medios para ejercer derechos ARCO"],
       pasos=["Redacta el aviso integral", "Publícalo donde recabas datos",
              "Incluye el aviso simplificado en formularios"],
       costo_aprox="Gratuito (autogestión)", fuente="https://home.inai.org.mx",
       keywords=["aviso de privacidad", "datos personales", "arco", "inai", "lfpdppp"]),
    _t(id="mx_profeco", country="MX", scope="nacional", category="cumplimiento", eje="seguridad",
       title="Obligaciones ante PROFECO",
       authority="PROFECO",
       requisitos=["Precios y condiciones a la vista", "Garantías por escrito",
                   "Política de devoluciones clara", "Comprobantes de compra"],
       pasos=["Muestra precios totales con IVA", "Respeta promociones anunciadas",
              "Atiende reclamaciones y conciliaciones"],
       costo_aprox="Sin costo (cumplimiento)", fuente="https://www.gob.mx/profeco",
       keywords=["profeco", "consumidor", "garantía", "devoluciones", "precios"]),

    # ===== México — estatal / municipal =====
    _t(id="mx_jal_gdl_licencia", country="MX", scope="municipal", region="Jalisco", municipio="Guadalajara",
       category="abrir", eje="economia",
       title="Licencia de funcionamiento — Guadalajara",
       authority="Dirección de Padrón y Licencias, Municipio de Guadalajara",
       requisitos=["Identificación oficial", "Comprobante de domicilio del local",
                   "Constancia de uso de suelo compatible", "RFC", "Dictamen de Protección Civil (según giro)"],
       pasos=["Verifica uso de suelo", "Reúne requisitos del giro", "Ingresa solicitud en Padrón y Licencias",
              "Paga derechos", "Recibe tu licencia/refrendo"],
       costo_aprox="$1,000–$8,000 MXN según giro/superficie", vigencia="Anual (refrendo)",
       fuente="https://guadalajara.gob.mx", keywords=["licencia", "funcionamiento", "guadalajara", "padrón", "giro"]),
    _t(id="mx_cdmx_uso_suelo", country="MX", scope="municipal", region="Ciudad de México",
       category="abrir", eje="servicios",
       title="Certificado único de uso de suelo — CDMX",
       authority="SEDUVI, Ciudad de México",
       requisitos=["Ubicación y cuenta predial", "Identificación", "Pago de derechos"],
       pasos=["Consulta el SIG de uso de suelo", "Solicita el certificado en SEDUVI/llave CDMX",
              "Paga derechos", "Descarga el certificado"],
       costo_aprox="~$1,500 MXN", fuente="https://www.seduvi.cdmx.gob.mx",
       keywords=["uso de suelo", "cdmx", "seduvi", "certificado", "predial"]),

    # ===== Colombia =====
    _t(id="co_rut", country="CO", scope="nacional", category="cumplimiento", eje="economia",
       title="Inscripción al RUT (DIAN)",
       authority="DIAN",
       requisitos=["Documento de identidad", "Correo electrónico"],
       pasos=["Ingresa a muisca.dian.gov.co", "Diligencia el formulario RUT", "Agenda cita si requiere verificación",
              "Obtén tu RUT con NIT"],
       costo_aprox="Gratuito", fuente="https://www.dian.gov.co",
       keywords=["rut", "dian", "nit", "impuestos", "colombia"]),
    _t(id="co_camara_comercio", country="CO", scope="nacional", category="abrir", eje="economia",
       title="Matrícula mercantil (Cámara de Comercio)",
       authority="Cámara de Comercio local",
       requisitos=["RUT", "Documento de identidad", "Formulario RUES", "Nombre del establecimiento"],
       pasos=["Consulta homonimia en RUES", "Diligencia el formulario", "Paga la matrícula",
              "Renueva cada año"],
       costo_aprox="Según activos (tarifa CCB)", vigencia="Anual",
       fuente="https://www.rues.org.co", keywords=["cámara de comercio", "matrícula mercantil", "rues", "colombia"]),

    # ===== Argentina =====
    _t(id="ar_monotributo", country="AR", scope="nacional", category="cumplimiento", eje="economia",
       title="Alta de Monotributo (AFIP/ARCA)",
       authority="AFIP / ARCA",
       requisitos=["CUIT", "Clave fiscal", "Categoría según ingresos"],
       pasos=["Tramita CUIT y clave fiscal", "Ingresa a Monotributo", "Selecciona categoría",
              "Genera la credencial de pago"],
       costo_aprox="Cuota mensual según categoría", fuente="https://www.afip.gob.ar",
       keywords=["monotributo", "afip", "cuit", "argentina", "impuestos"]),
]


def get_tramite(tid: str) -> dict | None:
    return next((t for t in TRAMITES if t["id"] == tid), None)


def _score(t: dict, country: str | None, region: str | None, municipio: str | None, q: str | None) -> int:
    score = 0
    if municipio and t.get("municipio") and municipio.lower() == t["municipio"].lower():
        score += 5
    if region and t.get("region") and region.lower() == t["region"].lower():
        score += 3
    if not t.get("region") and not t.get("municipio"):
        score += 1  # national entries are broadly relevant
    if q:
        ql = q.lower()
        if ql in t["title"].lower():
            score += 3
        score += sum(1 for k in t.get("keywords", []) if k in ql or ql in k)
    return score


def find_tramites(country: str | None = None, region: str | None = None,
                  municipio: str | None = None, q: str | None = None, limit: int = 6) -> list[dict]:
    """Relevance-ranked curated trámites, scoped by country and locality."""
    items = TRAMITES
    if country:
        items = [t for t in items if t["country"].upper() == country.upper()]
    scored = sorted(items, key=lambda t: _score(t, country, region, municipio, q), reverse=True)
    if q or region or municipio:
        scored = [t for t in scored if _score(t, country, region, municipio, q) > 0]
    return scored[:limit]


def to_context(t: dict) -> str:
    """Compact grounding block for an LLM."""
    reqs = "; ".join(t.get("requisitos", []))
    pasos = " → ".join(t.get("pasos", []))
    loc = " / ".join(x for x in (t.get("municipio"), t.get("region"), t["country"]) if x)
    return (f"[{t['title']} — {loc}] Autoridad: {t.get('authority', '')}. "
            f"Requisitos: {reqs}. Pasos: {pasos}. Costo: {t.get('costo_aprox', '')}. "
            f"Vigencia: {t.get('vigencia', 'N/D')}. Fuente: {t.get('fuente', '')}.")
