# Backlog & Auditoría — Plataforma MaestroAI (completa)

> Fecha: 2026-07-02. Auditoría honesta de toda la plataforma (backend, frontend, calidad),
> no solo del reporte de Silent4Business. Basada en revisión del código real en la rama `dev`
> por tres auditorías independientes + verificación manual de los hallazgos críticos.
> Backlog específico del reporte: ver `docs/BACKLOG-TABLERO-REPORTE.md`.

## Veredicto en tres frases
La **arquitectura de gobierno/privacidad está bien pensada** (árbol de decisión del router auditable,
aislamiento multi-tenant consistente y probado, fallback que nunca debilita la privacidad, cifrado
AES-256-GCM correcto). Pero el **diferenciador "IA privada" es, por defecto, fachada**: sin llaves
configuradas todo responde con un mock que reescribe el contexto, los embeddings son bag-of-words
hasheado (no semánticos) y la clasificación/PII son regex. Y hay una **capa de seguridad de
producción sin cerrar** (un secreto por defecto que es llave maestra de todo) que hace que hoy no
esté listo para un cliente real multi-tenant.

Contexto de escala/velocidad: ~18k líneas de Python (38 routers) + ~10k de TSX (34 páginas) + 313
tests, construidos casi todos en ~2 semanas. La velocidad es real; la deuda es la contracara.

---

## P0 — Bloqueantes de seguridad (antes de cualquier cliente real)

- [ ] **Secreto por defecto = llave maestra universal.** `config.py:13`
      `secret_key = "dev-secret-change-me-please-32-characters-min"` firma los JWT (`auth.py:48,64`),
      es raíz del cifrado at-rest (`config.py:201` → `master_kms_key` vacío cae a `secret_key`),
      firma el `state` de OAuth y cifra las API keys de proveedores. **No hay validación de arranque**
      que rechace el default con `app_env=production` (verificado: no existe). → Añadir un check en
      `lifespan`/`main.py` que aborte el arranque si `secret_key`/`master_kms_key` son el default en prod.
- [ ] **Credenciales demo sembradas sin gate de entorno.** `seed.py:10` `DEMO_PASSWORD="demo1234"`,
      `admin@maestroai.mx`, y `ensure_super_admin()` promueve a super-admin. Corre en cada arranque
      (`main.py:58`) sin condición sobre `app_env` (verificado). En un despliegue limpio de prod crea
      un super-admin con contraseña pública. → Gate por entorno + forzar cambio en primer login.
- [ ] **CORS abierto a todo `*.vercel.app` con credenciales.** `config.py:21` regex
      `https://(.*\.)?(vercel\.app|maestroai\.mx)` + `allow_credentials=True` (`main.py:83-92`).
      Cualquier deploy de cualquiera en vercel.app puede llamar con credenciales. → Lista blanca de
      dominios propios.
- [ ] **`/api/login` del reporte sin rate-limit** (verificado, sin throttle) → fuerza bruta contra la
      contraseña compartida. Y **`/api/health` sigue vivo** revelando presencia/longitud de la
      contraseña. (También en BACKLOG-TABLERO-REPORTE.md P0.)
- [ ] **SSRF vía DSN arbitrario en `/datasources`.** `datasources.py:66-80` hace `create_engine(dsn)`
      con DSN del usuario; `_check_dsn:59-63` solo valida el driver, no host/puerto. Rol privilegiado,
      pero permite apuntar a bases internas. → Allow-list de hosts + timeouts + red aislada.

## P1 — La brecha "sustancia vs fachada" (la propuesta de valor)

- [ ] **Por defecto no hay IA: MockAdapter.** `ai/adapters.py:31-54` es el fallback sin proveedor
      (`:175`), devuelve plantilla con `context[:3]`. Sin `.env` real, `/chat` solo formatea fragmentos.
      → Hacer explícito el "modo demo" en la UI y documentar que prod REQUIERE proveedor real.
- [ ] **Embeddings/RAG no semánticos por defecto.** `ai/embeddings.py:24-35`: hashing bag-of-words
      MD5 (384 dim); `EMBEDDINGS_PROVIDER=local` por defecto (`config.py:61`); reranker real apagado
      (`rerank_enabled=False`). Es coincidencia léxica disfrazada de vectorial. → Default a embeddings
      reales en prod o etiquetar la calidad honestamente.
- [ ] **Búsqueda global rota por el propio cifrado.** `search.py:54` hace `Document.text.ilike(...)`
      pero `rag.py:71` guarda `doc.text = encrypt(...)` (cifrado ON por defecto, verificado). Se busca
      sobre ciphertext → solo hace match el `filename`, nunca el contenido. → Índice de texto separado
      (tokens/tsvector) o búsqueda sobre chunks descifrados con permiso.
