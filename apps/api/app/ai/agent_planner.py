"""Planner agéntico: traduce una instrucción en lenguaje natural a una secuencia
de **pasos del toolkit** (acciones Google/Microsoft) que el modelo ejecuta «por
detrás» — comandos/clics automatizados — respetando la gobernanza existente
(lecturas al vuelo; escrituras con aprobación humana o «Permitir siempre»).

Estrategia:
1. Si hay un modelo real configurado, se le pide un **plan JSON** restringido al
   catálogo de acciones permitidas (las del proveedor conectado).
2. Si no hay modelo (modo laboratorio/mock) o el JSON no es válido, cae a un
   **emparejador heurístico** por intención (palabras clave en español).

El planner NO ejecuta nada: solo decide los pasos. La ejecución y la aprobación
viven en el router /actions, que ya audita todo.
"""
from __future__ import annotations

import json
import re

# Pistas de intención (palabra clave → fragmento de id de acción). El emparejador
# elige solo entre las acciones permitidas (las que llegan en `actions`).
_INTENTS: list[tuple[tuple[str, ...], str]] = [
    (("envía", "envia", "enviar", "manda", "mandar", "correo", "email", "mail"), ".send"),
    (("evento", "reunión", "reunion", "junta", "cita", "agenda una", "agendar"), ".create_event"),
    (("teams", "canal"), "teams.post"),
    (("agrega", "añade", "anade", "registra", "fila"), ".append"),
    (("lee", "leer", "muéstrame", "muestrame", "consulta"), ".read"),
    (("próximos", "proximos", "qué tengo", "que tengo", "calendario", "agenda"), ".list"),
    (("onedrive", "archivos", "documentos"), "onedrive.list"),
    (("sharepoint",), "sharepoint.search"),
]


def _match_actions(instruction: str, actions: list[dict]) -> list[dict]:
    """Heurística: devuelve pasos candidatos {action, params, reason} para las
    acciones permitidas cuyo patrón aparece en la instrucción."""
    low = instruction.lower()
    ids = {a["id"] for a in actions}
    steps: list[dict] = []
    used: set[str] = set()
    for keywords, frag in _INTENTS:
        if not any(k in low for k in keywords):
            continue
        for aid in ids:
            if aid in used:
                continue
            if (frag.startswith(".") and aid.endswith(frag)) or aid == frag:
                steps.append({"action": aid, "params": {},
                              "reason": f"Coincide con la intención «{keywords[0]}»."})
                used.add(aid)
    return steps


def _allowed_catalog_text(actions: list[dict]) -> str:
    lines = []
    for a in actions:
        params = ", ".join(a.get("params", []))
        kind = "escritura" if a.get("write") else "lectura"
        lines.append(f'- "{a["id"]}" ({kind}, {a.get("provider")}): {a.get("label")}. Params: [{params}]')
    return "\n".join(lines)


def _extract_json_array(text: str) -> list | None:
    """Extrae el primer arreglo JSON del texto del modelo (tolerante a prosa/```)."""
    if not text:
        return None
    m = re.search(r"\[.*\]", text, re.DOTALL)
    if not m:
        return None
    try:
        data = json.loads(m.group(0))
        return data if isinstance(data, list) else None
    except (ValueError, TypeError):
        return None


def _validate(steps: list, actions: list[dict]) -> list[dict]:
    """Filtra a pasos válidos: action en el catálogo permitido y params dict."""
    by_id = {a["id"]: a for a in actions}
    out: list[dict] = []
    for s in steps:
        if not isinstance(s, dict):
            continue
        aid = str(s.get("action", "")).strip()
        if aid not in by_id:
            continue
        params = s.get("params") if isinstance(s.get("params"), dict) else {}
        # Solo conserva params declarados por la acción.
        allowed = set(by_id[aid].get("params", []))
        params = {k: v for k, v in params.items() if k in allowed}
        out.append({"action": aid, "params": params,
                    "reason": str(s.get("reason", ""))[:200]})
    return out


def plan_steps(instruction: str, actions: list[dict], adapter=None) -> dict:
    """Devuelve {steps: [...], source: "modelo"|"heurística", note}. `actions` es el
    catálogo YA filtrado a lo que el usuario puede ejecutar (proveedor conectado)."""
    instruction = (instruction or "").strip()
    if not instruction or not actions:
        return {"steps": [], "source": "ninguna",
                "note": "Sin instrucción o sin acciones disponibles (conecta un proveedor)."}

    # 1) Camino del modelo (si hay adapter real).
    if adapter is not None and getattr(adapter, "model_name", "mock").startswith("mock") is False:
        system = (
            "Eres un planificador de acciones. Convierte la instrucción del usuario en "
            "una lista de pasos usando SOLO las acciones permitidas. Responde ÚNICAMENTE "
            "con un arreglo JSON: [{\"action\": id, \"params\": {...}, \"reason\": texto}]. "
            "No inventes acciones ni parámetros fuera de los declarados. Si falta un dato "
            "para una escritura, incluye el paso con los params que tengas (se pedirá "
            "aprobación). No incluyas nada más que el JSON.\n\n"
            f"Acciones permitidas:\n{_allowed_catalog_text(actions)}"
        )
        try:  # pragma: no cover - depende de modelo real
            resp = adapter.generate(system, instruction, [])
            parsed = _extract_json_array(resp.content)
            if parsed is not None:
                steps = _validate(parsed, actions)
                if steps:
                    return {"steps": steps, "source": "modelo", "note": ""}
        except Exception:
            pass  # cae a heurística

    # 2) Heurística determinista (laboratorio / sin modelo).
    steps = _match_actions(instruction, actions)
    note = "" if steps else "No se identificó ninguna acción para esa instrucción."
    return {"steps": steps, "source": "heurística", "note": note}
