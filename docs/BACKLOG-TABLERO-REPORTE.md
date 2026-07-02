# Backlog — Tablero Financiero (apps/report + ingest de finanzas)

> Estado al 2026-07-02. Reporte desplegado y funcionando en Vercel
> (proyecto `s4-bdashboard-web`, rama `dev`, root `apps/report`), protegido por contraseña
> server-side. Datos reales SOLO en la env var `REPORT_DATA` (nunca en el repo).
> Este backlog recoge la deuda técnica y metodológica conocida, en orden de prioridad.

## P0 — Seguridad / higiene (hacer ya)
- [ ] **Quitar `/api/health`** (`apps/report/src/app/api/health/route.ts` + entrada en el
      `matcher` de `apps/report/src/middleware.ts`). Era diagnóstico temporal; revela
      presencia/longitud de la contraseña.
- [ ] **Rate-limiting en `/api/login`** (p. ej. contador por IP en cookie/KV, o Vercel WAF).
      Hoy permite fuerza bruta sin límite contra la contraseña compartida.
- [ ] **Rotar `REPORT_PASSWORD` a una frase larga** (la de prueba era corta). Recordar:
      borrar+recrear la var y **Redeploy** (las env vars solo aplican al construir).

## P1 — Metodología del comparativo de costos (honestidad de los números)
- [ ] **CMI mensual real, no prorrateado.** El reporte de Nómina actual es acumulado anual →
      `costo_cmi` se prorratea plano entre los meses del periodo. Pedir el **Lay Out de
      nómina consolidado (cmi_consolidado)** con mes y centro de costos (proceso descrito en
      la doc del cliente, pasos de Daniel/Emanuel) y parsearlo por mes.
- [ ] **Eliminar la circularidad CMI↔Timesheet.** Hoy `costo_timesheet` usa el costo-hora
      derivado del propio CMI del periodo ⇒ los totales anuales coinciden por construcción y
      solo la distribución mensual es informativa. Con cmi_consolidado por persona/mes:
      costo-hora por persona (÷ horas del `Catalogo horas laborales`) × horas por
      proyecto/persona del Timesheet ⇒ medidas independientes, como el modelo Power BI (ER).
- [ ] **Dimensión Centro de Costos (NOMBRE DE CC).** RESUMEN_COSTOS del ER compara
      costo_cmi/bc/timesheet **por CC**; hoy solo hay totales. Requiere el catálogo de CC por
      empleado (derivable de la Nómina consolidada).
- [ ] **Cruce por persona Nómina×Timesheet** usando `Catalogo Nombres.xlsx` (ya se sube pero
      no se usa) para normalizar nombres (mayúsculas/acentos/orden de apellidos).
- [ ] **Prorrateo 2026:** el periodo 01/01–15/06 se divide entre 6 meses completos; junio es
      medio mes ⇒ costo mensual subestimado ~9%. Ponderar el último mes por días cubiertos.
- [ ] **Validar 310 empleados del timesheet 2025** (vs ~148 en 2026): si hay nombres
      duplicados por formato, la capacidad está inflada y la utilización real es MAYOR que
      la reportada (38.7%). Deduplicar con el catálogo de nombres.
- [ ] **"Invertido por proyecto"**: costo aplicado por proyecto (horas × costo-hora por
      persona), no solo horas por proyecto — es la tabla clave del ER que falta.

## P1 — Completar las 6 vistas DEMO con datos reales
(Resumen, Finanzas P&L, Posición/balance, Clientes, Benchmark, Alertas — hoy con badge DEMO.)
- [ ] Parser de **estados financieros consolidados** ("Consolidado Mensual mes/año" que
      elabora Talia/Emanuel) → `fy`, `fy_2024`, `monthly` (12 meses × S4B/S4C/CONS),
      `segments` y campos de balance (activo, pasivo, capital, caja, CxC, CxP, DSO/DPO/CCC,
      ROE, endeudamiento). Los zips de "Global Finanzas" recibidos traían **placeholders**
      (100/410 repetidos) — pedir los reales.
- [ ] **`top_clients` reales**: derivables YA de `projects.clients` (dato real existente) —
      quick win sin esperar archivos nuevos.
- [ ] **`alerts` generadas de datos reales** (desviación EBITDA vs BC, utilización baja,
      concentración por cliente) en vez de las 3 alertas demo.
- [ ] **Benchmarks**: conseguir fuente o etiquetar permanentemente como referencia sectorial.
- [ ] Al completar cada vista, quitarla de `--mark-demo` en `build_bundle.py` y regenerar
      `REPORT_DATA` (base64) + Redeploy.

## P2 — Infraestructura / proceso
- [ ] **CI: construir `apps/report`** (job con `npx tsc --noEmit` + `next build`); hoy
      `ci.yml` solo cubre api y web ⇒ un cambio que rompa el reporte pasa en verde.
- [ ] **Promover `dev` → `qa` → `main`**: hay ~26 commits sin promover; Vercel despliega de
      `dev` como parche. Tras promover, regresar la Production Branch del proyecto a `main`.
- [ ] **Tests del gate de auth** (`apps/report/src/lib/auth.ts`): firma/verificación,
      expiración, trim de contraseña — hoy solo hubo smoke test manual.
- [ ] **Tamaño de `REPORT_DATA`**: ~47 KB base64; el límite de env vars en Vercel es 64 KB
      totales. Si el dataset crece (más años/detalle), migrar a Vercel Blob o a un JSON
      cifrado servido por la app.
- [ ] Renombrar el proyecto Vercel (`s4-bdashboard-web` → `tablero-financiero`) y/o dominio
      propio (cosmético).
- [ ] Acceso por usuario (magic links o contraseñas individuales) si se necesita revocación
      granular — hoy una contraseña compartida no permite revocar a una sola persona.

## Hecho (referencia rápida)
- Ingesta real: Resumen por proyecto (2021–2026), Concentrado BC (costo_bc + costo/hora por
  rol), Nómina CONTPAQi (`_nomina` → costo_cmi), Timesheet por columnas
  (`_parse_timesheet` → costo_timesheet + utilización), Evaluación de clientes (46).
- App standalone `apps/report` con gate server-side (HMAC/Edge) desplegada y verificada.
- Bundle real generado con `apps/report/scripts/build_bundle.py` e inyectado por env var.
- Tests: suite completa de la API en verde, incl. Nómina/Timesheet.
