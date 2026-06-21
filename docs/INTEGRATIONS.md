# Integraciones (CRM / ERP / Delivery)

Dos direcciones:

## 1) Entrada — API pública `/v1` (otros sistemas llaman a MaestroAI)
Auth por **API key** (header `X-API-Key`). Genera llaves en *Admin → Integraciones*.
- `GET  /v1/ping` — verifica la llave.
- `POST /v1/cases/{recipe_id}/run` `{ "inputs": {...} }` — ejecuta un caso de uso.
- `GET  /v1/tramites?q=&region=&municipio=` — consulta el MCP de trámites.
- `POST /v1/events` `{ "event": "document_uploaded", "payload": {...} }` — dispara automatizaciones.

```bash
curl -H "X-API-Key: mai_..." https://<api>/v1/ping
```

## 2) Salida — Conectores (MaestroAI envía datos a tus sistemas)
En *Admin → Integraciones* registra un conector (CRM/ERP/Delivery/Custom) con su
`base_url` y token. Una automatización con acción **connector** hace POST del
payload a ese endpoint. Botón "Probar" para validar.

## Automatizaciones (disparador → acción)
- Disparadores: **manual**, **programada** (daily/weekly/monthly), **por evento**
  (`document_uploaded`).
- Acciones: **workflow** (n8n), **caso de uso** (IA + MCP), **conector**, **notificar**.
- Programadas: el scheduler interno (`SCHEDULER_ENABLED=true`) o un cron externo
  llamando `POST /automations/run-due?frequency=daily`.
