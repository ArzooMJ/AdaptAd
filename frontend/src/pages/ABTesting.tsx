import { useState } from 'react'
import { abApi } from '../api/client'
import DecisionBadge from '../components/DecisionBadge'

interface Break { break_minute: number; ad_category: string; decision: string }
interface Session { session_id: string; user_name: string; content_title: string; session_x: Break[]; session_y: Break[] }
interface Rating { annoyance: number; relevance: number; willingness: number }

function StarRating({ value, onChange }: { value: number; onChange: (v: number) => void }) {
  return (
    <div className="flex gap-1">
      {[1, 2, 3, 4, 5].map((n) => (
        <button key={n} onClick={() => onChange(n)} className={`text-xl transition-colors ${n <= value ? 'text-yellow-400' : 'text-gray-600 hover:text-gray-400'}`}>★</button>
      ))}
    </div>
  )
}

function SessionView({ label, breaks, rating, onRate }: { label: string; breaks: Break[]; rating: Rating; onRate: (field: keyof Rating, v: number) => void }) {
  return (
    <div className="card flex-1">
      <h3 className="font-semibold text-lg mb-3">Session {label}</h3>
      <div className="space-y-1 mb-4 max-h-48 overflow-y-auto">
        {breaks.length === 0
          ? <p className="text-gray-500 text-sm">No ad breaks</p>
          : breaks.map((b, i) => (
              <div key={i} className="flex items-center gap-2 text-sm">
                <span className="text-gray-500 w-10">{b.break_minute}m</span>
                <DecisionBadge decision={b.decision} size="sm" />
                <span className="text-gray-400 text-xs">{b.ad_category}</span>
              </div>
            ))
        }
      </div>
      <div className="border-t border-gray-800 pt-3 space-y-3">
        <div className="flex items-center justify-between">
          <span className="label">Annoyance</span>
          <StarRating value={rating.annoyance} onChange={(v) => onRate('annoyance', v)} />
        </div>
        <div className="flex items-center justify-between">
          <span className="label">Relevance</span>
          <StarRating value={rating.relevance} onChange={(v) => onRate('relevance', v)} />
        </div>
        <div className="flex items-center justify-between">
          <span className="label">Would continue watching?</span>
          <StarRating value={rating.willingness} onChange={(v) => onRate('willingness', v)} />
        </div>
      </div>
    </div>
  )
}

export default function ABTesting() {
  const [session, setSession] = useState<Session | null>(null)
  const [xRating, setXRating] = useState<Rating>({ annoyance: 0, relevance: 0, willingness: 0 })
  const [yRating, setYRating] = useState<Rating>({ annoyance: 0, relevance: 0, willingness: 0 })
  const [submitted, setSubmitted] = useState(false)
  const [results, setResults] = useState<Record<string, unknown> | null>(null)
  const [loading, setLoading] = useState(false)
  const [error, setError] = useState<string | null>(null)

  function updateRating(which: 'X' | 'Y', field: keyof Rating, v: number) {
    if (which === 'X') setXRating((r) => ({ ...r, [field]: v }))
    else setYRating((r) => ({ ...r, [field]: v }))
  }

  async function startSession() {
    setLoading(true); setError(null); setSubmitted(false)
    setXRating({ annoyance: 0, relevance: 0, willingness: 0 })
    setYRating({ annoyance: 0, relevance: 0, willingness: 0 })
    try {
      const r = await abApi.start()
      setSession(r.data as Session)
    } catch { setError('Failed to start A/B session.') }
    finally { setLoading(false) }
  }

  async function submitRatings() {
    if (!session) return
    const missingX = Object.values(xRating).some((v) => v === 0)
    const missingY = Object.values(yRating).some((v) => v === 0)
    if (missingX || missingY) { setError('Please rate all fields for both sessions.'); return }
    setLoading(true); setError(null)
    try {
      await abApi.rate(session.session_id, { session_label: 'X', ...xRating })
      await abApi.rate(session.session_id, { session_label: 'Y', ...yRating })
      setSubmitted(true)
      const r = await abApi.results()
      setResults(r.data)
    } catch { setError('Failed to submit ratings.') }
    finally { setLoading(false) }
  }

  const aggregate = (results as Record<string, unknown> | null)?.aggregate as Record<string, unknown> | undefined

  return (
    <div className="space-y-6">
      <div className="flex items-center justify-between">
        <div>
          <h1 className="text-2xl font-bold">A/B Testing</h1>
          <p className="text-sm text-gray-400 mt-1">Compare AdaptAd against random placement. Labels are randomized to prevent bias.</p>
        </div>
        <button className="btn-primary" onClick={startSession} disabled={loading}>
          {loading ? 'Loading...' : 'New Session'}
        </button>
      </div>

      {error && <div className="card border-red-700/40 text-suppress text-sm">{error}</div>}

      {session && !submitted && (
        <>
          <div className="card">
            <p className="text-sm text-gray-400">User: <span className="text-gray-200">{session.user_name}</span> | Content: <span className="text-gray-200">{session.content_title}</span></p>
            <p className="text-xs text-gray-500 mt-1">Rate each session honestly. You do not know which system generated which.</p>
          </div>
          <div className="flex gap-4">
            <SessionView label="X" breaks={session.session_x as Break[]} rating={xRating} onRate={(f, v) => updateRating('X', f, v)} />
            <SessionView label="Y" breaks={session.session_y as Break[]} rating={yRating} onRate={(f, v) => updateRating('Y', f, v)} />
          </div>
          <button className="btn-primary" onClick={submitRatings} disabled={loading}>Submit Ratings</button>
        </>
      )}

      {submitted && aggregate && (
        <div className="card space-y-3">
          <h2 className="font-semibold text-show">Ratings submitted. Aggregate results:</h2>
          <div className="grid grid-cols-3 gap-4 text-sm">
            <div className="card"><p className="label mb-1">AdaptAd Wins</p><p className="text-2xl font-bold text-show">{String(aggregate.adaptad_wins)}</p></div>
            <div className="card"><p className="label mb-1">Baseline Wins</p><p className="text-2xl font-bold text-suppress">{String(aggregate.baseline_wins)}</p></div>
            <div className="card"><p className="label mb-1">Ties</p><p className="text-2xl font-bold text-gray-400">{String(aggregate.ties)}</p></div>
          </div>
          <button className="btn-secondary" onClick={startSession}>Run Another Session</button>
        </div>
      )}

      {!session && !loading && (
        <div className="card h-48 flex items-center justify-center text-gray-600 text-sm">
          Click "New Session" to start an A/B test
        </div>
      )}
    </div>
  )
}
