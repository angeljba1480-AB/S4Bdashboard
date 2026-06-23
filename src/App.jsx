import { useState } from 'react'
import { LayoutDashboard, Building2, CreditCard, Trophy } from 'lucide-react'
import { leagues } from './data/mockData'
import OwnerDashboard from './components/OwnerDashboard'
import LeaguesView from './components/LeaguesView'
import LeagueDetail from './components/LeagueDetail'
import PaymentsView from './components/PaymentsView'

const NAV = [
  { id: 'dashboard', label: 'Panel', icon: LayoutDashboard },
  { id: 'leagues', label: 'Ligas', icon: Building2 },
  { id: 'payments', label: 'Pagos', icon: CreditCard },
]

export default function App() {
  const [view, setView] = useState('dashboard')
  const [openLeagueId, setOpenLeagueId] = useState(null)

  const openLeague = (id) => {
    setOpenLeagueId(id)
    setView('leagues')
  }
  const goTo = (id) => {
    setOpenLeagueId(null)
    setView(id)
  }

  const activeLeague = leagues.find((l) => l.id === openLeagueId)

  return (
    <div className="min-h-screen bg-slate-50 text-slate-900">
      {/* Sidebar (escritorio) */}
      <aside className="fixed inset-y-0 left-0 hidden w-60 flex-col border-r border-slate-200 bg-white px-4 py-6 lg:flex">
        <div className="flex items-center gap-2 px-2">
          <div className="flex h-9 w-9 items-center justify-center rounded-xl bg-indigo-600 text-white">
            <Trophy className="h-5 w-5" />
          </div>
          <div>
            <div className="text-sm font-bold leading-tight">S4B Ligas</div>
            <div className="text-xs text-slate-400">Admin de Ligas</div>
          </div>
        </div>
        <nav className="mt-8 flex flex-col gap-1">
          {NAV.map((item) => {
            const active = view === item.id
            return (
              <button
                key={item.id}
                onClick={() => goTo(item.id)}
                className={`flex items-center gap-3 rounded-xl px-3 py-2.5 text-sm font-medium transition ${
                  active ? 'bg-indigo-50 text-indigo-700' : 'text-slate-600 hover:bg-slate-50'
                }`}
              >
                <item.icon className="h-5 w-5" /> {item.label}
              </button>
            )
          })}
        </nav>
        <div className="mt-auto rounded-xl bg-slate-900 p-4 text-white">
          <div className="text-xs font-semibold">Prototipo</div>
          <p className="mt-1 text-xs text-slate-300">Datos de ejemplo. Multideporte: ⚽ ⚾ 🏀 🏐</p>
        </div>
      </aside>

      {/* Navegación superior (móvil) */}
      <div className="sticky top-0 z-10 flex items-center gap-1 border-b border-slate-200 bg-white px-3 py-2 lg:hidden">
        <div className="mr-2 flex items-center gap-2">
          <div className="flex h-8 w-8 items-center justify-center rounded-lg bg-indigo-600 text-white">
            <Trophy className="h-4 w-4" />
          </div>
          <span className="text-sm font-bold">S4B Ligas</span>
        </div>
        {NAV.map((item) => (
          <button
            key={item.id}
            onClick={() => goTo(item.id)}
            className={`rounded-lg px-3 py-1.5 text-sm font-medium ${
              view === item.id ? 'bg-indigo-50 text-indigo-700' : 'text-slate-600'
            }`}
          >
            {item.label}
          </button>
        ))}
      </div>

      {/* Contenido */}
      <main className="px-4 py-6 sm:px-8 lg:ml-60">
        <div className="mx-auto max-w-6xl">
          {view === 'dashboard' && <OwnerDashboard leagues={leagues} onOpenLeague={openLeague} />}
          {view === 'leagues' && activeLeague && (
            <LeagueDetail league={activeLeague} onBack={() => setOpenLeagueId(null)} />
          )}
          {view === 'leagues' && !activeLeague && (
            <LeaguesView leagues={leagues} onOpenLeague={openLeague} />
          )}
          {view === 'payments' && <PaymentsView leagues={leagues} />}
        </div>
      </main>
    </div>
  )
}
