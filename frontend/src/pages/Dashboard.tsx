import { useEffect, useState, useRef } from 'react'
import { useNavigate } from 'react-router-dom'
import { dataApi } from '../api/client'
import { useStore } from '../store'
import ChromosomeViz from '../components/ChromosomeViz'

// ── count-up hook ─────────────────────────────────────────────────────────────
function useCountUp(target: number, duration = 900) {
  const [val, setVal] = useState(0)
  useEffect(() => {
    if (!target) return
    const start = performance.now()
    const raf = (now: number) => {
      const t = Math.min(1, (now - start) / duration)
      const ease = 1 - Math.pow(1 - t, 3)
      setVal(Math.round(target * ease))
      if (t < 1) requestAnimationFrame(raf)
    }
    requestAnimationFrame(raf)
  }, [target, duration])
  return val
}

// ── live ticker ───────────────────────────────────────────────────────────────
const TICKER_USERS  = ['Priya S.', 'Lucas M.', 'Yuki T.', 'Emeka O.', 'Sofia G.', 'James K.', 'Aisha N.', 'Felix W.', 'Sakura I.', 'Diego R.']
const TICKER_ADS    = ['tech', 'food', 'gaming', 'travel', 'fashion', 'health', 'finance', 'auto']
const TICKER_DECISIONS = [
  { label: 'SHOW',     color: 'text-show',     bg: 'bg-show/10 border-show/30' },
  { label: 'SOFTEN',   color: 'text-soften',   bg: 'bg-soften/10 border-soften/30' },
  { label: 'DELAY',    color: 'text-delay',    bg: 'bg-delay/10 border-delay/30' },
  { label: 'SUPPRESS', color: 'text-suppress', bg: 'bg-suppress/10 border-suppress/30' },
]
const TICKER_WEIGHTS = [0.40, 0.25, 0.15, 0.20]

function pickWeighted() {
  const r = Math.random()
  let acc = 0
  for (let i = 0; i < TICKER_WEIGHTS.length; i++) {
    acc += TICKER_WEIGHTS[i]
    if (r < acc) return TICKER_DECISIONS[i]
  }
  return TICKER_DECISIONS[0]
}

interface TickerEntry { id: number; user: string; ad: string; decision: typeof TICKER_DECISIONS[0]; minute: number }

function LiveTicker() {
  const [entries, setEntries] = useState<TickerEntry[]>([])
  const counterRef = useRef(0)

  useEffect(() => {
    function addEntry() {
      counterRef.current += 1
      const entry: TickerEntry = {
        id: counterRef.current,
        user: TICKER_USERS[Math.floor(Math.random() * TICKER_USERS.length)],
        ad: TICKER_ADS[Math.floor(Math.random() * TICKER_ADS.length)],
        decision: pickWeighted(),
        minute: Math.floor(Math.random() * 50) + 5,
      }
      setEntries(prev => [entry, ...prev].slice(0, 7))
    }

    addEntry()
    const interval = setInterval(addEntry, 1800)
    return () => clearInterval(interval)
  }, [])

  return (
    <div className="card overflow-hidden">
      <div className="flex items-center justify-between mb-4">
        <h2 className="section-title">Live Decision Stream</h2>
        <div className="flex items-center gap-2">
          <span className="w-2 h-2 rounded-full bg-[#00ff88] animate-pulse shadow-sm shadow-[#00ff88]/60" />
          <span className="text-xs text-[#00ff88] font-semibold tracking-wide">LIVE</span>
        </div>
      </div>
      <div className="space-y-1.5 min-h-[196px]">
        {entries.map((e, i) => (
          <div
            key={e.id}
            className={`flex items-center gap-3 px-3 py-2 rounded-xl border text-xs
              ${i === 0 ? 'animate-ticker-in bg-violet-500/5 border-violet-500/20' : 'border-transparent'}
              transition-all duration-300`}
          >
            <span className="text-slate-500 dark:text-zinc-600 font-mono w-5 text-right">{e.minute}m</span>
            <span className="text-slate-700 dark:text-zinc-300 font-medium shrink-0">{e.user}</span>
            <span className="text-slate-400 dark:text-zinc-500">·</span>
            <span className="text-slate-500 dark:text-zinc-500 shrink-0">{e.ad} ad</span>
            <span className="ml-auto">
              <span className={`px-2 py-0.5 rounded-md border text-[10px] font-bold tracking-widest ${e.decision.bg} ${e.decision.color}`}>
                {e.decision.label}
              </span>
            </span>
          </div>
        ))}
      </div>
    </div>
  )
}

