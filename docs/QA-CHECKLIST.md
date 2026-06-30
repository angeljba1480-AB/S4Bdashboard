# MaestroAI · Checklist de QA (end-to-end)

Guía para validar la plataforma de punta a punta antes de entregar a un cliente.
Marca cada caso tras probarlo en producción. Orden sugerido: onboarding → datos →
automatización → entrega → módulos.

## 0. Acceso y marca
- [ ] Login con MFA funciona; logout limpia sesión.
- [ ] El sidebar muestra la **marca del tenant** (nombre/logo/color) si está configurada.
- [ ] (Marca blanca) Dominio propio resuelve y los **redirect URIs** de Microsoft/Google apuntan al dominio nuevo (si se cambió).

## 1. Onboarding de un cliente nuevo
- [ ] Crear tenant / Espacio del cliente.
- [ ] Configurar **branding** (Admin → Marca) y **remitente de soporte** (Configuración).
- [ ] Crear usuarios + asignar licencias (asientos).
- [ ] Definir **giro/industria** (si es ciberseguridad, debe aparecer **KEDB** en el menú).

## 2. Documentos y RAG
- [ ] Subir **cualquier tipo** de archivo (PDF, Word, Excel, PPT, ZIP, imagen) → se extrae texto.
- [ ] El **nombre** se autollena al elegir archivo; se puede editar antes de subir.
- [ ] Importar de **Google Drive** (navegar + importar).
- [ ] Importar de **SharePoint** (Documentos → Importar de SharePoint → navegar → importar).
- [ ] Borrar un documento → desaparece del repositorio **y** del índice RAG.
- [ ] **Chat con fuentes** responde citando documentos; en restringidos respeta la política.

## 3. Integraciones
- [ ] Conectar **Outlook/Gmail** (toolkit de acciones queda activo).
- [ ] **n8n**: Admin → n8n conectado; una automatización tipo workflow da `n8n 200`.
- [ ] Conector de salida (Zapier/Make/webhook) → "Probar" responde 200 con URL completa.
- [ ] Conector **OData (SAP)** y/o **SharePoint** (carpeta fija) → Probar + Importar.

## 4. Automatizaciones (multi-paso + canvas)
- [ ] Activar una plantilla; **Validar** muestra el diagrama (semáforo) y permite editar por nodo.
- [ ] **Constructor** multi-paso: agregar/ordenar (drag-and-drop)/editar/eliminar pasos; Guardar.
- [ ] Ejecutar un pipeline `entrada → workflow/ai → salida` → corre en orden y entrega.
- [ ] **Entrega**: el resultado llega a Notificación / WhatsApp / Correo según la salida.
- [ ] **Programar** (diario/semanal/mensual) deja la automatización activa.

## 5. Workflows reales
- [ ] `ingesta` indexa documentos pendientes.
- [ ] `mando` (Reporte de operación) → reporte ejecutivo legible (no JSON crudo).
- [ ] `sow` y `cyber` generan documento con IA + RAG.

## 6. Export
- [ ] **Descargar** un reporte como PDF / Word / PPT / Excel.
- [ ] **Guardar en la nube**: Google Docs / OneDrive con la cuenta propia.

## 7. KEDB (solo perfil ciberseguridad)
- [ ] Alta de error conocido; **Analizar síntoma** sugiere coincidencias.
- [ ] **Extraer** desde un log/incidente → borrador estructurado.
- [ ] **Compartir** (promover) → sanitiza y crea propuesta pendiente.
- [ ] Operador (super admin): **Propuestas** → Aprobar → queda visible como `shared`.
- [ ] Un tenant **no operador** NO puede editar un error `shared` (403).

## 8. Tablero Financiero (caso de uso)
- [ ] **Descargar plantilla** → llenarla → **Cargar datos** → el tablero muestra cifras reales.
- [ ] `Restablecer` vuelve al demo.
- [ ] Preguntar (RAG) responde con cifras del dataset cargado.

## 9. Seguridad / operación (producción)
- [ ] **Respaldos de la BD** (Postgres) configurados y restaurables.
- [ ] **Cifrado en reposo** activo (Admin → Postura de seguridad).
- [ ] **Auditoría** registra subidas, acciones, KEDB, automatizaciones.
- [ ] **Entregabilidad de correo** (SPF/DKIM del dominio de soporte) revisada.
- [ ] Rotación de `MASTER_KMS_KEY` documentada (rompe ciphertext → reconectar cuentas).

## Notas
- El RAG es **in-process** por defecto (vectores en la BD, coseno en Python). Para
  gran escala: `VECTOR_STORE=qdrant` o `pgvector`.
- Pendientes que dependen de datos del cliente: comparativo de costos (Nómina + CC).
