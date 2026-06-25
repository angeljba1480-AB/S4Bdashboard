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

## 3) Toolkit de acciones — Google Workspace / Microsoft 365
En *Acciones* la plataforma **ejecuta** tareas en tus herramientas (enviar correo,
crear eventos, append a Google Sheets / tabla de Excel, publicar en Teams) usando
el **OAuth del usuario**.
- **Lecturas** (sin aprobación): Google Sheets, Google/Outlook Calendar, OneDrive,
  leer rango de Excel, buscar en SharePoint.
- Las acciones de **escritura** requieren **aprobación humana**; con **“Permitir
  siempre”** se auto-aprueban a futuro (revocable).
- Endpoints: `GET /actions`, `POST /actions/run`, `GET /actions/requests`,
  `POST /actions/requests/{id}/approve?always=`, `/reject`, `GET/DELETE /actions/grants`.
- Setup de permisos/scopes: **[ACCIONES-ESCRITURA-SETUP.md](./ACCIONES-ESCRITURA-SETUP.md)**.

## 4) Google Drive como contexto
*Documentos → Importar de Google Drive*: lista y descarga archivos (Docs/Sheets/
Slides/texto) y los mete al pipeline de clasificación + índice RAG. Requiere el
scope `drive.readonly` (reconectar Google). Endpoints: `GET /drive/files`,
`POST /drive/import`.

## 5) Modelos externos (GPT / Claude / Llama)
*Admin → Modelos externos*: configura proveedores **premium** y **abierto**
(Base URL + modelo + API key cifrada). La **redacción de PII** se aplica antes de
cualquier salida. Soporta **cascada** (borrador con modelo abierto → refinar con
premium, con aprobación para contenido sensible). Usa **Probar conexión** para
verificar que el proveedor responde (llamada real mínima → latencia + muestra, o error).

## 6) Fuentes de datos legadas → RAG (`/datasources`)
*Integraciones → Fuentes de datos*. Dos vías para sistemas sin API:
- **Base de datos de solo lectura**: DSN (`postgresql://…`, `mysql://…`) + una
  consulta **SELECT**. Validado contra DML/CTE y esquemas no permitidos; corre en
  transacción de solo lectura. Endpoints: `POST /datasources`, `/{id}/test`,
  `/{id}/import`, `DELETE /{id}`.
- **Importar CSV**: pega el CSV exportado por el sistema (primera fila = encabezados,
  delimitador configurable). Endpoint: `POST /datasources/import-csv`.

Ambas clasifican el contenido (público/…/restringido + PII), lo cifran y lo indexan
en el RAG. Solo **ADMIN/DEVOPS**.

## 7) Sistemas a la medida sin API — recomendación
1. **n8n** (ya integrado): puente universal (REST/SOAP/DB/FTP/correo + 400 apps).
2. **Conector REST de salida** (sección 2) si exponen cualquier endpoint HTTP.
3. **Webhooks entrantes** firmados si el sistema empuja eventos.
4. Sin API: **BD de solo lectura** o **CSV** (sección 6), **adaptador delgado**
   (wrapper REST), o **correo-a-acción**. Regla: webhooks para *eventos*, REST para
   *comandos*, n8n para el resto.

## Automatizaciones (disparador → acción)
- Disparadores: **manual**, **programada** (daily/weekly/monthly), **por evento**
  (`document_uploaded`).
- Acciones: **workflow** (n8n), **caso de uso** (IA + MCP), **conector**, **notificar**.
- Programadas: el scheduler interno (`SCHEDULER_ENABLED=true`) o un cron externo
  llamando `POST /automations/run-due?frequency=daily`.
