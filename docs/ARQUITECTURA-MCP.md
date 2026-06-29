# Arquitectura: MCP / KB, aislamiento por cliente, KEDB y marca blanca

> Decisiones de arquitectura para MaestroAI como plataforma de un MSP (S4B) que
> automatiza procesos y entrega servicios a **múltiples clientes finales**.
> Principio rector: **aislamiento por defecto, compartir por excepción**.

## 1. Modelo de 3 capas (scopes, NO carpetas)
El riesgo #1 es **mezclar información entre clientes**. Por eso los límites son
*scopes duros* (namespaces/índices separados), no carpetas dentro de un store común.

1. **KB Global S4B (interna)** — "maestro" pero **solo conocimiento de S4B** (metodología,
   catálogos, playbooks, políticas, plantillas). **Sin PII de cliente.** Referencia de solo lectura.
2. **MCP por Área** (Finanzas, SOC/Ciber, RRHH, Legal, Trámites/Gobierno…) — herramientas +
   conocimiento de cada área, interno de S4B, segmentado por área y por rol.
3. **MCP por Cliente (= Espacio)** — cada cliente final tiene su **Espacio** con **su** data,
   su namespace de RAG y sus conectores. **Límite duro:** el agente de un cliente ve solo su
   scope + lo que S4B exponga de las capas 1/2 — **jamás** otro cliente.

> Flujo del agente de un Espacio = datos del cliente + área(s) habilitadas + KB global (referencia).
> Un "MCP" = *paquete de herramientas/conectores + namespace de conocimiento*, vinculado por Área y por Espacio.

**Anti-patrón:** un "MCP maestro tipo data lake" con carpetas mezclando datos crudos de
clientes. El data lake sirve para analítica **agregada y anonimizada**, no para que los
agentes operativos lo consulten.

## 2. KEDB — KB de Operaciones (aprendizaje entre clientes, SIN fuga)
Excepción válida al aislamiento: una base de **errores conocidos** (ITIL KEDB) que aprende
entre clientes para análisis **interno** (p. ej. SOC), **no** para respuestas al cliente.

> Se comparte el **CONOCIMIENTO** (anónimo); nunca el **DATO** del cliente.

Un error analizado para el Cliente A se vuelve "error conocido" reutilizable para el Cliente B,
pero lo que viaja al KEDB es **firma del error + causa raíz + solución** (genérico), sin nombres,
IPs, hostnames, usuarios ni PII.

**3 candados:**
1. **Sanitización al ingresar** — al "promover a error conocido", se quitan identificadores
   (regex + router de privacidad). Entra solo lo genérico (producto/vendor, síntoma, patrón de
   log, causa raíz, fix, severidad).
2. **Scope interno** — lo consultan operadores S4B, no los agentes de cara al cliente. Un
   entregable cita la solución, nunca dice "esto le pasó al Cliente X".
3. **Revisión humana** — promover → sanitizar → **aprobar** → KEDB.

Flujo: *incidente (Espacio cliente) → análisis → ¿nuevo? promover → sanitizar → aprobar → KEDB*;
y *nuevo incidente → buscar en KEDB por firma → "es KE-123, fix X"*.

Se apoya en lo que ya existe: **Documentos** (`sensibilidad`+`categoría`), **Runbooks** y el
**router de privacidad**. El KEDB sería una categoría/namespace `operaciones/known-errors` con
sanitización + aprobación a la entrada. *(Pendiente de implementar.)*

## 3. Clasificación: cifrado vs público
Por **sensibilidad** del documento (ya existe el campo) + router de privacidad (redacta PII
antes de salir a un modelo externo):
- **Público** (marketing, catálogos) → puede ir a modelos externos.
- **Interno** (metodología S4B) → usuarios internos; redacción al salir a externos.
- **Confidencial/Restringido** (datos de cliente, PII, financieros) → cifrado en reposo,
  fijado a rutas privadas (local/VPC) o redacción estricta, y **nunca** cross-cliente.

## 4. Marca blanca (white-label)
- **Branding por tenant** (✅ ya existe): nombre, logo, color, tagline en *Admin → Configuración*.
- **Remitente de soporte por tenant** (✅ implementado): el correo saliente de las
  automatizaciones sale del **buzón de soporte de la empresa**, no de la cuenta personal de
  quien ejecuta. Se elige en *Configuración de empresa → Remitente de soporte*
  (`GET/PUT /company/support-sender`); opción de alias *From* con send-as verificado.
- **Pendiente para marca blanca completa:** dominio propio por cliente (Vercel custom domain),
  correo desde el dominio del cliente, y el **rename interno `s4bdashboard` → MaestroAI**
  (ver `CONFIGURACION-PROGRESO.md`).

## Estado de implementación
- ✅ Espacios (límite por cliente), sensibilidad de documentos, router de privacidad,
  cifrado por tenant, branding por tenant, **remitente de soporte por tenant**.
- ⏳ Bindings explícitos Área/Espacio↔MCP como filtro duro; **KEDB** (promover/sanitizar/aprobar);
  dominio propio por cliente; rename interno.
