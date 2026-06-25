# Estado del proyecto — MaestroAI

> Bitácora viva de lo construido, cómo se despliega y qué falta. Última
> actualización: 2026-06-25.

Plataforma de **AI privada y gobernada** (Private AI Gateway + agentes
verticales): los datos se clasifican, la PII se redacta y el enrutador de
privacidad decide local / VPC / abierto / premium / bloqueo — todo auditado.

---

## 1. Arquitectura de despliegue

| Componente | Plataforma | URL |
|---|---|---|
| Portal (Next.js) | **Vercel** | (dominio del portal / `plataforma.maestroai.mx`) |
| API (FastAPI) | **Render** | `https://s4bdashboard.onrender.com` |
| Base de datos | Postgres (Render/Supabase) | — |
| Repo | GitHub `angeljba1480-AB/S4Bdashboard`, rama `main` | — |

> Cada push a `main` dispara **dos** despliegues independientes (Vercel + Render).
> Si el portal nuevo llama a una API vieja, revisar que Render redeployó desde `main`.

---

## 2. Funcionalidades (estado)

### Correo y cuentas
- ✅ Conexión OAuth **Outlook / Gmail** + **IMAP** (Yahoo, iCloud, Zoho, hosting…).
- ✅ **Varias cuentas por proveedor** (personal + trabajo); selector de cuenta.
- ✅ Caso «Resumen de correo y agenda».

### Documentos y RAG
- ✅ Repositorio por **área** + **catálogo de categorías** extensible.
- ✅ **Tratamiento** (público/interno/confidencial/restringido) auto-detectado y editable.
- ✅ Borrar y **re-etiquetar**; índice RAG cifrado.
- ✅ **Google Drive** como contexto (importar archivos al RAG).

### Casos de uso (recetas)
- ✅ Paso universal **objetivo / notas / formato** de salida.
- ✅ **Grounding por categoría** (cada caso jala de su tipo de documento).
- ✅ **Reporte por industria** (plantillas por sector).
- ✅ Export a **PDF / Word / Markdown / PPTX / XLSX**.

### Chat y Notebooks
- ✅ Chat con **3 modos de contexto** (sin contexto / todo / elegir documentos).
- ✅ **Notebooks** (estilo NotebookLM): fuentes + preguntas citadas + artefactos
  (resumen, FAQ, guía, briefing, cronología).

### Modelos
- ✅ **Router de privacidad** con redacción de PII y fallback.
- ✅ **Modelos externos** (GPT/Claude/Llama) configurables en la UI (cifrados).
- ✅ **Cascada**: borrador con modelo abierto → refinar con premium (aprobación
  para contenido sensible).

### Toolkit de acciones (Google/Microsoft)
- ✅ Enviar correo, crear eventos, append a Sheets, publicar en Teams.
- ✅ **Aprobación humana** para escrituras + **“Permitir siempre”** (revocable).

### Gobernanza y visibilidad
- ✅ **Super admin** (ve todos los tenants) + **permisos por área y licencia**.
- ✅ **Flujogramas navegables** (los 3 base del blueprint + flujo de caso + libre).
- ✅ **Dashboard** reforzado + **auditoría navegable** (filtros, búsqueda, detalle, stats).

---

## 3. Configuración pendiente del cliente (fuera del código)

Para activar lo que depende de credenciales/permisos:

1. **Scopes de escritura** (toolkit de acciones): agregar permisos en Azure/Google
   y **reconectar** — ver [`ACCIONES-ESCRITURA-SETUP.md`](./ACCIONES-ESCRITURA-SETUP.md).
2. **Modelo Premium** para la cascada: *Admin → Modelos externos* (Base URL + modelo + API key).
3. **Google Drive**: reconectar Google para otorgar `drive.readonly`.
4. Verificar que **Render** despliega desde `main` (Branch = `main`).

---

## 4. Calidad

- ✅ **151 pruebas** automatizadas en verde (API).
- Migraciones aditivas idempotentes (sin pérdida de datos).
- Credenciales cifradas (AES-256-GCM); todo auditado.

---

## 5. Pendientes / backlog

> Sección a completar con los detalles que el cliente comparta.

- [ ] _(por definir)_

### Ideas ya identificadas (candidatas a próximos sprints)
- Más acciones/lecturas del toolkit (Sheets/Excel read, SharePoint, OneDrive).
- Conector de **base de datos** (solo lectura) y **SFTP/CSV** para sistemas legados.
- Centrar integraciones a medida en **n8n** (catálogo de recetas: DB, SOAP, apps propias).
- Verificación del primer **modelo premium real** en producción.

_MaestroAI · Estado del proyecto._
