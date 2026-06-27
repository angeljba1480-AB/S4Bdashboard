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

# Pistas de intención → id de workflow n8n del catálogo.
_WF_INTENTS: list[tuple[tuple[str, ...], str]] = [
    (("ingesta", "ingestar", "indexa", "indexar"), "ingesta"),
    (("sow", "propuesta", "cotización", "cotizacion"), "sow"),
    (("cyber", "ciber", "ciberseguridad", "diagnóstico", "diagnostico"), "cyber"),
    (("centro de mando", "kpi", "tablero", "indicadores"), "mando"),
    (("fine-tuning", "fine tuning", "entrena", "entrenar"), "finetune"),
]


def _match_actions(instruction: str, actions: list[dict], workflows: list[dict] | None = None) -> list[dict]:
    """Heurística: devuelve pasos candidatos {action, params, reason} para las
    acciones/workflows permitidos cuyo patrón aparece en la instrucción."""
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
    wf_ids = {w["id"] for w in (workflows or [])}
    for keywords, wid in _WF_INTENTS:
        if wid in wf_ids and any(k in low for k in keywords):
            aid = f"workflow:{wid}"
            if aid not in used:
                steps.append({"action": aid, "params": {},
                              "reason": f"Dispara el workflow «{wid}» ({keywords[0]})."})
                used.add(aid)
    return steps


_REF_RE = re.compile(r"\{\{\s*step(\d+)(?:\.result)?\s*\}\}", re.IGNORECASE)


def resolve_refs(params: dict, outputs: dict) -> dict:
    """Sustituye referencias {{stepN}} / {{stepN.result}} en los params por la
    salida (1-based) de pasos previos ya ejecutados. Habilita el encadenamiento:
    la salida de un paso alimenta al siguiente."""
    out = {}
    for k, v in (params or {}).items():
        if isinstance(v, str):
            v = _REF_RE.sub(lambda m: str(outputs.get(int(m.group(1)), m.group(0))), v)
        out[k] = v
    return out


_TOOLS_SYSTEM = (
    "Eres un planificador de acciones. Usa SOLO las herramientas (functions) disponibles "
    "para cumplir la instrucción del usuario, en orden lógico. Para ENCADENAR, pon "
    "\"{{stepN}}\" (N = número de paso previo, 1-based) en el valor de un argumento y así "
    "usar la salida de ese paso. Llama únicamente a las herramientas necesarias; no "
    "inventes argumentos que no conozcas."
)


def _sanitize_name(action_id: str) -> str:
    """Los nombres de function deben casar `^[a-zA-Z0-9_-]+$` (máx 64). Los ids de
    acción traen `.`/`:` (gmail.send, workflow:ingesta) → se normalizan a `_`."""
    return re.sub(r"[^a-zA-Z0-9_-]", "_", action_id)[:64]


def build_tools(actions: list[dict], workflows: list[dict] | None = None) -> tuple[list[dict], dict]:
    """Construye el arreglo `tools` (function calling OpenAI) y el mapa nombre→id."""
    tools: list[dict] = []
    name_map: dict[str, str] = {}
    for a in actions:
        nm = _sanitize_name(a["id"])
        name_map[nm] = a["id"]
        props = {p: {"type": "string"} for p in a.get("params", [])}
        kind = "escritura" if a.get("write") else "lectura"
        tools.append({"type": "function", "function": {
            "name": nm,
            "description": f'{a.get("label", a["id"])} ({kind}, {a.get("provider", "")})',
            "parameters": {"type": "object", "properties": props, "required": []},
        }})
    for w in (workflows or []):
        aid = f'workflow:{w["id"]}'
        nm = _sanitize_name(aid)
        name_map[nm] = aid
        tools.append({"type": "function", "function": {
            "name": nm,
            "description": f'Workflow n8n: {w.get("name", w["id"])}. {w.get("steps", "")}'[:300],
            "parameters": {"type": "object",
                           "properties": {"payload": {"type": "string", "description": "Contexto opcional"}},
                           "required": []},
        }})
    return tools, name_map


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


