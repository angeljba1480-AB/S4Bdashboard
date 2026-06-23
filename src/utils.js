import { PLANS } from './data/mockData'

export const mxn = (n) =>
  new Intl.NumberFormat('es-MX', { style: 'currency', currency: 'MXN', maximumFractionDigits: 0 }).format(n)

// Tabla de posiciones ordenada. Para fútbol usa puntos (3/1/0); para el resto, % de victorias.
export function standings(league) {
  const isSoccer = league.sport === 'futbol'
  return [...league.teams]
    .map((t) => {
      const played = t.wins + t.losses + t.draws
      const points = t.wins * 3 + t.draws
      const winPct = played ? t.wins / played : 0
      return { ...t, played, points, winPct, diff: t.gf - t.ga }
    })
    .sort((a, b) =>
      isSoccer ? b.points - a.points || b.diff - a.diff : b.winPct - a.winPct || b.diff - a.diff
    )
}

export const planLabel = (id) => PLANS[id]?.label ?? id
export const planPrice = (id) => PLANS[id]?.price ?? 0

// Ingreso recurrente mensual (MRR) sumando solo ligas activas.
export function mrr(leagues) {
  return leagues
    .filter((l) => l.status === 'active')
    .reduce((sum, l) => sum + planPrice(l.plan), 0)
}
