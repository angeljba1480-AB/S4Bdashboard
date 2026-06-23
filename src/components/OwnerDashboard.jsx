import {
  LineChart, Line, XAxis, YAxis, Tooltip, ResponsiveContainer, CartesianGrid,
  BarChart, Bar,
} from 'recharts'
import { Building2, DollarSign, Users, TrendingUp, ArrowRight } from 'lucide-react'
import { Card, StatCard, Badge, SportBadge } from './ui'
import { SPORTS, monthlyRevenue, parentPayments } from '../data/mockData'
import { mxn, mrr, planLabel, planPrice } from '../utils'

export default function OwnerDashboard({ leagues, onOpenLeague }) {
  const activeLeagues = leagues.filter((l) => l.status === 'active')
  const totalTeams = leagues.reduce((s, l) => s + l.teams.length, 0)
  const platformMrr = mrr(leagues)
  const parentVolume = parentPayments
    .filter((p) => p.status === 'paid')
    .reduce((s, p) => s + p.amount, 0)

  const bySport = Object.values(SPORTS).map((sp) => ({
    name: sp.label,
    ligas: leagues.filter((l) => l.sport === sp.id).length,
    fill: sp.color,
  }))

  return (
    <div className="space-y-6">
      <div>
        <h1 className="text-2xl font-bold text-slate-900">Panel del dueño</h1>
        <p className="text-sm text-slate-500">Resumen de todas las ligas que rentan la plataforma.</p>
      </div>

      <div className="grid grid-cols-1 gap-4 sm:grid-cols-2 lg:grid-cols-4">
        <StatCard icon={DollarSign} label="Ingreso mensual (MRR)" value={mxn(platformMrr)}
          hint={`${activeLeagues.length} ligas activas`} accent="text-emerald-600" />
        <StatCard icon={Building2} label="Ligas" value={leagues.length}
          hint="Clientes en la plataforma" accent="text-indigo-600" />
        <StatCard icon={Users} label="Equipos totales" value={totalTeams}
          hint="En todas las ligas" accent="text-sky-600" />
        <StatCard icon={TrendingUp} label="Cobrado a papás" value={mxn(parentVolume)}
          hint="Volumen procesado este mes" accent="text-amber-600" />
      </div>

      <div className="grid grid-cols-1 gap-6 lg:grid-cols-3">
        <Card className="p-5 lg:col-span-2">
          <h2 className="text-sm font-semibold text-slate-700">Ingreso recurrente mensual</h2>
          <div className="mt-4 h-64">
            <ResponsiveContainer width="100%" height="100%">
              <LineChart data={monthlyRevenue} margin={{ left: -10, right: 10 }}>
                <CartesianGrid strokeDasharray="3 3" stroke="#eef2f7" />
                <XAxis dataKey="month" tick={{ fontSize: 12, fill: '#94a3b8' }} />
                <YAxis tick={{ fontSize: 12, fill: '#94a3b8' }} />
                <Tooltip formatter={(v) => mxn(v)} />
                <Line type="monotone" dataKey="mrr" stroke="#4f46e5" strokeWidth={3} dot={{ r: 4 }} />
              </LineChart>
            </ResponsiveContainer>
          </div>
        </Card>

        <Card className="p-5">
          <h2 className="text-sm font-semibold text-slate-700">Ligas por deporte</h2>
          <div className="mt-4 h-64">
            <ResponsiveContainer width="100%" height="100%">
              <BarChart data={bySport} margin={{ left: -20, right: 10 }}>
                <CartesianGrid strokeDasharray="3 3" stroke="#eef2f7" />
                <XAxis dataKey="name" tick={{ fontSize: 11, fill: '#94a3b8' }} />
                <YAxis allowDecimals={false} tick={{ fontSize: 12, fill: '#94a3b8' }} />
                <Tooltip />
                <Bar dataKey="ligas" radius={[6, 6, 0, 0]} />
              </BarChart>
            </ResponsiveContainer>
          </div>
        </Card>
      </div>

      <Card>
        <div className="flex items-center justify-between border-b border-slate-100 px-5 py-4">
          <h2 className="text-sm font-semibold text-slate-700">Ligas suscritas</h2>
        </div>
        <div className="divide-y divide-slate-100">
          {leagues.map((l) => {
            const sport = SPORTS[l.sport]
            return (
              <button
                key={l.id}
                onClick={() => onOpenLeague(l.id)}
                className="flex w-full items-center justify-between gap-4 px-5 py-4 text-left transition hover:bg-slate-50"
              >
                <div className="min-w-0">
                  <div className="flex items-center gap-2">
                    <span className="truncate font-semibold text-slate-900">{l.name}</span>
                    <SportBadge sport={sport} />
                  </div>
                  <div className="mt-0.5 text-xs text-slate-500">
                    {l.city} · Admin: {l.admin} · {l.teams.length} equipos
                  </div>
                </div>
                <div className="flex shrink-0 items-center gap-4">
                  <div className="hidden text-right sm:block">
                    <div className="text-sm font-semibold text-slate-900">{mxn(planPrice(l.plan))}/mes</div>
                    <div className="text-xs text-slate-400">Plan {planLabel(l.plan)}</div>
                  </div>
                  <Badge status={l.status} />
                  <ArrowRight className="h-4 w-4 text-slate-400" />
                </div>
              </button>
            )
          })}
        </div>
      </Card>
    </div>
  )
}
