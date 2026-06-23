// Componentes de UI reutilizables (estilo con Tailwind por CDN).

export function Card({ children, className = '' }) {
  return (
    <div className={`rounded-2xl border border-slate-200 bg-white shadow-sm ${className}`}>
      {children}
    </div>
  )
}

export function StatCard({ icon: Icon, label, value, hint, accent = 'text-indigo-600' }) {
  return (
    <Card className="p-5">
      <div className="flex items-center justify-between">
        <span className="text-sm font-medium text-slate-500">{label}</span>
        {Icon && <Icon className={`h-5 w-5 ${accent}`} />}
      </div>
      <div className="mt-2 text-3xl font-bold tracking-tight text-slate-900">{value}</div>
      {hint && <div className="mt-1 text-xs text-slate-400">{hint}</div>}
    </Card>
  )
}

const STATUS_STYLES = {
  active: 'bg-emerald-100 text-emerald-700',
  paid: 'bg-emerald-100 text-emerald-700',
  pending: 'bg-amber-100 text-amber-700',
  scheduled: 'bg-sky-100 text-sky-700',
  finished: 'bg-slate-100 text-slate-600',
  failed: 'bg-rose-100 text-rose-700',
}

const STATUS_LABELS = {
  active: 'Activa',
  paid: 'Pagado',
  pending: 'Pendiente',
  scheduled: 'Programado',
  finished: 'Finalizado',
  failed: 'Rechazado',
}

export function Badge({ status, children }) {
  const style = STATUS_STYLES[status] ?? 'bg-slate-100 text-slate-600'
  return (
    <span className={`inline-flex items-center rounded-full px-2.5 py-0.5 text-xs font-semibold ${style}`}>
      {children ?? STATUS_LABELS[status] ?? status}
    </span>
  )
}

export function SportBadge({ sport }) {
  return (
    <span
      className="inline-flex items-center gap-1.5 rounded-full px-2.5 py-0.5 text-xs font-semibold"
      style={{ backgroundColor: `${sport.color}1a`, color: sport.color }}
    >
      <span>{sport.emoji}</span>
      {sport.label}
    </span>
  )
}
