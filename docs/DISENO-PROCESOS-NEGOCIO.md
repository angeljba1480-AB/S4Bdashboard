# Diseño — Módulo de Procesos de Negocio (columna vertebral de MaestroAI)

> Fase 0 (diseño). Documento para validar el concepto y el alcance antes de codificar.
> Formatos hermanos: `.docx` y `.pptx` (misma fuente). Fecha: 2026-07-02.

## 1. El problema (por qué esto importa)
En "AI empresarial" abunda el humo: *"pon un agente y te resuelve la vida"*. En la práctica un
agente sin contexto de **qué proceso** mejora y **cuánto** vale, no sirve. Las tres auditorías de
la plataforma detectaron el mismo síntoma: **29 features sin columna vertebral** — no hay un "¿para
qué?" que conecte todo. Falta:
1. **Trazabilidad**: ¿esta automatización/agente a qué servicio y cliente beneficia?
2. **Medición de beneficio real**: ¿cuánto ahorró/mejoró, con cifras propias, no promesas?

## 2. La solución
Un **módulo de Procesos de Negocio** (BPM ligero, visual en canvas) que se configura justo después
del alta básica de la empresa y funciona como **hub de entrada**: desde ahí se decide qué automatizar,
con qué agentes/IA, y se mide el beneficio con los datos que la plataforma ya tiene.

## 3. Modelo conceptual
```
Línea de negocio ──> Servicio ──> Proceso ──> Paso (actividad)
   (p. ej. SOC,        (interno: OLA /        (cada paso puede
    Consultoría,        externo: SLA →         automatizarse con
    Licenciamiento)     Cliente que paga)      un Agente/Automatización)
```
- **Línea de negocio**: agrupador comercial (lo que la empresa "hace").
- **Servicio**: unidad entregable. Dos tipos:
  - **Interno (OLA — Operating Level Agreement)**: da servicio a otras áreas internas ("olas").
  - **Externo (SLA)**: se ofrece a **clientes finales que pagan**; se liga a uno o más clientes.
- **Proceso**: secuencia de pasos que produce el servicio.
- **Paso / actividad**: lo accionable. Estado: *manual* → *candidato a automatizar* → *automatizado*.

## 4. Trazabilidad (el hilo que hoy falta)
Cada **Agente**, **Automatización** o **Caso de uso** se **liga a un Paso**. Como el Paso pertenece a
Proceso → Servicio → Línea → (Cliente si es externo), el sistema puede responder en una frase:
> *"Este agente automatiza el paso «triage de alertas» del servicio SOC (SLA) de Banjercito,
> que factura $X al año."*

Esto convierte la pregunta recurrente *"¿esto para qué sirve?"* en una respuesta con nombre y monto.

## 5. Medición de beneficio / ROI (el diferenciador)
Por cada paso que se automatiza se captura un **baseline** y un **después**:
| Métrica | Fuente |
|---|---|
| Horas/persona por ciclo | Timesheet (ya ingerido) |
| Costo de esas horas | Costo-hora por rol del Concentrado BC (ya ingerido) |
| Tiempo de ciclo | Captura simple / timestamps |
| Errores / retrabajo | Captura simple |
| Volumen (ciclos/mes) | Captura simple |

Ahorro real = (costo_antes − costo_después) × volumen. **El ROI de la IA sale de las cifras propias
de la empresa (nómina/timesheet/BC), no de una promesa de proveedor.** Autollenado desde Timesheet
cuando el paso ya tenga horas registradas, para que capturar el baseline sea trivial.

## 6. Canvas (experiencia visual)
Un **solo lienzo** como forma primaria de ver y editar:
- Nodos: Línea, Servicio (interno/externo con color distinto), Proceso, Paso, Cliente, Agente/Automatización.
- Aristas: pertenencia (Línea→Servicio→Proceso→Paso) y "sirve a" (Servicio externo→Cliente).
- En cada Paso: badge de estado (manual / candidato / automatizado) y, si aplica, el ahorro estimado.
- Acción directa desde el Paso: **"Automatizar con IA"** → elige/crea Agente o Automatización.
- Unifica lo que hoy está disperso (Flujogramas + canvas de Automatizaciones) en un lienzo con propósito.

