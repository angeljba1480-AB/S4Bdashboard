// Datos de ejemplo para el prototipo de S4B — Administración de Ligas multideporte.
// Todo es ficticio y sirve solo para demostrar el flujo de la plataforma.

export const SPORTS = {
  futbol: { id: 'futbol', label: 'Fútbol', emoji: '⚽', color: '#16a34a' },
  beisbol: { id: 'beisbol', label: 'Béisbol', emoji: '⚾', color: '#d97706' },
  basquetbol: { id: 'basquetbol', label: 'Básquetbol', emoji: '🏀', color: '#ea580c' },
  voleibol: { id: 'voleibol', label: 'Voleibol', emoji: '🏐', color: '#2563eb' },
}

// Planes de suscripción que las ligas te rentan.
export const PLANS = {
  basico: { id: 'basico', label: 'Básico', price: 499, maxTeams: 8 },
  pro: { id: 'pro', label: 'Pro', price: 999, maxTeams: 20 },
  elite: { id: 'elite', label: 'Élite', price: 1999, maxTeams: 60 },
}

// Ligas que rentan la plataforma (cada una es un "cliente" tuyo).
export const leagues = [
  {
    id: 'lg-1',
    name: 'Liga Infantil Monterrey',
    sport: 'futbol',
    city: 'Monterrey, NL',
    admin: 'Carlos Méndez',
    plan: 'pro',
    status: 'active',
    since: '2024-08-01',
    teams: [
      { id: 't1', name: 'Tigres FC', coach: 'L. Robles', wins: 8, losses: 1, draws: 2, gf: 24, ga: 9 },
      { id: 't2', name: 'Rayados Jr', coach: 'M. Salas', wins: 7, losses: 2, draws: 2, gf: 21, ga: 12 },
      { id: 't3', name: 'Halcones', coach: 'J. Pérez', wins: 5, losses: 4, draws: 2, gf: 17, ga: 16 },
      { id: 't4', name: 'Pumas Cachorros', coach: 'R. Díaz', wins: 3, losses: 6, draws: 2, gf: 11, ga: 19 },
      { id: 't5', name: 'Leones', coach: 'A. Vega', wins: 1, losses: 8, draws: 2, gf: 8, ga: 26 },
    ],
    matches: [
      { id: 'm1', date: '2026-06-20', home: 'Tigres FC', away: 'Leones', homeScore: 4, awayScore: 0, status: 'finished' },
      { id: 'm2', date: '2026-06-20', home: 'Rayados Jr', away: 'Halcones', homeScore: 2, awayScore: 2, status: 'finished' },
      { id: 'm3', date: '2026-06-27', home: 'Tigres FC', away: 'Rayados Jr', homeScore: null, awayScore: null, status: 'scheduled' },
      { id: 'm4', date: '2026-06-27', home: 'Pumas Cachorros', away: 'Halcones', homeScore: null, awayScore: null, status: 'scheduled' },
    ],
  },
  {
    id: 'lg-2',
    name: 'Liga de Béisbol Pequeñas Ligas GDL',
    sport: 'beisbol',
    city: 'Guadalajara, JAL',
    admin: 'Verónica Ruiz',
    plan: 'elite',
    status: 'active',
    since: '2024-03-15',
    teams: [
      { id: 't1', name: 'Charros Kids', coach: 'P. Luna', wins: 12, losses: 3, draws: 0, gf: 88, ga: 41 },
      { id: 't2', name: 'Mariachis', coach: 'O. Campos', wins: 10, losses: 5, draws: 0, gf: 74, ga: 52 },
      { id: 't3', name: 'Tequileros Jr', coach: 'S. Mora', wins: 8, losses: 7, draws: 0, gf: 66, ga: 60 },
      { id: 't4', name: 'Agaveros', coach: 'F. Nava', wins: 4, losses: 11, draws: 0, gf: 49, ga: 79 },
    ],
    matches: [
      { id: 'm1', date: '2026-06-21', home: 'Charros Kids', away: 'Agaveros', homeScore: 9, awayScore: 3, status: 'finished' },
      { id: 'm2', date: '2026-06-21', home: 'Mariachis', away: 'Tequileros Jr', homeScore: 5, awayScore: 6, status: 'finished' },
      { id: 'm3', date: '2026-06-28', home: 'Charros Kids', away: 'Mariachis', homeScore: null, awayScore: null, status: 'scheduled' },
    ],
  },
  {
    id: 'lg-3',
    name: 'Básquet Juvenil CDMX',
    sport: 'basquetbol',
    city: 'Ciudad de México',
    admin: 'Diego Fuentes',
    plan: 'pro',
    status: 'active',
    since: '2025-01-10',
    teams: [
      { id: 't1', name: 'Diablos', coach: 'N. Ortiz', wins: 9, losses: 2, draws: 0, gf: 712, ga: 588 },
      { id: 't2', name: 'Capitalinos', coach: 'E. Soto', wins: 7, losses: 4, draws: 0, gf: 660, ga: 631 },
      { id: 't3', name: 'Aztecas', coach: 'G. Reyes', wins: 6, losses: 5, draws: 0, gf: 640, ga: 645 },
      { id: 't4', name: 'Coyotes', coach: 'V. Cano', wins: 2, losses: 9, draws: 0, gf: 561, ga: 690 },
    ],
    matches: [
      { id: 'm1', date: '2026-06-19', home: 'Diablos', away: 'Coyotes', homeScore: 78, awayScore: 55, status: 'finished' },
      { id: 'm2', date: '2026-06-22', home: 'Capitalinos', away: 'Aztecas', homeScore: 64, awayScore: 61, status: 'finished' },
      { id: 'm3', date: '2026-06-29', home: 'Diablos', away: 'Capitalinos', homeScore: null, awayScore: null, status: 'scheduled' },
    ],
  },
  {
    id: 'lg-4',
    name: 'Voleibol Playero Cancún',
    sport: 'voleibol',
    city: 'Cancún, QR',
    admin: 'Mariana Cruz',
    plan: 'basico',
    status: 'pending', // pago de suscripción pendiente
    since: '2026-05-01',
    teams: [
      { id: 't1', name: 'Caribes', coach: 'T. Aguilar', wins: 6, losses: 1, draws: 0, gf: 18, ga: 7 },
      { id: 't2', name: 'Delfines', coach: 'B. Marín', wins: 4, losses: 3, draws: 0, gf: 14, ga: 12 },
      { id: 't3', name: 'Tiburones', coach: 'H. Quintero', wins: 1, losses: 7, draws: 0, gf: 6, ga: 19 },
    ],
    matches: [
      { id: 'm1', date: '2026-06-18', home: 'Caribes', away: 'Tiburones', homeScore: 2, awayScore: 0, status: 'finished' },
      { id: 'm2', date: '2026-06-25', home: 'Delfines', away: 'Caribes', homeScore: null, awayScore: null, status: 'scheduled' },
    ],
  },
]

