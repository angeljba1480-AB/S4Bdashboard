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

    # ===== México — nacional (más) =====
    _t(id="mx_imss_patron", country="MX", scope="nacional", category="bienestar", eje="bienestar",
       title="Alta patronal e inscripción de trabajadores (IMSS)",
       authority="Instituto Mexicano del Seguro Social (IMSS)",
       requisitos=["RFC con e.firma", "Identificación del patrón", "Comprobante de domicilio",
                   "Datos de los trabajadores (CURP/NSS)"],
       pasos=["Regístrate en IDSE/Escritorio Virtual", "Da de alta el registro patronal",
              "Inscribe a cada trabajador", "Calcula y paga cuotas (SUA)"],
       costo_aprox="Cuotas obrero-patronales", fuente="https://www.imss.gob.mx",
       keywords=["imss", "alta patronal", "trabajadores", "nss", "cuotas", "empleados"]),
    _t(id="mx_impi_marca", country="MX", scope="nacional", category="cumplimiento", eje="economia",
       title="Registro de marca (IMPI)",
       authority="Instituto Mexicano de la Propiedad Industrial (IMPI)",
       requisitos=["Denominación o logo", "Productos/servicios (clasificación Niza)",
                   "Datos del solicitante", "Pago de derechos"],
       pasos=["Búsqueda fonética en MARCANET", "Presenta solicitud en MARCA en línea",
              "Paga derechos", "Atiende oficios", "Obtén el título de registro"],
       costo_aprox="~$2,400 MXN por clase", vigencia="10 años (renovable)",
       fuente="https://www.gob.mx/impi", keywords=["marca", "impi", "registro", "propiedad industrial", "logo"]),

    # ===== México — estatal / municipal (más) =====
    _t(id="mx_nl_mty_licencia", country="MX", scope="municipal", region="Nuevo León", municipio="Monterrey",
       category="abrir", eje="economia",
       title="Licencia / anuencia de funcionamiento — Monterrey",
       authority="Municipio de Monterrey",
       requisitos=["Uso de suelo", "Identificación", "Comprobante de domicilio del local",
                   "Dictamen de Protección Civil (según giro)"],
       pasos=["Verifica factibilidad de uso de suelo", "Ingresa solicitud", "Paga derechos",
              "Recibe anuencia/licencia"],
       costo_aprox="Variable por giro/superficie", vigencia="Anual",
       fuente="https://www.monterrey.gob.mx", keywords=["licencia", "monterrey", "nuevo león", "anuencia"]),
    _t(id="mx_jal_sare", country="MX", scope="estatal", region="Jalisco",
       category="abrir", eje="economia",
       title="Apertura rápida de empresas (SARE) — Jalisco",
       authority="Gobierno de Jalisco / municipios",
       requisitos=["Giro de bajo riesgo", "Uso de suelo compatible", "Identificación"],
       pasos=["Verifica si tu giro es de bajo riesgo", "Tramita por SARE/ventanilla única",
              "Obtén licencia en plazo reducido"],
       costo_aprox="Reducido (giros de bajo riesgo)", fuente="https://www.jalisco.gob.mx",
       keywords=["sare", "apertura rápida", "jalisco", "bajo riesgo", "licencia"]),

    # ===== Colombia (más) =====
    _t(id="co_bog_uso_suelo", country="CO", scope="municipal", region="Bogotá D.C.",
       category="abrir", eje="servicios",
       title="Concepto de uso de suelo — Bogotá",
       authority="Secretaría Distrital de Planeación, Bogotá",
       requisitos=["Dirección y CHIP del predio", "Actividad económica (CIIU)"],
       pasos=["Consulta norma urbana (POT)", "Solicita concepto de uso", "Verifica compatibilidad del CIIU"],
       costo_aprox="Gratuito (consulta)", fuente="https://www.sdp.gov.co",
       keywords=["uso de suelo", "bogotá", "pot", "ciiu", "planeación"]),

    # ===== Chile =====
    _t(id="cl_inicio_actividades", country="CL", scope="nacional", category="cumplimiento", eje="economia",
       title="Inicio de actividades (SII)",
       authority="Servicio de Impuestos Internos (SII)",
       requisitos=["RUT/ClaveÚnica", "Actividad económica", "Domicilio"],
       pasos=["Ingresa a sii.cl", "Declara inicio de actividades", "Selecciona giro/código",
              "Habilita boletas/facturas electrónicas"],
       costo_aprox="Gratuito", fuente="https://www.sii.cl",
       keywords=["sii", "inicio de actividades", "chile", "rut", "boleta"]),
    _t(id="cl_patente_municipal", country="CL", scope="municipal", category="abrir", eje="economia",
       title="Patente comercial municipal — Chile",
       authority="Municipalidad correspondiente",
       requisitos=["Inicio de actividades en SII", "Domicilio comercial", "Recepción definitiva del local"],
       pasos=["Reúne requisitos", "Solicita patente en la municipalidad", "Paga la patente (semestral)"],
       costo_aprox="% del capital propio (tope legal)", vigencia="Semestral",
       fuente="", keywords=["patente", "municipal", "chile", "comercial"]),

    # ===== Perú =====
    _t(id="pe_ruc_sunat", country="PE", scope="nacional", category="cumplimiento", eje="economia",
       title="Inscripción al RUC (SUNAT)",
       authority="SUNAT",
       requisitos=["DNI", "Comprobante de domicilio", "Actividad económica"],
       pasos=["Ingresa a SUNAT con Clave SOL", "Inscribe el RUC", "Elige régimen (NRUS/RER/RMT)",
              "Emite comprobantes electrónicos"],
       costo_aprox="Gratuito", fuente="https://www.sunat.gob.pe",
       keywords=["ruc", "sunat", "perú", "clave sol", "régimen"]),
    _t(id="pe_licencia_funcionamiento", country="PE", scope="municipal", category="abrir", eje="economia",
       title="Licencia de funcionamiento municipal — Perú",
       authority="Municipalidad distrital",
       requisitos=["RUC", "Zonificación compatible", "Inspección de Defensa Civil (ITSE)"],
       pasos=["Verifica zonificación", "Presenta solicitud y declaración jurada", "ITSE según riesgo",
              "Obtén la licencia"],
       costo_aprox="Según tasa municipal", fuente="",
       keywords=["licencia de funcionamiento", "perú", "itse", "defensa civil", "municipal"]),
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
    if t.get("text"):  # RAG snippet from the company's own documents
        loc = t.get("title", "Documento de la empresa")
        return f"[{loc} — documento empresa] {t['text'][:400]}"
    reqs = "; ".join(t.get("requisitos", []))
    pasos = " → ".join(t.get("pasos", []))
    loc = " / ".join(x for x in (t.get("municipio"), t.get("region"), t["country"]) if x)
    return (f"[{t['title']} — {loc}] Autoridad: {t.get('authority', '')}. "
            f"Requisitos: {reqs}. Pasos: {pasos}. Costo: {t.get('costo_aprox', '')}. "
            f"Vigencia: {t.get('vigencia', 'N/D')}. Fuente: {t.get('fuente', '')}.")
