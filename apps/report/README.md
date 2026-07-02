# Tablero Financiero — Reporte público (standalone)

App **Next.js autocontenida** para publicar el Tablero Financiero de solo lectura y
compartirlo con el equipo **sin** necesidad de entrar a MaestroAI. Protegida por una
**contraseña compartida validada en el servidor** (Edge Middleware) con cookie firmada
por HMAC — la contraseña nunca vive en el código del navegador.

## Cómo funciona

- `src/middleware.ts` — compuerta: todo exige sesión salvo `/login`.
- `src/app/api/login/route.ts` — valida la contraseña contra `REPORT_PASSWORD` (server-side,
  comparación en tiempo constante) y emite la cookie firmada.
- `src/lib/auth.ts` — firma/verificación HMAC-SHA256 con Web Crypto (compatible con Edge).
- `src/lib/data.ts` — carga el dataset desde la env var `REPORT_DATA` (JSON o base64);
  si no está, usa `src/data/demo_bundle.json` (datos de ejemplo versionados).
- `src/components/Dashboard.tsx` — el tablero (solo lectura). Las vistas sin datos reales
  se marcan con un badge **DEMO**.

## Datos reales (nunca se commitean)

Los números reales del cliente **no** están en el repositorio. Se generan aparte y se
inyectan por variable de entorno:

```bash
# genera el bundle real desde los Excel del cliente (requiere la API en apps/api)
python apps/report/scripts/build_bundle.py \
  --files Reporte_Nomina.xlsx Timesheet.xlsx "Proyectos Finanzas.zip" Evaluacion_Clientes.xlsx \
  --mark-demo resumen finanzas posicion clientes benchmark alertas \
  -o real_bundle.json

# en Vercel: pega el contenido en la env var REPORT_DATA (o su base64)
```

## Variables de entorno (Vercel)

| Variable | Descripción |
|---|---|
| `REPORT_PASSWORD` | Contraseña compartida que escribe el equipo. **Requerida.** |
| `REPORT_SECRET`   | Secreto para firmar la cookie (HMAC). `openssl rand -hex 32`. Recomendada. |
| `REPORT_DATA`     | Dataset del reporte (JSON o base64). Si falta, muestra el demo. |

## Local

```bash
cd apps/report
npm install
cp .env.example .env.local   # define REPORT_PASSWORD y (opcional) REPORT_DATA
npm run dev                  # http://localhost:3001
```