- [ ] **PII/clasificación frágiles.** `security/pii.py`: CLABE `\b\d{18}\b`, tarjeta sin Luhn,
      teléfono `\d{10}` — se solapan; `classifier.py:14-27` es keyword-matching en español. Es el
      corazón del router de privacidad y es evadible/ruidoso. → Validadores (Luhn), NER, y umbral de
      confianza; medir falsos negativos.
- [ ] **"Red team" tautológico.** La detección de inyección es substring-match (`policy.py:50`) y los
      tests (`test_redteam.py:36-40`) prueban exactamente esas frases. Una paráfrasis trivial pasa. →
      Corpus adversarial real + clasificador, no lista negra.

## P1 — Proceso de release (documentado pero no seguido)

- [ ] **Divergencia de ramas seria.** `dev` está **27 commits adelante** de `origin/main` y
      **128 commits atrás** (verificado). Es decir `dev` nunca se rebaseó sobre `main`; producción
      (`main`) avanzó por otro lado y el Tablero de un cliente real se **despliega desde `dev`**
      ("parche"). → Reconciliar ramas: rebasar `dev` sobre `main`, promover por Dev→QA→Prod, y regresar
      la Production Branch de Vercel a `main`. Definir branch protection + required checks.
- [ ] **CHANGELOG con ~42 commits de retraso**, todo en "[No liberado]". `ESTADO-PROYECTO.md` dice
      "245 pruebas" (son 313), fecha desactualizada, y se contradice (SFTP "hecho" y "candidato" a la
      vez). 20 .md en `docs/` con estado duplicado en 3 lugares. → Una sola fuente de verdad de estado;
      CHANGELOG por PR.

## P2 — Calidad, tests y escala

- [ ] **313 tests verdes que no prueban IA real.** El adaptador real está `# pragma: no cover - network`
      (`adapters.py:66,95`); 0 tests de timeout/API-key-inválida/JSON-malformado (`grep timeout tests/`
      → 0). CI verde = "funciona con un LLM imaginario perfecto". → Smoke test contra proveedor real
      (opcional, gated) + tests de caminos de error con stubs que fallan.
- [ ] **CI mínimo (44 líneas): 2 jobs.** No construye `apps/report` (un break llega a prod en verde),
      sin lint Python (no hay ruff/mypy), sin coverage, `npm install --no-audit` (auditoría apagada),
      sin pip-audit, sin dependabot. → Añadir report build, ruff+mypy, coverage con umbral, pip-audit/
      npm audit, dependabot.
- [ ] **Cero tests de frontend** en dos apps Next.js desplegadas (`apps/web`, `apps/report`). Sin
      jest/vitest/playwright; `next lint` configurado pero sin `.eslintrc` y CI no lo llama. El gate de
      contraseña del reporte solo tuvo smoke test manual. → Tests del gate de auth + smoke E2E (Playwright).
- [ ] **Vector store in-process O(n) en RAM por query.** `rag.py:152-180` carga TODOS los chunks del
      tenant y hace coseno en Python cada consulta. Inviable con 100k docs. Qdrant/pgvector es opt-in. →
      Default a pgvector en prod.
- [ ] **SQLite como default de prod** (`config.py:16`) — un solo escritor, sin pgvector. → Forzar
      Postgres si `app_env=production`.
- [ ] **Sin Alembic.** `db.py:_ensure_columns()` solo hace `ALTER ADD COLUMN` hardcodeado; renombres/
      tipos/backfills se pierden en bases existentes. → Adoptar Alembic.
- [ ] **Estado global no multi-worker.** `adapters.py:138 _RUNTIME` y `runtime_config.py:14 _CACHE` son
      estado de proceso; con `--workers>1` un cambio de config solo afecta a un worker. Además las API
      keys de proveedores son **globales, no por tenant** (mismo egress para todos). → Config en BD/Redis
      + keys por tenant.
- [ ] **~113 `except Exception` que tragan errores** (`token_store.py:106` refresh OAuth, `embeddings.py:58`
      cae a local silenciosamente mezclando dimensiones, `documents.py:82,90`). → Loggear + telemetría.
- [ ] **Integraciones happy-path.** SharePoint sin paginación (`@odata.nextLink`) ni manejo de 429
      (`sharepoint.py`); OAuth refresh no distingue "reconsentir" de error transitorio (`token_store.py:104`);
      n8n un solo POST sin reintento. → Reintentos con backoff, paginación, manejo de throttling.
- [ ] **Dependencias congeladas dic-2024** (~18 meses), sin proceso de actualización ni escaneo.
- [ ] **Routers/archivos grandes y acoplados.** `automations.py` (793), `models.py` (793, ~40 tablas),
      `admin.py` (617), `datasources.py` (615); patrón `session.get + if tenant_id !=` duplicado en
      decenas de endpoints. → Helper `get_owned(model, id, tenant)` único + dividir routers.

## P3 — Producto / UX (frontend)