// ── system status bar ─────────────────────────────────────────────────────────
function StatusBar({ health }: { health: { users: number; ads: number; content: number } | null }) {
  const items = [
    { label: 'Users',   value: health?.users,   color: 'bg-violet-400' },
    { label: 'Ads',     value: health?.ads,      color: 'bg-cyan-400' },
    { label: 'Content', value: health?.content,  color: 'bg-[#00ff88]' },
  ]
  return (
    <div className="flex items-center gap-4 flex-wrap">
      {items.map(item => (
        <div key={item.label} className="flex items-center gap-2">
          <span className={`w-1.5 h-1.5 rounded-full ${item.color}`} />
          <span className="text-xs text-slate-500 dark:text-zinc-500">{item.label}</span>
          <span className="text-xs font-mono font-semibold text-slate-700 dark:text-zinc-200">
            {item.value ?? '—'}
          </span>
        </div>
      ))}
      <div className="flex items-center gap-2 ml-auto">
        <span className="w-1.5 h-1.5 rounded-full bg-[#00ff88] animate-pulse" />
        <span className="text-xs text-[#00ff88] font-semibold">System online</span>
      </div>
    </div>
  )
}

// ── decision state cards ──────────────────────────────────────────────────────
const DECISION_META = [
  { d: 'SHOW',     color: 'show',     desc: 'Favorable conditions met',     icon: '▶' },
  { d: 'SOFTEN',   color: 'soften',   desc: 'Serve a shorter version',      icon: '◈' },
  { d: 'DELAY',    color: 'delay',    desc: 'Wait for a better moment',     icon: '⏸' },
  { d: 'SUPPRESS', color: 'suppress', desc: 'Skip — protect experience',    icon: '✕' },
] as const

