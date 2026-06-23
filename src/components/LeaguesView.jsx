import { useState } from 'react'
import { Search, ArrowRight } from 'lucide-react'
import { Card, Badge, SportBadge } from './ui'
import { SPORTS } from '../data/mockData'
import { mxn, planLabel, planPrice } from '../utils'

export default function LeaguesView({ leagues, onOpenLeague }) {
  const [q, setQ] = useState('')
  const [sport, setSport] = useState('all')

  const filtered = leagues.filter((l) => {
    const matchesSport = sport === 'all' || l.sport === sport
    const matchesQ =
      l.name.toLowerCase().includes(q.toLowerCase()) ||
      l.city.toLowerCase().includes(q.toLowerCase()) ||
      l.admin.toLowerCase().includes(q.toLowerCase())
    return matchesSport && matchesQ
  })

  return (
    <div className="space-y-6">
      <div>
        <h1 className="text-2xl font-bold text-slate-900">Ligas</h1>
        <p className="text-sm text-slate-500">Administra los clientes que rentan la plataforma.</p>
      </div>

      <div className="flex flex-col gap-3 sm:flex-row sm:items-center">
        <div className="relative flex-1">
          <Search className="pointer-events-none absolute left-3 top-1/2 h-4 w-4 -translate-y-1/2 text-slate-400" />
          <input
            value={q}
            onChange={(e) => setQ(e.target.value)}
            placeholder="Buscar por nombre, ciudad o admin…"
            className="w-full rounded-xl border border-slate-200 bg-white py-2.5 pl-10 pr-3 text-sm outline-none focus:border-indigo-400 focus:ring-2 focus:ring-indigo-100"
          />
        </div>
        <div className="flex flex-wrap gap-2">
          <FilterChip active={sport === 'all'} onClick={() => setSport('all')}>Todos</FilterChip>
          {Object.values(SPORTS).map((sp) => (
            <FilterChip key={sp.id} active={sport === sp.id} onClick={() => setSport(sp.id)}>
              {sp.emoji} {sp.label}
            </FilterChip>
          ))}
        </div>
      </div>

      <div className="grid grid-cols-1 gap-4 md:grid-cols-2 xl:grid-cols-3">
        {filtered.map((l) => {
          const sp = SPORTS[l.sport]
          return (
            <Card key={l.id} className="flex flex-col p-5">
              <div className="flex items-start justify-between">
                <SportBadge sport={sp} />
                <Badge status={l.status} />
              </div>
              <h3 className="mt-3 font-semibold text-slate-900">{l.name}</h3>
              <p className="text-xs text-slate-500">{l.city}</p>
              <dl className="mt-4 grid grid-cols-2 gap-3 text-sm">
                <div>
                  <dt className="text-xs text-slate-400">Admin</dt>
                  <dd className="font-medium text-slate-700">{l.admin}</dd>
                </div>
                <div>
                  <dt className="text-xs text-slate-400">Equipos</dt>
                  <dd className="font-medium text-slate-700">{l.teams.length}</dd>
                </div>
                <div>
                  <dt className="text-xs text-slate-400">Plan</dt>
                  <dd className="font-medium text-slate-700">{planLabel(l.plan)}</dd>
                </div>
                <div>
                  <dt className="text-xs text-slate-400">Renta</dt>
                  <dd className="font-medium text-slate-700">{mxn(planPrice(l.plan))}/mes</dd>
                </div>
              </dl>
              <button
                onClick={() => onOpenLeague(l.id)}
                className="mt-5 inline-flex items-center justify-center gap-1.5 rounded-xl bg-slate-900 py-2.5 text-sm font-semibold text-white transition hover:bg-slate-700"
              >
                Abrir liga <ArrowRight className="h-4 w-4" />
              </button>
            </Card>
          )
        })}
      </div>

      {filtered.length === 0 && (
        <p className="py-12 text-center text-sm text-slate-400">No se encontraron ligas.</p>
      )}
    </div>
  )
}

function FilterChip({ active, onClick, children }) {
  return (
    <button
      onClick={onClick}
      className={`rounded-full px-3 py-1.5 text-sm font-medium transition ${
        active ? 'bg-indigo-600 text-white' : 'bg-white text-slate-600 ring-1 ring-slate-200 hover:bg-slate-50'
      }`}
    >
      {children}
    </button>
  )
}
