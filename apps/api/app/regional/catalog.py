"""Regional catalog: procedures / problems faced by the population by estado,
organized by government development axes ("ejes de desarrollo").

This seeds the use-case engine: a procedure can be turned into a use-case
proposal (which an admin curates into a runnable recipe). Seed data is a
starter set, meant to be expanded and curated per region.
"""
from __future__ import annotations

# Government development axes — the lens the state uses to prioritize. Editable.
EJES: list[dict] = [
    {"id": "economia", "label": "Economía y empleo"},
    {"id": "bienestar", "label": "Bienestar social"},
    {"id": "seguridad", "label": "Seguridad y justicia"},
    {"id": "salud", "label": "Salud"},
    {"id": "educacion", "label": "Educación"},
    {"id": "servicios", "label": "Servicios e infraestructura"},
    {"id": "medio_ambiente", "label": "Medio ambiente"},
    {"id": "gobierno_digital", "label": "Gobierno digital"},
]


def _p(**kw) -> dict:
    kw.setdefault("estados", [])          # [] = aplica a nivel nacional
    kw.setdefault("category", "operaciones")
    kw.setdefault("suggested_recipe", "")
    return kw


# Starter set. `estados` empty = nationwide; otherwise especially relevant there.
PROCEDURES: list[dict] = [
    _p(id="abrir_negocio", eje="economia", category="abrir",
       title="Abrir un negocio formal",
       problem="No sé qué trámites necesito ni el orden para empezar a operar.",
       suggested_recipe="registro_tramites"),
    _p(id="licencia_municipal", eje="economia", category="abrir",
       title="Licencia de funcionamiento municipal",
       problem="Cada municipio pide cosas distintas y no sé los requisitos de aquí.",
       suggested_recipe="licencia_funcionamiento"),
    _p(id="uso_suelo", eje="servicios", category="abrir",
       title="Constancia de uso de suelo",
       problem="No sé si mi local puede tener mi giro según el uso de suelo.",
       suggested_recipe="uso_de_suelo"),
    _p(id="permiso_anuncio", eje="servicios", category="abrir",
       title="Permiso de anuncio / letrero",
       problem="Quiero poner mi letrero pero desconozco el permiso municipal.",
       suggested_recipe="permiso_anuncio"),
    _p(id="alta_sat", eje="economia", category="cumplimiento",
       title="Darse de alta en el SAT (RFC)",
       problem="Vendo pero no estoy dado de alta; no sé el régimen que me toca.",
       suggested_recipe="rfc_alta"),
    _p(id="impuestos_locales", eje="economia", category="cumplimiento",
       title="Impuestos estatales y municipales",
       problem="No sé qué impuestos locales debo pagar por mi negocio.",
       suggested_recipe="impuestos_locales"),
    _p(id="formalizar_empleados", eje="bienestar", category="cumplimiento",
       title="Registrar empleados (IMSS)",
       problem="Quiero dar de alta a mi personal pero no sé el proceso.",
       suggested_recipe=""),
    _p(id="apoyo_financiamiento", eje="economia", category="crecer",
       title="Buscar financiamiento / apoyos",
       problem="Necesito capital y no sé qué programas o créditos existen para mí.",
       suggested_recipe="plan_negocio"),
    _p(id="vender_en_linea", eje="economia", category="crecer",
       title="Empezar a vender en línea",
       problem="Quiero vender por internet/redes y no sé cómo empezar.",
       suggested_recipe="post_redes"),
    _p(id="cobranza", eje="economia", category="operaciones",
       title="Cobrar a clientes morosos",
       problem="Me deben y no sé cómo cobrar de forma efectiva y cordial.",
       suggested_recipe="recordatorio_cobranza"),
    _p(id="precios_justos", eje="economia", category="dia_a_dia",
       title="Saber a cuánto vender",
       problem="No sé poner precios y a veces pierdo dinero.",
       suggested_recipe="precio_venta"),
    _p(id="proteccion_consumidor", eje="seguridad", category="cumplimiento",
       title="Cumplir con PROFECO",
       problem="No sé qué políticas debo mostrar a mis clientes.",
       suggested_recipe="politica_devoluciones"),
    _p(id="datos_personales", eje="gobierno_digital", category="cumplimiento",
       title="Aviso de privacidad (datos personales)",
       problem="Recolecto datos de clientes y no tengo aviso de privacidad.",
       suggested_recipe="aviso_privacidad"),
    _p(id="tramite_salud", eje="salud", category="cumplimiento",
       title="Aviso de funcionamiento sanitario (COFEPRIS)",
       problem="Mi giro maneja alimentos/salud y desconozco el aviso sanitario.",
       suggested_recipe="reglamento_local"),
    _p(id="capacitacion", eje="educacion", category="crecer",
       title="Capacitar a mi equipo",
       problem="Quiero que mi personal aprenda pero no tengo material.",
       suggested_recipe="guion_ventas"),
    _p(id="residuos", eje="medio_ambiente", category="cumplimiento",
       title="Manejo de residuos del negocio",
       problem="No sé las reglas locales para mis residuos.",
       suggested_recipe="reglamento_local"),
]


def get_procedure(pid: str) -> dict | None:
    return next((p for p in PROCEDURES if p["id"] == pid), None)


def filter_procedures(estado: str | None = None, eje: str | None = None, q: str | None = None) -> list[dict]:
    items = PROCEDURES
    if eje:
        items = [p for p in items if p["eje"] == eje]
    if estado:
        items = [p for p in items if not p["estados"] or estado in p["estados"]]
    if q:
        ql = q.lower()
        items = [p for p in items if ql in p["title"].lower() or ql in p["problem"].lower()]
    return items