// ── main ──────────────────────────────────────────────────────────────────────
export default function Dashboard() {
  const navigate = useNavigate()
  const fitness = useStore((s) => s.chromosomeFitness)
  const genes = useStore((s) => s.chromosomeGenes)
  const totalDecisions = useStore((s) => s.totalDecisions)
  const [health, setHealth] = useState<{ users: number; ads: number; content: number } | null>(null)

  useEffect(() => {
    dataApi.health().then((r) => setHealth(r.data)).catch(() => {})
  }, [])

  const animUsers     = useCountUp(health?.users ?? 0)
  const animAds       = useCountUp(health?.ads ?? 0)
  const animDecisions = useCountUp(totalDecisions)
  const fitnessDisplay = fitness != null ? fitness.toFixed(4) : '—'

  return (
    <div className="space-y-6 animate-fade-in">

      {/* ── Hero ── */}
      <div className="relative overflow-hidden rounded-2xl border border-[#00d4ff]/15 p-6 sm:p-8" style={{ backgroundColor: 'var(--bg-card-deep)' }}>
        {/* Decorative orbs */}
        <div className="absolute -top-10 -right-10 w-56 h-56 rounded-full bg-[#00d4ff]/8 blur-3xl pointer-events-none" />
        <div className="absolute -bottom-10 -left-10 w-56 h-56 rounded-full bg-[#00ff88]/6 blur-3xl pointer-events-none" />

        <div className="relative">
          <div className="flex items-center gap-2 mb-3">
            <span className="w-2 h-2 rounded-full bg-[#00ff88] animate-pulse shadow-sm shadow-[#00ff88]/60" />
            <span className="text-xs font-semibold text-[#00ff88] tracking-widest uppercase">System Active</span>
          </div>
          <h1 className="text-3xl sm:text-4xl font-bold tracking-tight mb-2">
            <span className="gradient-text">AdaptAd</span>
          </h1>
          <p className="text-slate-600 dark:text-zinc-400 text-sm sm:text-base max-w-lg leading-relaxed">
            Human-centered ad decision engine. Genetic algorithms evolve the optimal policy —
            balancing viewer satisfaction with advertiser revenue in real time.
          </p>

          <div className="mt-5 flex flex-wrap gap-2.5">
            <button className="btn-primary" onClick={() => navigate('/evolve')}>Run Evolution</button>
            <button className="btn-secondary" onClick={() => navigate('/simulate')}>Simulate Session</button>
            <button className="btn-secondary" onClick={() => navigate('/ab-test')}>Start A/B Test</button>
          </div>
        </div>
      </div>

      {/* ── Stats ── */}
      <div className="grid grid-cols-2 lg:grid-cols-4 gap-4">
        {/* Fitness */}
        <div className="card hover:border-[#00d4ff]/30 hover:shadow-glow-brand transition-all duration-300">
          <p className="label mb-3">Chromosome Fitness</p>
          <p className={`text-3xl font-bold font-mono ${fitness != null ? 'text-[#00d4ff] stat-glow-brand' : 'text-zinc-600'}`}>
            {fitnessDisplay}
          </p>
          <p className="text-xs text-zinc-500 mt-2">
            {fitness != null ? 'Evolved · loaded' : 'Run evolution first'}
          </p>
          {fitness != null && (
            <div className="mt-3 h-0.5 rounded-full overflow-hidden" style={{ backgroundColor: 'var(--border)' }}>
              <div className="h-full bg-gradient-to-r from-[#00d4ff] to-[#00ff88] rounded-full transition-all duration-1000"
                style={{ width: `${Math.min(100, fitness * 100).toFixed(1)}%` }} />
            </div>
          )}
        </div>

        {/* Decisions */}
        <div className="card hover:border-[#00ff88]/30 hover:shadow-glow-accent transition-all duration-300">
          <p className="label mb-3">Decisions Made</p>
          <p className="text-3xl font-bold font-mono text-[#00ff88] stat-glow-accent">{animDecisions}</p>
          <p className="text-xs text-zinc-500 mt-2">This session</p>
        </div>

        {/* Users */}
        <div className="card hover:border-[#1e3048] transition-all duration-300">
          <p className="label mb-3">Synthetic Users</p>
          <p className="text-3xl font-bold font-mono text-zinc-700 dark:text-zinc-200">{animUsers}</p>
          <p className="text-xs text-zinc-500 mt-2">12 countries · 7 age groups</p>
        </div>

        {/* Ads */}
        <div className="card hover:border-[#1e3048] transition-all duration-300">
          <p className="label mb-3">Ad Inventory</p>
          <p className="text-3xl font-bold font-mono text-zinc-700 dark:text-zinc-200">{animAds}</p>
          <p className="text-xs text-zinc-500 mt-2">8 categories · seasonal</p>
        </div>
      </div>

      {/* ── Decision states + Live ticker ── */}
      <div className="grid grid-cols-1 lg:grid-cols-2 gap-4">

        {/* Decision states */}
        <div className="card">
          <h2 className="section-title mb-4">Decision Engine States</h2>
          <div className="grid grid-cols-2 gap-3">
            {DECISION_META.map(({ d, color, desc, icon }) => (
              <div key={d}
                className={`relative overflow-hidden rounded-xl px-4 py-3.5 border
                  bg-${color}/5 border-${color}/20
                  hover:bg-${color}/10 hover:border-${color}/40
                  transition-all duration-300 group cursor-default`}
              >
                <div className="flex items-start justify-between mb-1.5">
                  <span className={`text-xs font-bold tracking-widest text-${color}`}>{d}</span>
                  <span className={`text-base text-${color} opacity-60 group-hover:opacity-100 transition-opacity`}>{icon}</span>
                </div>
                <p className={`text-xs text-${color}/70 leading-snug`}>{desc}</p>
                {/* animated corner glow on hover */}
                <div className={`absolute -bottom-4 -right-4 w-12 h-12 rounded-full bg-${color}/20 blur-xl opacity-0 group-hover:opacity-100 transition-opacity duration-500`} />
              </div>
            ))}
          </div>
        </div>

        {/* Live ticker */}
        <LiveTicker />
      </div>

      {/* ── System status ── */}
      <div className="card">
        <StatusBar health={health} />
      </div>

      {/* ── Chromosome ── */}
      {genes && (
        <div className="card animate-slide-up">
          <div className="flex items-center justify-between mb-1">
            <h2 className="section-title">Active Chromosome</h2>
            <span className="text-xs font-mono text-cyan-400 bg-cyan-400/10 border border-cyan-400/20 px-2.5 py-1 rounded-full">
              fitness {fitness?.toFixed(4)}
            </span>
          </div>
          <p className="text-xs text-slate-500 dark:text-zinc-500 mb-4">
            8 genes evolved by the GA — controlling when ads are shown, softened, delayed, or suppressed.
          </p>
          <ChromosomeViz genes={genes} fitness={fitness} />
        </div>
      )}
    </div>
  )
}