def _validate(steps: list, actions: list[dict], workflows: list[dict] | None = None) -> list[dict]:
    """Filtra a pasos válidos: action en el catálogo permitido (acción o
    workflow:<id>) y params dict (conserva referencias {{stepN}})."""
    by_id = {a["id"]: a for a in actions}
    wf_ids = {w["id"] for w in (workflows or [])}
    out: list[dict] = []
    for s in steps:
        if not isinstance(s, dict):
            continue
        aid = str(s.get("action", "")).strip()
        params = s.get("params") if isinstance(s.get("params"), dict) else {}
        if aid.startswith("workflow:"):
            if aid.split(":", 1)[1] not in wf_ids:
                continue
            params = {"payload": params.get("payload")} if "payload" in params else {}
        elif aid in by_id:
            allowed = set(by_id[aid].get("params", []))
            params = {k: v for k, v in params.items() if k in allowed}
        else:
            continue
        out.append({"action": aid, "params": params,
                    "reason": str(s.get("reason", ""))[:200]})
    return out


def plan_steps(instruction: str, actions: list[dict], adapter=None,
               workflows: list[dict] | None = None) -> dict:
    """Devuelve {steps: [...], source: "modelo"|"heurística", note}. `actions` es el
    catálogo YA filtrado a lo que el usuario puede ejecutar (proveedor conectado);
    `workflows` son los workflows n8n disponibles (acción `workflow:<id>`). Los pasos
    pueden encadenarse con referencias {{stepN}} a la salida de pasos previos."""
    instruction = (instruction or "").strip()
    workflows = workflows or []
    if not instruction or (not actions and not workflows):
        return {"steps": [], "source": "ninguna",
                "note": "Sin instrucción o sin herramientas disponibles (conecta un proveedor)."}

    # 1) Function-calling nativo (proveedor real con tools, p. ej. qwen3.6 de NaN).
    if adapter is not None and hasattr(adapter, "generate_tools"):
        try:  # pragma: no cover - depende de modelo real
            tools, name_map = build_tools(actions, workflows)
            calls = adapter.generate_tools(_TOOLS_SYSTEM, instruction, tools)
            raw = [{"action": name_map.get(c.get("name", "")), "params": c.get("arguments", {}),
                    "reason": ""} for c in (calls or []) if name_map.get(c.get("name", ""))]
            steps = _validate(raw, actions, workflows)
            if steps:
                return {"steps": steps, "source": "modelo (tools)", "note": ""}
        except Exception:
            pass  # cae a texto-JSON o heurística

    # 2) Camino del modelo por texto-JSON (proveedor real sin tools).
    if adapter is not None and getattr(adapter, "model_name", "mock").startswith("mock") is False:
        wf_text = "\n".join(f'- "workflow:{w["id"]}" ({w.get("name")}): {w.get("steps", "")}' for w in workflows)
        system = (
            "Eres un planificador de acciones. Convierte la instrucción del usuario en "
            "una lista ORDENADA de pasos usando SOLO las herramientas permitidas. Responde "
            "ÚNICAMENTE con un arreglo JSON: [{\"action\": id, \"params\": {...}, \"reason\": texto}]. "
            "Puedes ENCADENAR: para usar la salida de un paso previo en otro, pon "
            "\"{{stepN}}\" (N es el número de paso, 1-based) en el valor del parámetro. "
            "No inventes herramientas ni parámetros fuera de los declarados. Si falta un dato "
            "para una escritura, incluye el paso con los params que tengas (se pedirá "
            "aprobación). No incluyas nada más que el JSON.\n\n"
            f"Acciones permitidas:\n{_allowed_catalog_text(actions)}\n\n"
            f"Workflows n8n permitidos (úsalos como action \"workflow:<id>\", param opcional \"payload\"):\n{wf_text or '(ninguno)'}"
        )
        try:  # pragma: no cover - depende de modelo real
            resp = adapter.generate(system, instruction, [])
            parsed = _extract_json_array(resp.content)
            if parsed is not None:
                steps = _validate(parsed, actions, workflows)
                if steps:
                    return {"steps": steps, "source": "modelo", "note": ""}
        except Exception:
            pass  # cae a heurística

    # 2) Heurística determinista (laboratorio / sin modelo).
    steps = _match_actions(instruction, actions, workflows)
    note = "" if steps else "No se identificó ninguna acción para esa instrucción."
    return {"steps": steps, "source": "heurística", "note": note}
