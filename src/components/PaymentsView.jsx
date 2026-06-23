import { DollarSign, Repeat, CreditCard } from 'lucide-react'
import { Card, StatCard, Badge, SportBadge } from './ui'
import { SPORTS, parentPayments } from '../data/mockData'
import { mxn, mrr, planLabel, planPrice } from '../utils'

export default function PaymentsView({ leagues }) {
  const platformMrr = mrr(leagues)
  const paid = parentPayments.filter((p) => p.status === 'paid').reduce((s, p) => s + p.amount, 0)
  const pendingCount = parentPayments.filter((p) => p.status !== 'paid').length
  const leagueName = (id) => leagues.find((l) => l.id === id)?.name ?? id

  return (
    <div className="space-y-6">
      <div>
        <h1 className="text-2xl font-bold text-slate-900">Pagos y suscripciones</h1>
        <p className="text-sm text-slate-500">Lo que te rentan las ligas y lo que pagan los papás dentro de la app.</p>
      </div>

      <div className="grid grid-cols-1 gap-4 sm:grid-cols-3">
        <StatCard icon={Repeat} label="Renta de ligas (MRR)" value={mxn(platformMrr)}
          hint="Suscripciones activas" accent="text-emerald-600" />
        <StatCard icon={DollarSign} label="Pagos de papás (cobrado)" value={mxn(paid)}
          hint="Procesado este mes" accent="text-indigo-600" />
        <StatCard icon={CreditCard} label="Pagos por resolver" value={pendingCount}
          hint="Pendientes o rechazados" accent="text-amber-600" />
      </div>

      <Card>
        <div className="border-b border-slate-100 px-5 py-4">
          <h2 className="text-sm font-semibold text-slate-700">Suscripciones de ligas</h2>
          <p className="text-xs text-slate-400">Ingreso recurrente que paga cada liga por usar la plataforma.</p>
        </div>
        <div className="divide-y divide-slate-100">
          {leagues.map((l) => (
            <div key={l.id} className="flex items-center justify-between gap-4 px-5 py-4">
              <div className="flex items-center gap-3">
                <SportBadge sport={SPORTS[l.sport]} />
                <div>
                  <div className="font-medium text-slate-900">{l.name}</div>
                  <div className="text-xs text-slate-400">Plan {planLabel(l.plan)} · Desde {l.since}</div>
                </div>
              </div>
              <div className="flex items-center gap-4">
                <span className="text-sm font-semibold text-slate-900">{mxn(planPrice(l.plan))}/mes</span>
                <Badge status={l.status} />
              </div>
            </div>
          ))}
        </div>
      </Card>

      <Card className="overflow-hidden">
        <div className="border-b border-slate-100 px-5 py-4">
          <h2 className="text-sm font-semibold text-slate-700">Pagos de papás / tutores</h2>
          <p className="text-xs text-slate-400">Inscripciones, cuotas y uniformes cobrados dentro de cada liga.</p>
        </div>
        <div className="overflow-x-auto">
          <table className="w-full text-sm">
            <thead className="bg-slate-50 text-xs uppercase text-slate-400">
              <tr>
                <th className="px-5 py-3 text-left">Padre/Tutor</th>
                <th className="px-3 py-3 text-left">Jugador</th>
                <th className="px-3 py-3 text-left">Liga</th>
                <th className="px-3 py-3 text-left">Concepto</th>
                <th className="px-3 py-3 text-left">Fecha</th>
                <th className="px-3 py-3 text-right">Monto</th>
                <th className="px-5 py-3 text-right">Estado</th>
              </tr>
            </thead>
            <tbody className="divide-y divide-slate-100">
              {parentPayments.map((p) => (
                <tr key={p.id}>
                  <td className="px-5 py-3 font-medium text-slate-900">{p.parent}</td>
                  <td className="px-3 py-3 text-slate-600">{p.player}</td>
                  <td className="px-3 py-3 text-slate-600">{leagueName(p.league)}</td>
                  <td className="px-3 py-3 text-slate-600">{p.concept}</td>
                  <td className="px-3 py-3 text-slate-400">{p.date}</td>
                  <td className="px-3 py-3 text-right font-semibold text-slate-900">{mxn(p.amount)}</td>
                  <td className="px-5 py-3 text-right"><Badge status={p.status} /></td>
                </tr>
              ))}
            </tbody>
          </table>
        </div>
      </Card>
    </div>
  )
}
