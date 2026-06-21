"""LATAM countries + their first-level administrative divisions.

The platform starts with Mexico context but is multi-country. Region-aware
recipes use a generic "region" field that this module localizes to each
country's division label (Estado / Provincia / Departamento / Región) and its
list of divisions. Countries without a seeded list fall back to free text.
"""
from __future__ import annotations

DEFAULT = "MX"

_MX = ["Aguascalientes", "Baja California", "Baja California Sur", "Campeche",
       "Chiapas", "Chihuahua", "Ciudad de México", "Coahuila", "Colima", "Durango",
       "Estado de México", "Guanajuato", "Guerrero", "Hidalgo", "Jalisco",
       "Michoacán", "Morelos", "Nayarit", "Nuevo León", "Oaxaca", "Puebla",
       "Querétaro", "Quintana Roo", "San Luis Potosí", "Sinaloa", "Sonora",
       "Tabasco", "Tamaulipas", "Tlaxcala", "Veracruz", "Yucatán", "Zacatecas"]

_AR = ["Buenos Aires", "CABA", "Catamarca", "Chaco", "Chubut", "Córdoba",
       "Corrientes", "Entre Ríos", "Formosa", "Jujuy", "La Pampa", "La Rioja",
       "Mendoza", "Misiones", "Neuquén", "Río Negro", "Salta", "San Juan",
       "San Luis", "Santa Cruz", "Santa Fe", "Santiago del Estero",
       "Tierra del Fuego", "Tucumán"]

_CL = ["Arica y Parinacota", "Tarapacá", "Antofagasta", "Atacama", "Coquimbo",
       "Valparaíso", "Metropolitana de Santiago", "O'Higgins", "Maule", "Ñuble",
       "Biobío", "La Araucanía", "Los Ríos", "Los Lagos", "Aysén", "Magallanes"]

_CO = ["Amazonas", "Antioquia", "Arauca", "Atlántico", "Bogotá D.C.", "Bolívar",
       "Boyacá", "Caldas", "Caquetá", "Casanare", "Cauca", "Cesar", "Chocó",
       "Córdoba", "Cundinamarca", "Guainía", "Guaviare", "Huila", "La Guajira",
       "Magdalena", "Meta", "Nariño", "Norte de Santander", "Putumayo", "Quindío",
       "Risaralda", "Santander", "Sucre", "Tolima", "Valle del Cauca", "Vaupés", "Vichada"]

_PE = ["Amazonas", "Áncash", "Apurímac", "Arequipa", "Ayacucho", "Cajamarca",
       "Callao", "Cusco", "Huancavelica", "Huánuco", "Ica", "Junín", "La Libertad",
       "Lambayeque", "Lima", "Loreto", "Madre de Dios", "Moquegua", "Pasco",
       "Piura", "Puno", "San Martín", "Tacna", "Tumbes", "Ucayali"]

COUNTRIES: list[dict] = [
    {"code": "MX", "name": "México", "division_label": "Estado", "currency": "MXN", "divisions": _MX},
    {"code": "CO", "name": "Colombia", "division_label": "Departamento", "currency": "COP", "divisions": _CO},
    {"code": "AR", "name": "Argentina", "division_label": "Provincia", "currency": "ARS", "divisions": _AR},
    {"code": "CL", "name": "Chile", "division_label": "Región", "currency": "CLP", "divisions": _CL},
    {"code": "PE", "name": "Perú", "division_label": "Departamento", "currency": "PEN", "divisions": _PE},
    {"code": "GT", "name": "Guatemala", "division_label": "Departamento", "currency": "GTQ", "divisions": []},
    {"code": "EC", "name": "Ecuador", "division_label": "Provincia", "currency": "USD", "divisions": []},
    {"code": "BO", "name": "Bolivia", "division_label": "Departamento", "currency": "BOB", "divisions": []},
    {"code": "DO", "name": "República Dominicana", "division_label": "Provincia", "currency": "DOP", "divisions": []},
    {"code": "CR", "name": "Costa Rica", "division_label": "Provincia", "currency": "CRC", "divisions": []},
    {"code": "PA", "name": "Panamá", "division_label": "Provincia", "currency": "PAB", "divisions": []},
    {"code": "UY", "name": "Uruguay", "division_label": "Departamento", "currency": "UYU", "divisions": []},
    {"code": "PY", "name": "Paraguay", "division_label": "Departamento", "currency": "PYG", "divisions": []},
    {"code": "SV", "name": "El Salvador", "division_label": "Departamento", "currency": "USD", "divisions": []},
    {"code": "HN", "name": "Honduras", "division_label": "Departamento", "currency": "HNL", "divisions": []},
    {"code": "NI", "name": "Nicaragua", "division_label": "Departamento", "currency": "NIO", "divisions": []},
]

_BY_CODE = {c["code"]: c for c in COUNTRIES}


def get_country(code: str | None) -> dict:
    return _BY_CODE.get((code or DEFAULT).upper(), _BY_CODE[DEFAULT])


def localize_field(field: dict, country_code: str | None) -> dict:
    """Turn a generic {"type":"region"} input into a concrete field for a country."""
    if field.get("type") != "region":
        return field
    c = get_country(country_code)
    out = {**field, "label": c["division_label"]}
    if c["divisions"]:
        out["type"] = "choice"
        out["options"] = c["divisions"] + ["Otra"]
    else:
        out["type"] = "text"
    return out


def localize_inputs(inputs: list[dict], country_code: str | None) -> list[dict]:
    return [localize_field(f, country_code) for f in inputs]
