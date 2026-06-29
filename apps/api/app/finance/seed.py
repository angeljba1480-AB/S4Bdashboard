"""Acceso al dataset del Tablero Financiero.

Antes esto contenía los números reales en código. Ahora **todos los datos vienen
inyectados** (ver ``dataset.py``): variable de entorno o *secret file* en prod, y un
``demo_dataset.json`` sintético versionado como fallback. El repositorio no guarda
datos reales del cliente.

Las constantes de módulo se mantienen por compatibilidad con el router, pero se
resuelven desde el dataset cargado; ``reload()`` permite refrescar en runtime.
"""
from __future__ import annotations

from . import dataset

_D = dataset.load()

COMPANY = _D["company"]
HEADCOUNT = _D["headcount"]
FY = _D["fy"]
FY_2024 = _D["fy_2024"]
MONTHLY = _D["monthly"]
SEGMENTS = _D["segments"]
GOB_IP = _D["gob_ip"]
BENCHMARKS = _D["benchmarks"]
ALERTS = _D["alerts"]
TOP_CLIENTS = _D["top_clients"]


def projects() -> dict:
    """Portafolio de proyectos (totales, tendencia, mezcla de costo, clientes, detalle)."""
    return dataset.load().get("projects", {})


def utilization() -> dict:
    """Utilización del equipo (timesheet real vs capacidad)."""
    return dataset.load().get("utilization", {})


def cost_per_hour() -> dict:
    """Costo por hora por rol (derivado de Concentrado BC)."""
    return dataset.load().get("cost_per_hour", {})


def client_scoring() -> dict:
    """Evaluación/score de clientes (modelo ponderado del equipo)."""
    return dataset.load().get("client_scoring", {})


def is_demo() -> bool:
    return dataset.is_demo()


def entity_kpis(entity: str) -> dict:
    d = FY.get(entity, FY["CONS"])
    prev = FY_2024.get(entity, FY_2024["CONS"])
    growth = (d["revenue"] / prev["revenue"] - 1) if prev.get("revenue") else 0.0
    return {**d, "growth": growth}
