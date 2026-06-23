import { useState } from 'react'
import { ArrowLeft, Trophy, CalendarDays, Users } from 'lucide-react'
import { Card, Badge, SportBadge } from './ui'
import { SPORTS } from '../data/mockData'
import { standings, mxn, planLabel, planPrice } from '../utils'

export default function LeagueDetail({ league, onBack }) {
  const [tab, setTab] = useState('standings')
  const sport = SPORTS[league.sport]
  const isSoccer = league.sport === 'futbol'
  const table = standings(league)

  return (
    <div className="space-y-6">
      <button onClick={onBack} className="inline-flex items-center gap-1.5 text-sm font-medium text-slate-500 hover:text-slate-800">
        <ArrowLeft className="h-4 w-4" /> Volver a ligas
      </button>

      <div className="flex flex-col gap-3 sm:flex-row sm:items-center sm:justify-between">
        <div>
          <div className="flex items-center gap-2">
            <h1 className="text-2xl font-bold text-slate-900">{league.name}</h1>
            <SportBadge sport={sport} />
          </div>
          <p className="text-sm text-slate-500">{league.city} · Admin: {league.admin}</p>
        </div>
        <div className="flex items-center gap-3">
          <div className="text-right">
            <div className="text-sm font-semibold text-slate-900">{mxn(planPrice(league.plan))}/mes</div>
            <div className="text-xs text-slate-400">Plan {planLabel(league.plan)}</div>
          </div>
          <Badge status={league.status} />
        </div>
      </div>

      <div className="flex gap-1 rounded-xl bg-slate-100 p-1">
        <Tab icon={Trophy} active={tab === 'standings'} onClick={() => setTab('standings')}>Posiciones</Tab>
        <Tab icon={CalendarDays} active={tab === 'matches'} onClick={() => setTab('matches')}>Partidos</Tab>
        <Tab icon={Users} active={tab === 'teams'} onClick={() => setTab('teams')}>Equipos</Tab>
      </div>

      {tab === 'standings' && <Standings table={table} isSoccer={isSoccer} />}
      {tab === 'matches' && <Matches matches={league.matches} />}
      {tab === 'teams' && <Teams table={table} />}
    </div>
  )
}

function Tab({ icon: Icon, active, onClick, children }) {
  return (
    <button
      onClick={onClick}
      className={`inline-flex flex-1 items-center justify-center gap-1.5 rounded-lg py-2 text-sm font-semibold transition ${
        active ? 'bg-white text-slate-900 shadow-sm' : 'text-slate-500 hover:text-slate-700'
      }`}
    >
      <Icon className="h-4 w-4" /> {children}
    </button>
  )
}

function Standings({ table, isSoccer }) {
  return (
    <Card className="overflow-hidden">
      <table className="w-full text-sm">
        <thead className="bg-slate-50 text-xs uppercase text-slate-400">
          <tr>
            <th className="px-4 py-3 text-left">#</th>
            <th className="px-4 py-3 text-left">Equipo</th>
            <th className="px-3 py-3 text-center">PJ</th>
            <th className="px-3 py-3 text-center text-emerald-600">G</th>
            <th className="px-3 py-3 text-center text-rose-600">P</th>
            {isSoccer && <th className="px-3 py-3 text-center">E</th>}
            <th className="px-3 py-3 text-center">Dif</th>
            <th className="px-4 py-3 text-center">{isSoccer ? 'Pts' : '% Vict.'}</th>
          </tr>
        </thead>
        <tbody className="divide-y divide-slate-100">
          {table.map((t, i) => (
            <tr key={t.id} className={i === 0 ? 'bg-amber-50/50' : ''}>
              <td className="px-4 py-3 font-semibold text-slate-400">{i + 1}</td>
              <td className="px-4 py-3 font-semibold text-slate-900">{t.name}</td>
              <td className="px-3 py-3 text-center text-slate-600">{t.played}</td>
              <td className="px-3 py-3 text-center font-semibold text-emerald-600">{t.wins}</td>
              <td className="px-3 py-3 text-center font-semibold text-rose-600">{t.losses}</td>
              {isSoccer && <td className="px-3 py-3 text-center text-slate-600">{t.draws}</td>}
              <td className="px-3 py-3 text-center text-slate-600">{t.diff > 0 ? `+${t.diff}` : t.diff}</td>
              <td className="px-4 py-3 text-center font-bold text-slate-900">
                {isSoccer ? t.points : `${Math.round(t.winPct * 100)}%`}
              </td>
            </tr>
          ))}
        </tbody>
      </table>
    </Card>
  )
}

function Matches({ matches }) {
  return (
    <div className="space-y-3">
      {matches.map((m) => {
        const done = m.status === 'finished'
        const homeWon = done && m.homeScore > m.awayScore
        const awayWon = done && m.awayScore > m.homeScore
        return (
          <Card key={m.id} className="flex items-center justify-between gap-4 p-4">
            <span className="w-24 text-xs text-slate-400">{m.date}</span>
            <div className="flex flex-1 items-center justify-center gap-3 sm:gap-5">
              <span className={`flex-1 text-right text-sm font-medium ${homeWon ? 'text-slate-900' : 'text-slate-500'}`}>
                {m.home}
              </span>
              <span className="rounded-lg bg-slate-100 px-3 py-1 text-sm font-bold text-slate-900 tabular-nums">
                {done ? `${m.homeScore} - ${m.awayScore}` : 'vs'}
              </span>
              <span className={`flex-1 text-left text-sm font-medium ${awayWon ? 'text-slate-900' : 'text-slate-500'}`}>
                {m.away}
              </span>
            </div>
            <Badge status={m.status} />
          </Card>
        )
      })}
    </div>
  )
}

function Teams({ table }) {
  return (
    <div className="grid grid-cols-1 gap-4 sm:grid-cols-2 lg:grid-cols-3">
      {table.map((t) => (
        <Card key={t.id} className="p-5">
          <h3 className="font-semibold text-slate-900">{t.name}</h3>
          <p className="text-xs text-slate-500">DT: {t.coach}</p>
          <div className="mt-4 flex gap-4 text-center">
            <div>
              <div className="text-2xl font-bold text-emerald-600">{t.wins}</div>
              <div className="text-xs text-slate-400">Ganados</div>
            </div>
            <div>
              <div className="text-2xl font-bold text-rose-600">{t.losses}</div>
              <div className="text-xs text-slate-400">Perdidos</div>
            </div>
            <div>
              <div className="text-2xl font-bold text-slate-400">{t.draws}</div>
              <div className="text-xs text-slate-400">Empates</div>
            </div>
          </div>
        </Card>
      ))}
    </div>
  )
}
