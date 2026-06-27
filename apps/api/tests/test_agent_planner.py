"""Planner agéntico: encadenamiento de pasos y validación de herramientas."""
from __future__ import annotations

from app.ai.agent_planner import _validate, build_tools, plan_steps, resolve_refs

ACTIONS = [
    {"id": "gmail.send", "provider": "google", "label": "Enviar correo", "write": True, "params": ["to", "subject", "body"]},
    {"id": "sharepoint.search", "provider": "microsoft", "label": "Buscar SharePoint", "write": False, "params": ["query"]},
]
WORKFLOWS = [{"id": "ingesta", "name": "Ingesta documental", "steps": "Upload → ..."}]


def test_resolve_refs_chains_outputs():
    params = {"body": "Resumen: {{step1}}", "subject": "x"}
    out = resolve_refs(params, {1: "hola mundo"})
    assert out["body"] == "Resumen: hola mundo" and out["subject"] == "x"


def test_resolve_refs_keeps_unknown_ref():
    out = resolve_refs({"body": "{{step5}}"}, {1: "a"})
    assert out["body"] == "{{step5}}"


def test_validate_accepts_workflow_and_filters_params():
    steps = [
        {"action": "workflow:ingesta", "params": {"payload": "x", "ajeno": 1}, "reason": "r"},
        {"action": "gmail.send", "params": {"to": "a@b.com", "hack": "no"}},
        {"action": "no.existe", "params": {}},
    ]
    out = _validate(steps, ACTIONS, WORKFLOWS)
    assert [s["action"] for s in out] == ["workflow:ingesta", "gmail.send"]
    assert out[0]["params"] == {"payload": "x"}
    assert out[1]["params"] == {"to": "a@b.com"}


def test_plan_heuristic_matches_workflow_and_action():
    plan = plan_steps("haz la ingesta documental y busca en sharepoint", ACTIONS, workflows=WORKFLOWS)
    ids = {s["action"] for s in plan["steps"]}
    assert "workflow:ingesta" in ids and "sharepoint.search" in ids
    assert plan["source"] == "heurística"


def test_build_tools_sanitizes_names_and_maps_back():
    tools, name_map = build_tools(ACTIONS, WORKFLOWS)
    names = {t["function"]["name"] for t in tools}
    assert "gmail_send" in names and "sharepoint_search" in names and "workflow_ingesta" in names
    # El mapa devuelve el id real (con punto/dos puntos).
    assert name_map["gmail_send"] == "gmail.send"
    assert name_map["workflow_ingesta"] == "workflow:ingesta"
    # Sin puntos ni dos puntos en los nombres de function.
    assert all("." not in n and ":" not in n for n in names)


class _ToolAdapter:
    """Adaptador falso con function-calling: simula que qwen3.6 invoca tools."""
    model_name = "qwen3.6"

    def __init__(self, calls):
        self._calls = calls

    def generate_tools(self, system, prompt, tools):
        return self._calls


def test_plan_uses_tool_calls_with_chaining():
    adapter = _ToolAdapter([
        {"name": "sharepoint_search", "arguments": {"query": "contrato"}},
        {"name": "gmail_send", "arguments": {"to": "a@b.com", "subject": "Resumen", "body": "{{step1}}"}},
    ])
    plan = plan_steps("busca el contrato y manda un correo", ACTIONS, adapter=adapter, workflows=WORKFLOWS)
    assert plan["source"] == "modelo (tools)"
    ids = [s["action"] for s in plan["steps"]]
    assert ids == ["sharepoint.search", "gmail.send"]
    # La referencia de encadenamiento se conserva en los params (se resuelve al ejecutar).
    assert plan["steps"][1]["params"]["body"] == "{{step1}}"


def test_plan_tool_calls_empty_falls_back_to_heuristic():
    adapter = _ToolAdapter([])   # el modelo no invocó ninguna tool
    plan = plan_steps("busca en sharepoint", ACTIONS, adapter=adapter, workflows=WORKFLOWS)
    assert plan["source"] == "heurística"
    assert any(s["action"] == "sharepoint.search" for s in plan["steps"])