## 7. Modelo de datos (propuesta, SQLModel)
Nuevas tablas (multi-tenant, con `tenant_id`):
- `business_lines` (id, tenant_id, name, description)
- `business_services` (id, tenant_id, line_id, name, kind[`internal`|`external`], sla_ola, description)
- `service_clients` (service_id, client_ref) — liga servicios externos a clientes (Evaluación de Clientes)
- `business_processes` (id, tenant_id, service_id, name, description)
- `process_steps` (id, tenant_id, process_id, name, order, automation_state[`manual`|`candidate`|`automated`])
- `step_links` (step_id, target_type[`agent`|`automation`|`recipe`], target_id) — trazabilidad
- `step_metrics` (step_id, phase[`baseline`|`after`], hours_per_cycle, cost_per_cycle, cycle_time, errors, volume_month, captured_at)
- `canvas_layout` (tenant_id, node positions) — posiciones del lienzo

## 8. Integración con lo ya construido
- **Clientes**: reutiliza la Evaluación de Clientes del Tablero (no se duplica).
- **Costos**: reutiliza costo-hora (BC) y horas (Timesheet) ya ingeridos para el ROI.
- **Agentes / Automatizaciones / Casos de uso**: ya existen; este módulo les da el "a qué sirven".
- **Canvas**: parte de la base existente (Flujogramas / canvas de Automatizaciones).
- **Gobierno**: hereda RBAC por área, auditoría y el router de privacidad.

## 9. Flujo de usuario (onboarding con propósito)
1. Configurar empresa (básico) — ya existe.
2. **Mapa de Procesos**: dibujar líneas → servicios (interno OLA / externo SLA→cliente) → procesos → pasos.
3. Marcar pasos *candidatos a automatizar*.
4. Desde el paso: **"Automatizar con IA"** (agente/automatización) — con el banner de modo demo si no hay IA real.
5. Capturar baseline (autollenado desde Timesheet cuando se pueda) y medir el después.
6. Ver **beneficio real por servicio/línea/cliente** en un tablero de ROI.

## 10. Fases de entrega
- **Fase 0 (este documento):** diseño y validación. ✅
- **Fase 1:** modelo de datos + CRUD de Líneas/Servicios/Procesos/Pasos + ligar clientes.
- **Fase 2:** canvas (diagramar y enlazar).
- **Fase 3:** enganchar agentes/automatizaciones a pasos + baseline/ROI con datos reales.
- **Paralelo (bajo riesgo):** recorte del sidebar (fusión de navegación + banderas), ver §12.

## 11. Riesgos y decisiones
- **Alcance:** BPM **ligero**, NO BPMN 2.0 completo (80% del valor, 20% del esfuerzo).
- **Captura de datos:** el ROI solo vale si se captura el baseline → hacerlo trivial (autollenar).
- **No otra isla:** debe ser el hub de entrada, no una pestaña huérfana más.
- **Abierto:** ¿jerarquía estricta o un servicio puede pertenecer a varias líneas? (propuesta: 1 línea, N clientes).

## 12. Recorte del sidebar (paralelo)
- **Conservar:** Resumen, Buscar, Operación, Documentos, Chat, Notebooks, Generar imágenes, Tableros,
  Integraciones, Agentes, Gobierno.
- **Fusionar:** Casos de uso + Runbooks + Acciones → *Casos de uso*; Automatizaciones + Workflows →
  *Automatizaciones (canvas)*; Memoria → dentro de Chat/Documentos.
- **Esconder (cascarón/simulado):** App Studio, Fine-tuning, Espacios (su función la absorbe Procesos).
- Meta: de ~29 a ~12–14 pestañas con propósito. Nada se borra de golpe; se esconde tras banderas.

## 13. Métricas de éxito del módulo
- % de pasos con dueño de servicio/línea identificado (trazabilidad).
- # de pasos con baseline capturado y # automatizados.
- Ahorro real acumulado ($/horas) atribuible a IA, por servicio/línea/cliente.
- Tiempo desde "configuré la empresa" hasta "primer proceso mapeado y primer paso automatizado".
