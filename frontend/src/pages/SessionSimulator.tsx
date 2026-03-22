import { useEffect, useState } from 'react'
import { dataApi, simulateApi, type User, type ContentItem, type SimulationResult } from '../api/client'
import DecisionBadge from '../components/DecisionBadge'
import FatigueMeter from '../components/FatigueMeter'
import SessionTimeline from '../components/SessionTimeline'

export default function SessionSimulator() {
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

  // Animate playhead when playing.
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

  const selectedUser = users.find((u) => u.id === userId)
  const selectedContent = content.find((c) => c.id === contentId)

  return (
    <div className="space-y-6">
      <div>
        <h1 className="text-2xl font-bold">Session Simulator</h1>
        <p className="text-sm text-gray-400 mt-1">Simulate a full streaming session and see every ad decision</p>
      </div>

      <div className="grid grid-cols-1 lg:grid-cols-3 gap-4">
        <div className="card space-y-3 lg:col-span-1">
          <h2 className="font-semibold">Setup</h2>
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
            {selectedContent && <p className="text-xs text-gray-500 mt-1">{selectedContent.genre} | {selectedContent.duration_minutes}min | {selectedContent.mood}</p>}
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
            {loading ? 'Simulating...' : 'Run Simulation'}
          </button>
          {error && <p className="text-suppress text-sm">{error}</p>}
        </div>

        <div className="lg:col-span-2 space-y-4">
          {result ? (
            <>
              <div className="card">
                <div className="flex items-center justify-between mb-4">
                  <div>
                    <p className="font-semibold">{result.content_title}</p>
                    <p className="text-xs text-gray-400">{result.content_duration_minutes}min</p>
                  </div>
                  <div className="flex gap-2">
                    <button className="btn-secondary text-xs" onClick={() => { setPlayheadMinute(0); setPlaying(true) }}>
                      {playing ? 'Playing...' : 'Animate'}
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
                <h3 className="font-semibold mb-3">Summary</h3>
                <div className="grid grid-cols-4 gap-3">
                  {Object.entries(result.summary.decision_counts).map(([d, count]) => (
                    <div key={d} className="text-center">
                      <p className="text-xl font-bold font-mono">{count}</p>
                      <DecisionBadge decision={d} size="sm" />
                    </div>
                  ))}
                </div>
              </div>

              <div className="card space-y-2">
                <h3 className="font-semibold">Break-by-break</h3>
                {result.decisions.map((d, i) => (
                  <div key={i} className="flex items-center gap-3 text-sm py-1 border-b border-gray-800 last:border-0">
                    <span className="text-gray-500 w-10">{d.break_minute}m</span>
                    <DecisionBadge decision={d.decision} size="sm" />
                    <span className="text-gray-400 text-xs">{d.ad_category} ad</span>
                    <span className="ml-auto font-mono text-xs text-gray-500">score {d.combined_score.toFixed(3)}</span>
                    <span className="font-mono text-xs text-gray-500">fat {d.fatigue_at_break.toFixed(2)}</span>
                  </div>
                ))}
              </div>
            </>
          ) : (
            <div className="card h-64 flex items-center justify-center text-gray-600 text-sm">
              Run a simulation to see the session timeline
            </div>
          )}
        </div>
      </div>
    </div>
  )
}
