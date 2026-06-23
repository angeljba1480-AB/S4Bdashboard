# S4B · Administración de Ligas (prototipo)

Plataforma **multideporte** para administrar ligas deportivas como SaaS:
tú rentas la plataforma a cada liga, las ligas llevan sus partidos
(ganados / perdidos / empates) y tabla de posiciones, y los papás pueden
pagar inscripciones y cuotas dentro de la app.

> Este es un **prototipo visual** con datos de ejemplo (sin backend todavía).
> Sirve para validar el flujo y la interfaz antes de conectar base de datos,
> inicio de sesión y pagos reales.

## Deportes incluidos

⚽ Fútbol · ⚾ Béisbol · 🏀 Básquetbol · 🏐 Voleibol

## Vistas

- **Panel del dueño** — KPIs de la plataforma (ingreso recurrente / MRR,
  número de ligas, equipos totales, volumen cobrado a papás), gráficas y
  listado de ligas suscritas.
- **Ligas** — buscador y filtro por deporte; tarjeta de cada liga con su plan
  y renta mensual. Al abrir una liga:
  - **Posiciones** — tabla ordenada (puntos en fútbol, % de victorias en el
    resto).
  - **Partidos** — calendario con resultados (ganados/perdidos) y próximos
    juegos.
  - **Equipos** — ganados, perdidos y empates por equipo.
- **Pagos** — suscripciones que pagan las ligas (lo que te rentan) y los pagos
  de papás/tutores (inscripciones, cuotas, uniformes).

## Cómo correrlo

```bash
npm install
npm run dev      # servidor de desarrollo
npm run build    # build de producción
npm run lint     # revisión de código
```

## Estructura

```
src/
  App.jsx                  # shell + navegación de la app de ligas
  data/mockData.js         # ligas, equipos, partidos y pagos de ejemplo
  utils.js                 # formato de moneda y cálculo de posiciones
  components/
    ui.jsx                 # tarjetas, badges, etc.
    OwnerDashboard.jsx     # panel del dueño de la plataforma
    LeaguesView.jsx        # listado y filtro de ligas
    LeagueDetail.jsx       # posiciones, partidos y equipos de una liga
    PaymentsView.jsx       # suscripciones y pagos de papás
  S4BFinanceDashboard.jsx  # dashboard financiero original (referencia)
```

## Próximos pasos sugeridos

1. **Backend y base de datos** (p. ej. Supabase) para guardar ligas, equipos
   y resultados reales.
2. **Inicio de sesión y roles** (dueño de plataforma / admin de liga / papás).
3. **Pagos reales** (Stripe / Mercado Pago) para suscripciones de ligas y
   cobros a papás.
4. **Multi-liga real** (cada liga ve solo sus datos).
