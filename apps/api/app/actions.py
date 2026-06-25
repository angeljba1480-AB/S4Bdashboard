"""Google Workspace / Microsoft 365 action toolkit (catalog).

Read actions run immediately; write actions are gated on human approval. Each
action declares the provider, whether it writes, and its parameters. Execution
lives in integrations/actions_exec.py.
"""
from __future__ import annotations

# id -> metadata
ACTIONS: dict[str, dict] = {
    # --- Google ---
    "gmail.send": {"provider": "google", "label": "Enviar correo (Gmail)", "write": True,
                   "params": ["to", "subject", "body"]},
    "gcal.create_event": {"provider": "google", "label": "Crear evento (Google Calendar)", "write": True,
                          "params": ["summary", "start", "end", "location"]},
    "gsheets.append": {"provider": "google", "label": "Agregar fila a Google Sheets", "write": True,
                       "params": ["spreadsheet_id", "range", "values"]},
    # --- Google (lectura) ---
    "gsheets.read": {"provider": "google", "label": "Leer Google Sheets", "write": False,
                     "params": ["spreadsheet_id", "range"]},
    "gcal.list": {"provider": "google", "label": "Próximos eventos (Google Calendar)", "write": False,
                  "params": ["days"]},
    # --- Microsoft 365 ---
    "outlook.send": {"provider": "microsoft", "label": "Enviar correo (Outlook)", "write": True,
                     "params": ["to", "subject", "body"]},
    "mscal.create_event": {"provider": "microsoft", "label": "Crear evento (Outlook Calendar)", "write": True,
                           "params": ["summary", "start", "end", "location"]},
    "teams.post": {"provider": "microsoft", "label": "Publicar en Teams (canal)", "write": True,
                   "params": ["team_id", "channel_id", "message"]},
    # --- Microsoft 365 (lectura) ---
    "mscal.list": {"provider": "microsoft", "label": "Próximos eventos (Outlook Calendar)", "write": False,
                   "params": ["days"]},
    "onedrive.list": {"provider": "microsoft", "label": "Listar archivos (OneDrive)", "write": False,
                      "params": ["query"]},
}


def list_actions() -> list[dict]:
    return [{"id": k, **v} for k, v in ACTIONS.items()]


def get_action(action_id: str) -> dict | None:
    a = ACTIONS.get(action_id)
    return {"id": action_id, **a} if a else None
