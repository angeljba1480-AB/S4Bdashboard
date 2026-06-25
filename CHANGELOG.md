# Bitácora de cambios — MaestroAI

Formato basado en *Keep a Changelog*. Las versiones se promueven **dev → qa → main (prod)**.

## [No liberado]
- **Toolkit · Excel y SharePoint**: leer rango de Excel y **agregar fila a tabla**
  (Graph workbook), **buscar en SharePoint**. Nuevos scopes `Files.ReadWrite.All`
  y `Sites.Read.All` (la escritura sigue con aprobación humana).
- **Conector CSV** para sistemas legados sin API: importa un CSV pegado al
  repositorio + RAG (`/datasources/import-csv`), con panel en Integraciones.

## 2026-06-25 — promovido a prod (PR #12)
- CI: primera corrida en `dev`/`qa` para registrar los checks (`API · pytest`,
  `Web · build`) y validar la compuerta antes de producción.
- **Eficiencia de tokens en la UI**: controles de condensación y tope de gasto por
  consulta configurables (Admin), con ahorro acumulado.
- **Toolkit · lecturas**: Google Sheets, Google/Outlook Calendar y OneDrive.
- **Conector de base de datos** (solo lectura) → importa al RAG (`/datasources`).
- **Frontend** de fuentes de datos en Integraciones.
- **Seguridad**: revisión del código nuevo + fixes — config global restringida a
  super admin, sanitización de consultas Drive/OneDrive, denylist DML/CTE y
  esquemas de DSN permitidos, escapado de segmentos de URL en acciones.

## 2026-06-25

### Añadido
- **Memoria + Tags** (#6): memoria persistente por usuario, búsqueda semántica +
  por tags, auto-captura al completar casos, recall en el chat (`use_memory`),
  página *Memoria*.
- **Eficiencia de tokens** (#5): condensación del contexto con el modelo barato
  antes de premium, escalado por respuesta insuficiente, tope de tokens por
  consulta (`MAX_TOKENS_PER_REQUEST`).
- **Toolkit de acciones Google/Microsoft** (#... Sprint 7): enviar correo, crear
  eventos, append a Sheets, publicar en Teams; aprobación humana + "Permitir
  siempre".
- **Scopes de escritura** y guía `ACCIONES-ESCRITURA-SETUP.md` (#3).
- **Notebooks** (estilo NotebookLM), **LLMs externos** configurables y **cascada
  de modelos** (Sprint 6).
- **Dashboard reforzado + auditoría navegable** (Sprint 5).
- **Salidas** PPTX/XLSX, **reportes por industria** y **Google Drive** como
  contexto (Sprint 4).
- **Flujogramas navegables** (Sprint 3).
- **Gobernanza**: super admin + permisos por área y licencia (Sprint 2).
- **Línea base**: onboarding obligatorio + paso objetivo/notas/formato (Sprint 1).
- **Documentos por área + categorías + tratamiento**, **chat con 3 modos de
  contexto**, **recetas con grounding por categoría**, **multi-cuenta de correo**.
- **Diagramas de arquitectura** (`docs/ARQUITECTURA.md`) y **modelo de entornos**
  (`docs/ENTORNOS.md`).

### Corregido
- Build de Vercel: el tipo de `api.chat` no incluía `precision`/`approve_external`
  (rompía TypeScript). Verificado con `tsc` y `next build` (#6).

### Seguridad / privacidad
- Redacción de PII antes de cualquier salida externa; credenciales cifradas
  (AES-256-GCM); todo auditado; permisos por área aplicados en documentos, chat,
  recetas, notebooks y memoria.

---

> Cómo registrar cambios: agrega tu entrada bajo **[No liberado]** al abrir el PR
> a `qa`; al promover a `main` se fecha y se mueve a una sección de versión.
