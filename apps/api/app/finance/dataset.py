"""Carga del dataset financiero — **solo inyectado**, nunca con datos reales en el repo.

Orden de resolución (el primero que exista gana):

1. ``FINANCE_DATASET_JSON``  — el JSON completo en la variable de entorno.
2. ``FINANCE_DATASET_PATH``  — ruta a un archivo JSON (p. ej. un *Secret File* de Render).
3. ``dataset.local.json``    — archivo local junto a este módulo (git-ignored, para dev).
4. ``demo_dataset.json``     — **fallback sintético** versionado en el repo (sin datos reales).

Así los números reales del cliente viven solo en el entorno/secret (Paso 1 = conector),
y el repositorio solo contiene datos de demostración. El contrato (las llaves del JSON) es
el mismo en demo y en real, de modo que el tablero no cambia.
"""
from __future__ import annotations

import json
import os
from functools import lru_cache
from pathlib import Path

_DIR = Path(__file__).resolve().parent


def _source() -> tuple[str, str]:
    raw = os.getenv("FINANCE_DATASET_JSON")
    if raw and raw.strip():
        return raw, "env:FINANCE_DATASET_JSON"
    path = os.getenv("FINANCE_DATASET_PATH")
    if path and Path(path).is_file():
        return Path(path).read_text(encoding="utf-8"), f"file:{path}"
    local = _DIR / "dataset.local.json"
    if local.is_file():
        return local.read_text(encoding="utf-8"), "file:dataset.local.json"
    return (_DIR / "demo_dataset.json").read_text(encoding="utf-8"), "demo"


@lru_cache(maxsize=1)
def load() -> dict:
    raw, origin = _source()
    data = json.loads(raw)
    data["_origin"] = origin
    data["_is_demo"] = origin == "demo"
    return data


def is_demo() -> bool:
    return bool(load().get("_is_demo"))
