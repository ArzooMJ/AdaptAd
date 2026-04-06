import { useEffect, useState } from 'react'
import { dataApi, simulateApi, type User, type ContentItem, type SimulationResult } from '../api/client'
import { AreaChart, Area, XAxis, YAxis, CartesianGrid, Tooltip, ResponsiveContainer, Bar, BarChart, Legend } from 'recharts'
import DecisionBadge from '../components/DecisionBadge'
import FatigueMeter from '../components/FatigueMeter'
import SessionTimeline from '../components/SessionTimeline'
import { useStore } from '../store'

export default function SessionSimulator() {
  const activeChromosomeGenes = useStore((s) => s.chromosomeGenes)
  const [users, setUsers] = useState<User[]>([])
  const [content, setContent] = useState<ContentItem[]>([])
  const [userId, setUserId] = useState(1)
  const [contentId, setContentId] = useState(1)
  const [time, setTime] = useState('evening')
  const [season, setSeason] = useState('Fall')
  const [result, setResult] = useState<SimulationResult | null>(null)
  const [loading, setLoading] = useState(false)
  const [error, setError] = useState<string | null>(null)
  const [playheadMinute, setPlayheadMinute] = useState(0)
  const [playing, setPlaying] = useState(false)

  useEffect(() => {
    dataApi.getUsers(200).then((r) => { setUsers(r.data.users); if (r.data.users[0]) setUserId(r.data.users[0].id) }).catch(() => {})
    dataApi.getContent(100).then((r) => { setContent(r.data.content); if (r.data.content[0]) setContentId(r.data.content[0].id) }).catch(() => {})
  }, [])

  useEffect(() => {
    if (!playing || !result) return
    if (playheadMinute >= result.content_duration_minutes) { setPlaying(false); return }
    const t = setTimeout(() => setPlayheadMinute((m) => m + 1), 120)
    return () => clearTimeout(t)
  }, [playing, playheadMinute, result])

  async function runSimulation() {
    setLoading(true); setError(null); setResult(null); setPlayheadMinute(0); setPlaying(false)
    try {
      const r = await simulateApi.session({ user_id: userId, content_id: contentId, time_of_day: time, season })
      setResult(r.data)
    } catch { setError('Simulation failed. Is the server running?') }
    finally { setLoading(false) }
  }

  const selectedContent = content.find((c) => c.id === contentId)
  const selectedUser = users.find((u) => u.id === userId)
  const policyGenes = result?.chromosome_genes ?? activeChromosomeGenes

  const fatigueSensitivity = policyGenes?.[0] ?? null
  const relevanceSensitivity = policyGenes?.[1] ?? null
  const delayBias = policyGenes?.[4] ?? null
  const softenBias = policyGenes?.[5] ?? null

  const splitAndNormalize = (items: string[]) =>
    items
      .flatMap((item) => item.split(/[,&/|]/g))
      .map((token) => token.trim().toLowerCase())
      .filter(Boolean)

  const contentPreferenceTokens = splitAndNormalize(selectedUser?.content_preferences ?? [])
  const selectedContentTokens = splitAndNormalize([selectedContent?.genre ?? ''])
  const matchedGenres = selectedContentTokens.filter((token) => contentPreferenceTokens.includes(token))
  const preferenceMatch = matchedGenres.length > 0

  const topAdInterests = selectedUser?.interests?.slice(0, 3) ?? []
  const topContentPreferences = selectedUser?.content_preferences?.slice(0, 4) ?? []

  function levelLabel(value: number | null) {
    if (value == null) return 'n/a'
    if (value >= 0.67) return 'high'
    if (value >= 0.34) return 'mid'
    return 'low'
  }

  return (
    <div className="space-y-6">
      <div className="page-header">
        <h1 className="page-title">Session Simulator</h1>
        <p className="page-sub">Simulate a full streaming session and see every ad decision</p>
      </div>

      <div className="grid grid-cols-1 lg:grid-cols-3 gap-4">
        <div className="card space-y-3 lg:col-span-1">
          <h2 className="section-title">Setup</h2>
          <div>
            <label className="label">User</label>
            <select className="select-input w-full mt-1" value={userId} onChange={(e) => setUserId(Number(e.target.value))}>
              {users.map((u) => <option key={u.id} value={u.id}>{u.name} ({u.age_group})</option>)}
            </select>
          </div>
          <div>
            <label className="label">Content</label>
            <select className="select-input w-full mt-1" value={contentId} onChange={(e) => setContentId(Number(e.target.value))}>
              {content.map((c) => <option key={c.id} value={c.id}>{c.title}</option>)}
            </select>
            {selectedContent && (
              <p className="text-xs text-zinc-500 mt-1.5">{selectedContent.genre} · {selectedContent.duration_minutes}min · {selectedContent.mood}</p>
            )}
          </div>
          <div className="grid grid-cols-2 gap-2">
            <div>
              <label className="label">Time</label>
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
          </div>
          <button className="btn-primary w-full" onClick={runSimulation} disabled={loading}>
            {loading ? 'Simulating…' : 'Run Simulation'}
          </button>

          <div className="rounded-xl border border-violet-900/30 bg-violet-950/10 p-4 sm:p-5 space-y-4">
            <div>
              <p className="label">Viewer Context</p>
              <p className="text-xs text-zinc-500 mt-2 leading-relaxed">Explains why SHOW, DELAY, SOFTEN, or SUPPRESS can happen for this profile.</p>
            </div>

            <div className="space-y-2 text-xs text-zinc-400 leading-relaxed">
              <p>
                <span className="text-zinc-500">Profession:</span>{' '}
                <span className="text-zinc-300">{selectedUser?.profession || '—'}</span>
              </p>
              <p>
                <span className="text-zinc-500">Ad category interests:</span>{' '}
                <span className="text-zinc-300">{topAdInterests.join(', ') || '—'}</span>
              </p>
              <p>
                <span className="text-zinc-500">Preferred watch time:</span>{' '}
                <span className="text-zinc-300">{selectedUser?.preferred_watch_time || '—'}</span>
              </p>
              <p>
                <span className="text-zinc-500">Favorite content categories:</span>{' '}
                <span className="text-zinc-300">{topContentPreferences.join(', ') || '—'}</span>
              </p>
            </div>

            <div className="pt-3 border-t border-violet-900/20 space-y-2.5">
              <p className="text-[11px] uppercase tracking-widest text-zinc-500">Policy Signals</p>
              <div className="grid grid-cols-2 gap-2.5 text-xs">
                <div className="rounded-lg border border-violet-900/20 px-2.5 py-2">
                  <p className="text-zinc-500">Fatigue weight</p>
                  <p className="font-mono text-zinc-300 mt-0.5">{fatigueSensitivity != null ? fatigueSensitivity.toFixed(2) : '—'} ({levelLabel(fatigueSensitivity)})</p>
                </div>
                <div className="rounded-lg border border-violet-900/20 px-2.5 py-2">
                  <p className="text-zinc-500">Relevance weight</p>
                  <p className="font-mono text-zinc-300 mt-0.5">{relevanceSensitivity != null ? relevanceSensitivity.toFixed(2) : '—'} ({levelLabel(relevanceSensitivity)})</p>
                </div>
                <div className="rounded-lg border border-violet-900/20 px-2.5 py-2">
                  <p className="text-zinc-500">Delay bias</p>
                  <p className="font-mono text-zinc-300 mt-0.5">{delayBias != null ? delayBias.toFixed(2) : '—'} ({levelLabel(delayBias)})</p>
                </div>
                <div className="rounded-lg border border-violet-900/20 px-2.5 py-2">
                  <p className="text-zinc-500">Soften bias</p>
                  <p className="font-mono text-zinc-300 mt-0.5">{softenBias != null ? softenBias.toFixed(2) : '—'} ({levelLabel(softenBias)})</p>
                </div>
              </div>
            </div>

            <div className="pt-3 border-t border-violet-900/20 text-xs text-zinc-400 space-y-1.5 leading-relaxed">
              <p>
                Current context: {time} in {season}
                {selectedUser?.preferred_watch_time ? `, viewer prefers ${selectedUser.preferred_watch_time}` : ''}.
              </p>
              <p>
                Content match: {selectedContent?.genre || '—'}
                {selectedUser && selectedContent
                  ? (preferenceMatch
                    ? ` matches preferred category: ${matchedGenres[0]}.`
                    : ' is outside preferred categories.')
                  : '.'}
              </p>
              <p>
                {selectedUser && selectedUser.ad_tolerance < 0.4
                  ? 'Low ad tolerance profile: expect more DELAY/SUPPRESS as fatigue rises.'
                  : 'Moderate/high ad tolerance profile: policy can allow more SHOW/SOFTEN if relevance is strong.'}
              </p>
            </div>
          </div>

          {error && <p className="text-suppress text-sm">{error}</p>}
        </div>

        <div className="lg:col-span-2 space-y-4">
          {result ? (
            <>
              <div className="card">
                <div className="flex items-start justify-between mb-4 gap-3">
                  <div>
                    <p className="font-semibold text-zinc-800 dark:text-zinc-100">{result.content_title}</p>
                    <p className="text-xs text-zinc-500">{result.content_duration_minutes}min</p>
                  </div>
                  <div className="flex gap-2 shrink-0">
                    <button className="btn-secondary text-xs" onClick={() => { setPlayheadMinute(0); setPlaying(true) }}>
                      {playing ? 'Playing…' : 'Animate'}
                    </button>
                    {playing && <button className="btn-secondary text-xs" onClick={() => setPlaying(false)}>Pause</button>}
                  </div>
                </div>
                <SessionTimeline
                  durationMinutes={result.content_duration_minutes}
                  decisions={result.decisions}
                  currentMinute={playing ? playheadMinute : undefined}
                />
              </div>

              <FatigueMeter value={result.summary.final_fatigue} />

              <div className="card">
                <h3 className="section-title mb-3">Fatigue &amp; Ads Over Session</h3>
                <ResponsiveContainer width="100%" height={220}>
                  <AreaChart
                    data={result.decisions.map((d) => ({
                      min: `${d.break_minute}m`,
                      fatigue: parseFloat((d.fatigue_at_break * 100).toFixed(1)),
                      ads_shown: d.ads_shown_before,
                    }))}
                    margin={{ top: 8, right: 16, bottom: 0, left: 0 }}
                  >
                    <CartesianGrid strokeDasharray="3 3" stroke="#1e293b" />
                    <XAxis dataKey="min" stroke="#475569" tick={{ fontSize: 11, fill: '#64748b' }} />
                    <YAxis yAxisId="left" stroke="#475569" tick={{ fontSize: 11, fill: '#64748b' }} tickFormatter={(v) => `${v}%`} domain={[0, 100]} />
                    <YAxis yAxisId="right" orientation="right" stroke="#475569" tick={{ fontSize: 11, fill: '#64748b' }} allowDecimals={false} />
                    <Tooltip
                      contentStyle={{ background: '#0f172a', border: '1px solid #1e293b', borderRadius: 8 }}
                      labelStyle={{ color: '#cbd5e1' }}
                      formatter={(v: number, name: string) => [name === 'fatigue' ? `${v}%` : v, name === 'fatigue' ? 'Fatigue' : 'Ads shown']}
                    />
                    <Legend wrapperStyle={{ fontSize: 12, color: '#64748b' }} />
                    <Area yAxisId="left" type="monotone" dataKey="fatigue" stroke="#f97316" fill="#f9731620" strokeWidth={2} dot={false} name="fatigue" />
                    <Area yAxisId="right" type="monotone" dataKey="ads_shown" stroke="#0ea5e9" fill="#0ea5e920" strokeWidth={2} dot={false} name="ads_shown" />
                  </AreaChart>
                </ResponsiveContainer>
              </div>

              <div className="card">
                <h3 className="section-title mb-3">Summary</h3>
                <div className="grid grid-cols-2 sm:grid-cols-4 gap-3">
                  {Object.entries(result.summary.decision_counts).map(([d, count]) => (
                    <div key={d} className="text-center">
                      <p className="text-xl font-bold font-mono text-zinc-800 dark:text-zinc-100">{count}</p>
                      <div className="mt-1"><DecisionBadge decision={d} size="sm" /></div>
                    </div>
                  ))}
                </div>
              </div>

              <div className="card">
                <h3 className="section-title mb-3">Break-by-break</h3>
                <div className="space-y-0">
                  {result.decisions.map((d, i) => (
                    <div key={i} className="flex items-center gap-3 text-sm py-2 border-b border-violet-900/20 last:border-0 flex-wrap">
                      <span className="text-zinc-600 w-8 font-mono text-xs">{d.break_minute}m</span>
                      <DecisionBadge decision={d.decision} size="sm" />
                      <span className="text-zinc-500 text-xs">{d.ad_category}</span>
                      <span className="ml-auto font-mono text-xs text-zinc-600">score {d.combined_score.toFixed(3)}</span>
                      <span className="font-mono text-xs text-zinc-600">fat {d.fatigue_at_break.toFixed(2)}</span>
                    </div>
                  ))}
                </div>
              </div>
            </>
          ) : (
            <div className="card h-64 flex items-center justify-center text-zinc-600 text-sm">
              Run a simulation to see the session timeline
            </div>
          )}
        </div>
      </div>
    </div>
  )
}
