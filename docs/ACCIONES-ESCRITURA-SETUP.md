# Guía: Acciones de escritura (Toolkit Google / Microsoft) — MaestroAI

> Habilita el **Toolkit de acciones** (menú **Acciones**) para que la plataforma
> **ejecute** tareas en tus herramientas: enviar correo, crear eventos, agregar
> filas a Google Sheets y publicar en Microsoft Teams.

## Cómo funciona
1. El usuario abre **Acciones**, elige una acción (ej. *Enviar correo*) y llena los datos.
2. Las acciones de **escritura** se crean como **solicitud pendiente** → requieren tu
   **aprobación** antes de ejecutarse (principio “tú apruebas” del blueprint).
3. Botón **“Aprobar y permitir siempre”**: autoriza esa acción para el futuro
   (auto-ejecuta sin volver a preguntar). Es **revocable** en la sección
   *“Permitidas siempre”*.
4. Toda acción queda **auditada** (Auditoría → evento `action`).

> Las acciones usan el **OAuth del propio usuario**. Como agregamos permisos
> nuevos (escritura), **cada usuario debe reconectar** su cuenta una vez para
> otorgarlos (ver “Reconectar” abajo).

---

## A) Microsoft 365 (Outlook / Calendar / Teams)

### 1. Permisos en Azure (Entra ID)
**portal.azure.com → tu app `MaestroAI` → API permissions → Add a permission →
Microsoft Graph → Delegated** y agrega:

| Permiso | Para qué |
|---|---|
| `Mail.Send` | Enviar correo (Outlook) |
| `Calendars.ReadWrite` | Crear eventos de calendario |
| `ChannelMessage.Send` | Publicar en un canal de Teams |
| `Files.ReadWrite.All` | OneDrive (listar) + Excel (leer rango / agregar fila a tabla) |
| `Sites.Read.All` | Buscar en SharePoint |

> Ya deberías tener de antes: `User.Read`, `Mail.Read`, `offline_access`.
> `Calendars.ReadWrite` reemplaza/incluye a `Calendars.Read`.
> `Files.ReadWrite.All` incluye lectura (cubre el listado de OneDrive existente).

(Opcional pero recomendado en cuentas de empresa) **Grant admin consent**.

### 2. Nada nuevo en Render
Las mismas variables `MICROSOFT_*` ya configuradas. Los scopes los pide la app
automáticamente (ya están en el código).

---

## B) Google Workspace (Gmail / Calendar / Sheets)

### 1. Habilita las APIs
**console.cloud.google.com → APIs y servicios → Biblioteca**, habilita:
- **Gmail API**, **Google Calendar API**, **Google Drive API**, **Google Sheets API**.

### 2. Scopes en la pantalla de consentimiento
**APIs y servicios → Pantalla de consentimiento de OAuth → Editar → Scopes**, agrega:

| Scope | Para qué |
|---|---|
| `.../auth/gmail.send` | Enviar correo (Gmail) |
| `.../auth/calendar.events` | Crear/leer eventos |
| `.../auth/spreadsheets` | Escribir en Google Sheets |
| `.../auth/gmail.readonly`, `.../auth/drive.readonly` | Lectura (resumen + contexto) |

> Si la app está en modo **Prueba**, asegúrate de tener tu correo en **Usuarios de prueba**.

### 3. Nada nuevo en Render
Las mismas variables `GOOGLE_*`. Los scopes ya están en el código.

---

## C) Reconectar (paso obligatorio una vez)
Como los permisos cambiaron, cada usuario debe **volver a autorizar**:

1. Portal → **Integraciones → Conectar correo**.
2. En Outlook/Gmail toca **Conectar** (o **Conectar otra cuenta**).
3. En la pantalla de Microsoft/Google **acepta los nuevos permisos** (verás envío de
   correo, calendario, etc.).
4. Listo: en **Acciones** las tarjetas del proveedor aparecen como **conectadas**.

---

## D) Catálogo de acciones disponible

| Acción | Proveedor | Parámetros |
|---|---|---|
| Enviar correo (Gmail) | Google | `to`, `subject`, `body` |
| Crear evento (Google Calendar) | Google | `summary`, `start`, `end`, `location` |
| Agregar fila a Google Sheets | Google | `spreadsheet_id`, `range`, `values` |
| Enviar correo (Outlook) | Microsoft | `to`, `subject`, `body` |
| Crear evento (Outlook Calendar) | Microsoft | `summary`, `start`, `end`, `location` |
| Publicar en Teams | Microsoft | `team_id`, `channel_id`, `message` |
| Agregar fila a tabla de Excel | Microsoft | `item_id`, `table`, `values` |
| **Lecturas** (sin aprobación) | | |
| Leer Google Sheets | Google | `spreadsheet_id`, `range` |
| Próximos eventos (Google / Outlook) | Google / Microsoft | `days` |
| Listar archivos (OneDrive) | Microsoft | `query` |
| Leer rango de Excel | Microsoft | `item_id`, `worksheet`, `range` |
| Buscar en SharePoint | Microsoft | `query` |

> Fechas en formato ISO 8601 (ej. `2026-07-01T10:00:00Z`). `values` admite una lista
> separada por comas (una fila). En Excel, `item_id` es el id del archivo en
> OneDrive/SharePoint (lo da *Listar archivos* o *Buscar en SharePoint*).

---

## E) Privacidad y gobernanza
- Las credenciales (tokens) se guardan **cifradas** y se refrescan solas.
- Las acciones respetan **permisos por área** y quedan **auditadas**.
- El contenido sensible sigue las reglas del enrutador de privacidad.
- Las **escrituras** nunca corren solas salvo que otorgues **“Permitir siempre”**.

_MaestroAI · Guía de acciones de escritura (toolkit Google/Microsoft)._