- [ ] **~40% del catálogo es UI sobre backend simulado/stub.** Workflows (`workflows.py:130` "simulado"),
      App Studio, Agentes, Espacios, mitad de Fine-tuning (`finetune.py:222`), Automatizaciones sin n8n
      (`automations.py:649`). Hay un producto real de ~6 features (Notebooks, Documentos+RAG, Chat con
      fuentes, Generar imágenes, datasets de fine-tuning) escondido bajo 29 pestañas. → Cortar/fusionar
      cascarones; marcar honestamente lo "simulado".
- [ ] **App Studio "cobra" 499 MXN sin proveedor de pago.** `apps.py:156` pone `paid=True` directo; el
      deploy fabrica una URL muerta `https://{id}.apps.tu-saas.mx`. Presentado como transacción real. →
      Quitar o integrar pago real; es riesgo de confianza con clientes.
- [ ] **Solapamiento conceptual: 7 formas de "ejecutar algo con IA"** (Casos de uso, Runbooks, Acciones,
      Automatizaciones, Workflows, Agentes, App Studio). `Journeys.tsx` (126 líneas explicando dónde ver
      cada resultado) es la confesión de que la arquitectura de información falló. → Unificar vocabulario.
- [ ] **Auth 100% client-side** (`apps/web`): sin `middleware.ts`, token en `localStorage` (XSS),
      protección solo por `useEffect` en `Shell.tsx:98`. → Middleware + cookie httpOnly (como sí hace
      `apps/report`).
- [ ] **102 `.catch(() => {})`** que tiran errores (dashboard con 7 fetches silenciados); solo ~13/34
      páginas tienen estado de carga. → Manejo de error visible + toasts.
- [ ] **Sin design system:** card class ×95, input class ×143, `violet-600` hardcodeado ×113; branding
      multi-tenant solo tiñe el sidebar. **4 atributos aria en toda la app**; borrados sin confirmación.
      → 5 primitivas (Button/Card/Input/Field/Dialog) + accesibilidad básica.
- [ ] **53/53 archivos `"use client"`** — Next 15 usado como SPA; `api.ts` monolítico de 805 líneas;
      i18n/moneda inconsistente ($0.0000 USD vs MXN vs helper local). → Server Components donde aplique,
      `lib/format` compartido.
- [ ] **Datos del piloto hardcodeados en el producto white-label.** `tablero-financiero/page.tsx:14-18`
      trae `ENTITIES=[S4B,S4C,CONS]` y benchmark con columna literal "S4B". → Parametrizar por tenant.

---

## Lo que SÍ está sólido (para ser justos)
- Aislamiento multi-tenant **consistente y probado** con dos tenants reales (`test_redteam.py:57-97`:
  404 cross-tenant, no-fuga vía RAG/citations).
- Router de privacidad auditable (`ai/router.py`) y fallback que solo baja a rutas iguales o más
  privadas (`resilience.py`, `test_fallback.py`).
- Cripto correcta: AES-256-GCM con nonce+tag y versión de llave; PBKDF2 100k + `compare_digest`; MFA
  TOTP; webhooks con HMAC.
- Base de tests por encima del promedio de la categoría: 313 tests, 763 asserts, solo ~14% triviales,
  con asserts de negocio reales (`test_finance.py:35`).
- Núcleo de producto genuino: Notebooks, Documentos+RAG, Chat con fuentes, pipeline de datasets.

---

## Autocrítica (mía, como asistente en esta sesión)
- **Contribuí a la deuda de proceso:** empujé ~9 commits directo a `dev` y desplegué el Tablero de un
  cliente real desde `dev` — el mismo antipatrón que critico aquí. Lo correcto habría sido reconciliar
  con `main` y promover por Dev→QA→Prod.
- **Dejé `/api/health` en producción** (revela metadatos de la contraseña) marcándolo "temporal" en vez
  de quitarlo enseguida. Está en P0.
- **No añadí `apps/report` al CI** al crearlo, repitiendo la brecha que existía.
- **El comparativo de costos del reporte tiene circularidad metodológica** (CMI↔Timesheet) que documenté
  pero no resolví (ver BACKLOG-TABLERO-REPORTE.md P1).
- Reporté "162/151/245 tests" en distintos momentos citando de memoria/PRs; el número real hoy es **313**.
  Debí verificar antes de afirmar.

## Recomendación de orden (si hubiera que elegir 5 cosas)
1. Cerrar los P0 de seguridad (secreto de arranque, seed gate, CORS, rate-limit + quitar `/api/health`, SSRF).
2. Reconciliar ramas y arreglar el proceso de release (dev↔main + branch protection + report en CI).
3. Ser honestos sobre "modo demo": UI + docs que dejen claro qué requiere proveedor real (IA, embeddings, pago).
4. Escala de datos: Postgres+pgvector como default de prod; Alembic.
5. Recortar el sidebar a las ~6 features reales y unificar el vocabulario de ejecución.