// Pagos de papás/tutores (inscripciones y cuotas) dentro de las ligas.
export const parentPayments = [
  { id: 'p1', parent: 'Ana López', player: 'Mateo López', team: 'Tigres FC', league: 'lg-1', concept: 'Inscripción temporada', amount: 850, date: '2026-06-15', status: 'paid' },
  { id: 'p2', parent: 'Jorge Pérez', player: 'Sofía Pérez', team: 'Charros Kids', league: 'lg-2', concept: 'Cuota mensual', amount: 400, date: '2026-06-14', status: 'paid' },
  { id: 'p3', parent: 'Laura Gómez', player: 'Diego Gómez', team: 'Diablos', league: 'lg-3', concept: 'Uniforme', amount: 600, date: '2026-06-12', status: 'paid' },
  { id: 'p4', parent: 'Raúl Torres', player: 'Emma Torres', team: 'Caribes', league: 'lg-4', concept: 'Inscripción temporada', amount: 750, date: '2026-06-20', status: 'pending' },
  { id: 'p5', parent: 'Patricia Núñez', player: 'Luis Núñez', team: 'Rayados Jr', league: 'lg-1', concept: 'Cuota mensual', amount: 400, date: '2026-06-10', status: 'paid' },
  { id: 'p6', parent: 'Hugo Ramírez', player: 'Ian Ramírez', team: 'Mariachis', league: 'lg-2', concept: 'Cuota mensual', amount: 400, date: '2026-06-22', status: 'failed' },
]

// Ingresos mensuales de la plataforma (lo que te rentan las ligas).
export const monthlyRevenue = [
  { month: 'Ene', mrr: 3200 },
  { month: 'Feb', mrr: 3700 },
  { month: 'Mar', mrr: 4200 },
  { month: 'Abr', mrr: 4200 },
  { month: 'May', mrr: 4700 },
  { month: 'Jun', mrr: 5196 },
]
