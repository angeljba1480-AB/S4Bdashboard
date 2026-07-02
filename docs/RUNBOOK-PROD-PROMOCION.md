# Runbook — Cierre de la promoción a producción (acciones manuales)

> Contexto: los P0 de seguridad, la ingesta Nómina/Timesheet y el reporte `apps/report`
> ya están en `main` (PRs #181 dev→qa, #182 qa→main, CI verde). `dev == main`.
> Backup de producción previo: rama `backup/prod-main-20260702` (= commit `bd52fd9`).
> Estos 3 pasos son en dashboards (Render/Vercel/GitHub); requieren tus permisos.

---

## 1. 🔴 CRÍTICO — Variables del API en Render (antes/tras el deploy)

Con el nuevo gate de arranque, si el API corre con `APP_ENV=production` y el secreto/llave
siguen en el valor por defecto, **el arranque falla a propósito** (así evitamos la llave
maestra universal). Define en Render → tu servicio del API → **Environment**:

```
APP_ENV        = production
SECRET_KEY     = <valor de: openssl rand -hex 32>
MASTER_KMS_KEY = <valor de: openssl rand -hex 32>   # otro valor distinto
```

Genera cada uno en tu terminal:
```bash
openssl rand -hex 32   # ejecútalo dos veces; usa una salida para cada variable
```

⚠️ **Advertencia de cifrado:** `MASTER_KMS_KEY` (o `SECRET_KEY` si aquél está vacío) es la
raíz del cifrado en reposo. Si **cambias** el valor con el que ya se cifraron datos, esos
datos **no se podrán descifrar**. Casos:
- **Si hoy NO tenían KMS propio** (usaban el default): NO había datos cifrados con una llave
  segura; define ambas variables ahora sin problema.
- **Si ya tenían un `MASTER_KMS_KEY` propio**: NO lo cambies; solo asegúrate de que `SECRET_KEY`
  no sea el default. Cambiar el KMS requeriría re-cifrar (descifrar con la vieja, cifrar con la
  nueva) — no lo hagas sin un plan de migración.

Verificación tras el deploy: el servicio arranca sin el error
`"Arranque abortado por seguridad (APP_ENV=production)"` en los logs.

### Otras variables recomendadas en prod (del backlog)
```
DATABASE_URL        = postgresql://...        # NO SQLite en prod
SEED_DEMO_DATA      = (no la definas)         # así NO se siembra admin@maestroai.mx/demo1234
CORS_ORIGIN_REGEX   = (opcional)              # el default ya es solo *.maestroai.mx
```
Si necesitas permitir previews de Vercel del portal, define `CORS_ORIGIN_REGEX` acotado a tu
proyecto, p. ej.: `https://([a-z0-9-]+\.)*maestroai\.mx|https://portal-[a-z0-9-]+\.vercel\.app`

---

## 2. Vercel — reapuntar el reporte a `main`

`main` ya contiene `apps/report`, así que deja de servir desde `dev`:

1. Vercel → proyecto **`s4-bdashboard-web`** → **Settings**.
2. **Environments → Production → Branch Tracking** (o **Git → Production Branch**) → cámbialo de
   `dev` a **`main`** → **Save**.
3. **Deployments → Redeploy** (para tomar `main`).

Funciona igual ahora porque `dev == main`, pero deja el estado final limpio (producción
sirviéndose de la rama de producción). Las env vars del reporte (`REPORT_PASSWORD`,
`REPORT_SECRET`, `REPORT_DATA`) no cambian.

---

## 3. GitHub — Branch protection (recomendado)

Evita que se vuelva a empujar directo a producción y que se mergee sin CI:

1. GitHub → repo **S4Bdashboard** → **Settings → Rules → Rulesets → New branch ruleset**.
2. **Name:** `protect-prod`; **Enforcement:** Active.
3. **Target branches:** incluir `main` y `qa` (Add target → por patrón: `main`, `qa`).
4. Activa:
   - **Require a pull request before merging** (mín. 1 aprobación si quieres revisión).
   - **Require status checks to pass** → agrega como requeridos:
     - `API · pytest`
     - `Web · build`
     - `Report · build + E2E`
   - **Require branches to be up to date before merging**.
   - **Block force pushes**.
5. Save.

(Si prefieres proteger también `dev`, crea otro ruleset con los mismos checks pero sin exigir
aprobación, para no frenar el trabajo diario.)

### Nota de proceso: el "churn" de merges vacíos
Los PRs #157–180 en `main` fueron merges sin cambio de código (el pipeline dev→qa→main
ciclando en vacío). Vale la pena revisar la automatización que los genera (¿un cron/bot que
mergea aunque no haya diff?) para no inflar el historial ni gastar minutos de CI. Con branch
protection + "require up to date" se reduce, pero conviene apagar el disparador de fondo.
