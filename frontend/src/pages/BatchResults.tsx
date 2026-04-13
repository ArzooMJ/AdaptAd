import { useEffect, useState } from 'react'
import { dataApi, decideApi, type Ad } from '../api/client'
import {
  PieChart, Pie, Cell, Tooltip, ResponsiveContainer,
  BarChart, Bar, XAxis, YAxis, CartesianGrid,
} from 'recharts'
import DecisionBadge from '../components/DecisionBadge'

const DECISION_COLORS: Record<string, string> = {
  SHOW: '#00ff88', SWAP: '#38bdf8', SUPPRESS: '#ff2d55',
}

interface BatchRow {
  user_id: number; user_name: string; age_group: string
  decision: string; combined_score: number
}

// Custom donut centre label
function DonutLabel({ cx, cy, total }: { cx: number; cy: number; total: number }) {
  return (
    <g>
      <text x={cx} y={cy - 8} textAnchor="middle" fill="#e4e4e7" fontSize={28} fontWeight={700} fontFamily="JetBrains Mono, monospace">
        {total}
      </text>
      <text x={cx} y={cy + 14} textAnchor="middle" fill="#71717a" fontSize={11} fontFamily="Space Grotesk, sans-serif">
        users
      </text>
    </g>
  )
}

export default function BatchResults() {
  const [ads, setAds] = useState<Ad[]>([])
  const [adId, setAdId] = useState('')
  const [time, setTime] = useState('evening')
  const [season, setSeason] = useState('Fall')
  const [adsShown, setAdsShown] = useState(0)
  const [fatigue, setFatigue] = useState(0.2)
  const [rows, setRows] = useState<BatchRow[]>([])
  const [counts, setCounts] = useState<Record<string, number>>({})
  const [filter, setFilter] = useState<string>('ALL')
  const [loading, setLoading] = useState(false)
  const [error, setError] = useState<string | null>(null)

  useEffect(() => {
    dataApi.getAds(80).then((r) => { setAds(r.data.ads); if (r.data.ads[0]) setAdId(r.data.ads[0].id) }).catch(() => {})
  }, [])

  async function runBatch() {
    setLoading(true); setError(null)
    try {
      const r = await decideApi.batch({ ad_id: adId, time_of_day: time, season, ads_shown_this_session: adsShown, session_fatigue: fatigue })
      setRows(r.data.results)
      setCounts(r.data.decision_counts)
    } catch { setError('Batch failed. Is the server running?') }
    finally { setLoading(false) }
  }

  const pieData = Object.entries(counts)
    .map(([name, value]) => ({ name, value }))
    .filter((d) => d.value > 0)

  const filtered = filter === 'ALL' ? rows : rows.filter((r) => r.decision === filter)

  // Score distribution histogram (bucket into 0.1 ranges)
  const scoreBuckets = rows.length > 0 ? (() => {
    const buckets: Record<string, number> = {}
    for (let i = 0; i <= 9; i++) buckets[`${i/10}–${(i+1)/10}`] = 0
    rows.forEach(r => {
      const b = Math.min(9, Math.floor(r.combined_score * 10))
      const key = `${b/10}–${(b+1)/10}`
      buckets[key] = (buckets[key] || 0) + 1
    })
    return Object.entries(buckets).map(([range, count]) => ({ range, count }))
  })() : []

  const total = rows.length

  return (
    <div className="space-y-6">
      <div className="page-header">
        <h1 className="page-title">Batch Decisions</h1>
        <p className="page-sub">Run decisions for all 1,000 users simultaneously and see the distribution</p>
      </div>

      {/* Controls */}
      <div className="card space-y-4">
        <div className="grid grid-cols-1 sm:grid-cols-2 lg:grid-cols-4 gap-4">
          <div>
            <label className="label">Ad</label>
            <select className="select-input w-full mt-1" value={adId} onChange={(e) => setAdId(e.target.value)}>
              {ads.map((a) => <option key={a.id} value={a.id}>{a.id} — {a.category}</option>)}
            </select>
          </div>
          <div>
            <label className="label">Time of day</label>
            <select className="select-input w-full mt-1" value={time} onChange={(e) => setTime(e.target.value)}>
              {['morning','afternoon','evening','latenight'].map((t) => <option key={t}>{t}</option>)}
            </select>
          </div>
          <div>
            <label className="label">Season</label>
            <select className="select-input w-full mt-1" value={season} onChange={(e) => setSeason(e.target.value)}>
              {['Spring','Summer','Fall','Winter'].map((s) => <option key={s}>{s}</option>)}
            </select>
          </div>
          <div className="space-y-3">
            <div>
              <label className="label">Ads shown — <span className="text-[#00d4ff] font-mono normal-case">{adsShown}</span></label>
              <input type="range" min={0} max={5} value={adsShown} onChange={(e) => setAdsShown(Number(e.target.value))} className="w-full mt-1 accent-[#00d4ff]" />
            </div>
            <div>
              <label className="label">Fatigue — <span className="text-[#00d4ff] font-mono normal-case">{fatigue.toFixed(2)}</span></label>
              <input type="range" min={0} max={1} step={0.05} value={fatigue} onChange={(e) => setFatigue(Number(e.target.value))} className="w-full mt-1 accent-[#00d4ff]" />
            </div>
          </div>
        </div>
        <div className="flex items-center gap-3">
          <button className="btn-primary" onClick={runBatch} disabled={loading || !adId}>
            {loading ? 'Running…' : 'Run Batch'}
          </button>
          {error && <span className="text-[#ff2d55] text-sm">{error}</span>}
        </div>
      </div>

      {rows.length > 0 && (
        <>
          {/* Charts row */}
          <div className="grid grid-cols-1 lg:grid-cols-2 gap-4">

            {/* Donut — decision split */}
            <div className="card">
              <h2 className="section-title mb-4">Decision Split</h2>
              <div className="flex items-center gap-6">
                <ResponsiveContainer width={200} height={200}>
                  <PieChart>
                    <Pie
                      data={pieData} dataKey="value" nameKey="name"
                      cx="50%" cy="50%"
                      innerRadius={55} outerRadius={85}
                      paddingAngle={3}
                      label={false}
                    >
                      {pieData.map((entry) => (
                        <Cell key={entry.name} fill={DECISION_COLORS[entry.name] ?? '#3f3f46'} stroke="transparent" />
                      ))}
                    </Pie>
                    <Tooltip
                      contentStyle={{ background: '#0d1117', border: '1px solid #1a2332', borderRadius: 10, fontSize: 12 }}
                      formatter={(v: number) => [`${v} users (${((v/total)*100).toFixed(1)}%)`, '']}
                    />
                  </PieChart>
                </ResponsiveContainer>

                {/* Legend + counts */}
                <div className="flex-1 space-y-2.5">
                  {pieData.map(({ name, value }) => (
                    <div key={name} className="flex items-center justify-between gap-3">
                      <div className="flex items-center gap-2">
                        <span className="w-2.5 h-2.5 rounded-full shrink-0" style={{ backgroundColor: DECISION_COLORS[name] ?? '#3f3f46' }} />
                        <span className="text-xs font-semibold text-zinc-400 tracking-wider">{name}</span>
                      </div>
                      <div className="flex items-center gap-2">
                        <div className="w-20 h-1 rounded-full overflow-hidden" style={{ backgroundColor: 'var(--border)' }}>
                          <div className="h-full rounded-full" style={{ width: `${(value/total)*100}%`, backgroundColor: DECISION_COLORS[name] }} />
                        </div>
                        <span className="text-xs font-mono text-zinc-600 dark:text-zinc-300 w-8 text-right">{value}</span>
                        <span className="text-[10px] text-zinc-600 w-10">({((value/total)*100).toFixed(0)}%)</span>
                      </div>
                    </div>
                  ))}
                </div>
              </div>
            </div>

            {/* Score distribution */}
            <div className="card">
              <h2 className="section-title mb-4">Score Distribution</h2>
              <ResponsiveContainer width="100%" height={200}>
                <BarChart data={scoreBuckets} margin={{ top: 4, right: 8, bottom: 16, left: -20 }}>
                  <CartesianGrid strokeDasharray="3 3" stroke="#1a2332" vertical={false} />
                  <XAxis
                    dataKey="range"
                    tick={{ fontSize: 9, fill: '#52525b' }}
                    angle={-35}
                    textAnchor="end"
                    interval={0}
                    tickLine={false}
                    axisLine={{ stroke: '#1a2332' }}
                  />
                  <YAxis tick={{ fontSize: 10, fill: '#52525b' }} tickLine={false} axisLine={false} />
                  <Tooltip
                    contentStyle={{ background: '#0d1117', border: '1px solid #1a2332', borderRadius: 10, fontSize: 12 }}
                    formatter={(v: number) => [v, 'users']}
                    labelFormatter={(l) => `Score ${l}`}
                  />
                  <Bar dataKey="count" radius={[4, 4, 0, 0]}>
                    {scoreBuckets.map((entry, i) => {
                      const score = i / 10
                      const color = score >= 0.6 ? '#00ff88' : score >= 0.4 ? '#ffb800' : '#ff2d55'
                      return <Cell key={i} fill={color} opacity={0.85} />
                    })}
                  </Bar>
                </BarChart>
              </ResponsiveContainer>
            </div>
          </div>

          {/* Results table */}
          <div className="card">
            <div className="flex items-center gap-3 mb-4 flex-wrap">
              <h2 className="section-title">Per-user Results</h2>
              <span className="text-xs text-zinc-600 font-mono">{filtered.length} rows</span>
              <div className="ml-auto flex gap-2 flex-wrap">
                {['ALL','SHOW','SWAP','SUPPRESS'].map(d => (
                  <button key={d} onClick={() => setFilter(d)}
                    className={`px-3 py-1.5 rounded-lg text-xs font-semibold border transition-all ${
                      filter === d
                        ? 'border-[#00d4ff]/50 text-[#00d4ff] bg-[#00d4ff]/10'
                        : 'border-zinc-300 dark:border-[#1a2332] text-zinc-500 hover:border-zinc-500 dark:hover:border-zinc-600 hover:text-zinc-700 dark:hover:text-zinc-300'
                    }`}>
                    {d}
                  </button>
                ))}
              </div>
            </div>
            <div className="overflow-x-auto">
              <table className="w-full text-sm">
                <thead>
                  <tr className="border-b border-zinc-200 dark:border-[#1a2332]">
                    {['User', 'Age', 'Decision', 'Score'].map(h => (
                      <th key={h} className="pb-3 text-left text-[11px] text-zinc-500 font-semibold uppercase tracking-widest">{h}</th>
                    ))}
                  </tr>
                </thead>
                <tbody>
                  {filtered.slice(0, 50).map((r) => (
                    <tr key={r.user_id} className="border-b border-zinc-100 dark:border-[#0d1117] hover:bg-zinc-50 dark:hover:bg-[#0d1f2d]/60 transition-colors">
                      <td className="py-2.5 text-zinc-700 dark:text-zinc-200 text-xs">{r.user_name}</td>
                      <td className="py-2.5 text-zinc-500 text-xs font-mono">{r.age_group}</td>
                      <td className="py-2.5"><DecisionBadge decision={r.decision} size="sm" /></td>
                      <td className="py-2.5 font-mono text-xs">
                        <span className={`${
                          r.combined_score >= 0.6 ? 'text-[#00ff88]' :
                          r.combined_score >= 0.4 ? 'text-[#ffb800]' :
                          'text-[#ff2d55]'
                        }`}>{r.combined_score.toFixed(3)}</span>
                      </td>
                    </tr>
                  ))}
                </tbody>
              </table>
              {filtered.length > 50 && (
                <p className="text-xs text-zinc-600 mt-3 text-center">
                  Showing 50 of {filtered.length} results
                </p>
              )}
            </div>
          </div>
        </>
      )}
    </div>
  )
}
