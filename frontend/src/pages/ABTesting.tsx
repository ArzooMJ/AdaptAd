import { useState } from 'react'
import { abApi } from '../api/client'
import DecisionBadge from '../components/DecisionBadge'

// ── constants ─────────────────────────────────────────────────────────────────
const AD_CATEGORIES = ['tech', 'food', 'auto', 'fashion', 'finance', 'travel', 'health', 'gaming']
const GENRES = ['Action', 'Comedy', 'Drama', 'Sci-Fi', 'Horror', 'Documentary', 'Romance', 'Thriller', 'Animation', 'Fantasy']
const AGE_GROUPS = ['13-17', '18-24', '25-34', '35-44', '45-54', '55-64', '65+']
const WATCH_TIMES = ['morning', 'afternoon', 'evening', 'latenight']

// ── types ─────────────────────────────────────────────────────────────────────
interface Break { break_minute: number; ad_category: string; decision: string }
interface UserProfile {
  name: string; age_group: string; profession: string
  interests: string[]; content_preferences: string[]
  binge_tendency: number; ad_tolerance: number; preferred_watch_time: string
}
interface ContentProfile {
  title: string; genre: string; duration_minutes: number | null
  mood: string | null; language: string; is_series: boolean
}
interface SessionContext {
  ads_shown: number; total_breaks: number; fatigue: number
  session_depth: number; content_duration: number | null; binge: boolean
}
interface Session {
  session_id: string; user_name: string; content_title: string
  session_x: Break[]; session_y: Break[]
  x_is_adaptad?: boolean
  user_profile?: UserProfile
  content_profile?: ContentProfile
  session_context?: SessionContext
}
interface Rating { annoyance: number; relevance: number; willingness: number }

const EMPTY_FORM = {
  person_name: '',
  age_group: '25-34',
  occupation: '',
  interests: [] as string[],
  content_preferences: [] as string[],
  ad_tolerance: 0.5,
  binge_tendency: 0.4,
  preferred_watch_time: 'evening',
  show_title: '',
  show_genre: 'Drama',
  show_duration_minutes: 45,
  is_series: true,
}

// ── small UI helpers ──────────────────────────────────────────────────────────

function InfoRow({ label, value }: { label: string; value: React.ReactNode }) {
  return (
    <div className="flex justify-between items-start gap-3 py-1.5 border-b border-slate-800/40 last:border-0">
      <span className="text-xs text-slate-500 shrink-0">{label}</span>
      <span className="text-xs text-slate-200 text-right">{value}</span>
    </div>
  )
}

function ScaleRating({ value, onChange, readonly }: {
  value: number; onChange?: (v: number) => void; readonly?: boolean
}) {
  return (
    <div className="flex gap-1 flex-wrap">
      {[1,2,3,4,5,6,7,8,9,10].map(n => (
        <button key={n} onClick={() => !readonly && onChange?.(n)}
          className={`w-7 h-7 rounded-md text-xs font-semibold border transition-colors ${
            n === value
              ? 'bg-sky-600 border-sky-500 text-white'
              : readonly
              ? 'bg-slate-800 border-slate-700 text-slate-600 cursor-default'
              : 'bg-slate-800 border-slate-700 text-slate-400 hover:border-sky-500 hover:text-sky-300 cursor-pointer'
          }`}>{n}</button>
      ))}
    </div>
  )
}

function ToggleChip({ label, active, onClick }: { label: string; active: boolean; onClick: () => void }) {
  return (
    <button onClick={onClick}
      className={`px-3 py-1.5 rounded-lg text-xs font-medium border transition-colors ${
        active
          ? 'bg-sky-600/20 border-sky-500/50 text-sky-300'
          : 'bg-slate-800 border-slate-700 text-slate-500 hover:border-slate-500 hover:text-slate-300'
      }`}>{label}</button>
  )
}

// ── info panels ───────────────────────────────────────────────────────────────

function UserPanel({ p }: { p: UserProfile }) {
  const watch = p.preferred_watch_time.replace('TimeOfDay.', '')
  return (
    <div className="card flex-1 min-w-0">
      <p className="text-[11px] font-bold text-slate-400 uppercase tracking-widest mb-3">User</p>
      <InfoRow label="Name" value={<span className="font-semibold">{p.name}</span>} />
      <InfoRow label="Age Group" value={p.age_group} />
      <InfoRow label="Profession" value={p.profession} />
      <div className="py-1.5 border-b border-slate-800/40">
        <p className="text-xs text-slate-500 mb-1">Ad Interests</p>
        <p className="text-xs text-slate-200">{p.interests.join(', ') || '—'}</p>
      </div>
      <div className="py-1.5 border-b border-slate-800/40">
        <p className="text-xs text-slate-500 mb-1">Preferred Genres</p>
        <p className="text-xs text-slate-200">{p.content_preferences.join(', ') || '—'}</p>
      </div>
      <InfoRow label="Ad Tolerance" value={p.ad_tolerance.toFixed(2)} />
      <InfoRow label="Binge Tendency" value={p.binge_tendency.toFixed(2)} />
      <InfoRow label="Preferred Watch Time" value={watch} />
    </div>
  )
}

function ContentPanel({ p }: { p: ContentProfile }) {
  return (
    <div className="card flex-1 min-w-0">
      <p className="text-[11px] font-bold text-slate-400 uppercase tracking-widest mb-3">Content</p>
      <InfoRow label="Title" value={<span className="font-semibold">{p.title}</span>} />
      <InfoRow label="Genre" value={p.genre || '—'} />
      <InfoRow label="Mood" value={p.mood || '—'} />
      <InfoRow label="Duration" value={p.duration_minutes ? `${p.duration_minutes} min` : '—'} />
      <InfoRow label="Language" value={p.language} />
      <InfoRow label="Type" value={p.is_series ? 'Series episode' : 'Movie'} />
    </div>
  )
}

function ContextPanel({ c }: { c: SessionContext }) {
  return (
    <div className="card flex-1 min-w-0">
      <p className="text-[11px] font-bold text-slate-400 uppercase tracking-widest mb-3">Session Context</p>
      <InfoRow label="Ads Shown" value={c.ads_shown} />
      <InfoRow label="Total Breaks" value={c.total_breaks} />
      <InfoRow label="Fatigue" value={c.fatigue.toFixed(2)} />
      <InfoRow label="Minutes Into Session" value={c.session_depth} />
      <InfoRow label="Content Duration" value={c.content_duration ? `${c.content_duration} min` : '—'} />
      <InfoRow label="Binge Mode" value={c.binge ? 'Yes' : 'No'} />
    </div>
  )
}

// ── session rating card ───────────────────────────────────────────────────────

function SessionCard({ label, breaks, rating, onRate, readonly = false }: {
  label: string; breaks: Break[]; rating: Rating
  onRate?: (f: keyof Rating, v: number) => void; readonly?: boolean
}) {
  // Group ads by break minute to form pods
  const pods: { minute: number; ads: Break[] }[] = []
  for (const b of breaks) {
    const existing = pods.find(p => p.minute === b.break_minute)
    if (existing) existing.ads.push(b)
    else pods.push({ minute: b.break_minute, ads: [b] })
  }

  return (
    <div className="card flex-1 min-w-0 space-y-4">
      <h3 className="text-sm font-bold text-slate-300">Session {label}</h3>
      <div className="space-y-3">
        {pods.length === 0
          ? <p className="text-xs text-slate-600">No ad breaks</p>
          : pods.map((pod, i) => (
              <div key={i} className="rounded-lg border border-slate-700/50 bg-slate-800/30 px-3 py-2 space-y-1.5">
                <span className="text-[10px] font-bold text-slate-500 uppercase tracking-widest">
                  {pod.minute}m — {pod.ads.length} ad{pod.ads.length > 1 ? 's' : ''}
                </span>
                {pod.ads.map((b, j) => (
                  <div key={j} className="flex items-center gap-2 pl-1">
                    <span className="text-slate-600 text-xs w-3">{j + 1}.</span>
                    <DecisionBadge decision={b.decision} size="sm" />
                    <span className="text-slate-500 text-xs">{b.ad_category}</span>
                  </div>
                ))}
              </div>
            ))}
      </div>
      <div className="border-t border-slate-700/40 pt-3 space-y-3">
        {(['annoyance', 'relevance', 'willingness'] as (keyof Rating)[]).map(field => (
          <div key={field} className="space-y-1.5">
            <span className="text-[10px] font-bold uppercase tracking-widest text-slate-500">
              {field === 'willingness' ? 'Would Continue?' : field}
            </span>
            <ScaleRating value={rating[field]} onChange={v => onRate?.(field, v)} readonly={readonly} />
          </div>
        ))}
      </div>
    </div>
  )
}

// ── main ─────────────────────────────────────────────────────────────────────

export default function ABTesting() {
  const [form, setForm] = useState(EMPTY_FORM)
  const [durationStr, setDurationStr] = useState('45')
  const [lookupLoading, setLookupLoading] = useState(false)
  const [showDescription, setShowDescription] = useState('')

  const [session, setSession] = useState<Session | null>(null)
  const [xRating, setXRating] = useState<Rating>({ annoyance: 0, relevance: 0, willingness: 0 })
  const [yRating, setYRating] = useState<Rating>({ annoyance: 0, relevance: 0, willingness: 0 })
  const [submitted, setSubmitted] = useState(false)
  const [results, setResults] = useState<Record<string, unknown> | null>(null)
  const [loading, setLoading] = useState(false)
  const [error, setError] = useState<string | null>(null)

  function resetSession() {
    setSession(null); setSubmitted(false); setResults(null); setError(null)
    setXRating({ annoyance: 0, relevance: 0, willingness: 0 })
    setYRating({ annoyance: 0, relevance: 0, willingness: 0 })
  }

  function resetAll() {
    resetSession()
    setForm(EMPTY_FORM); setDurationStr('45'); setShowDescription('')
  }

  function toggleList(key: 'interests' | 'content_preferences', val: string) {
    setForm(f => ({
      ...f,
      [key]: f[key].includes(val) ? f[key].filter(v => v !== val) : [...f[key], val]
    }))
  }

  async function lookupShow() {
    if (!form.show_title.trim()) return
    setLookupLoading(true)
    try {
      const d = (await abApi.lookupShow(form.show_title)).data
      setForm(f => ({ ...f, show_genre: d.genre, show_duration_minutes: d.duration_minutes, is_series: d.is_series }))
      setDurationStr(String(d.duration_minutes))
      setShowDescription(d.description || '')
    } catch { /* ignore — user fills manually */ }
    finally { setLookupLoading(false) }
  }

  async function startSession() {
    if (!form.person_name.trim()) { setError('Please enter your name.'); return }
    if (!form.show_title.trim()) { setError('Please enter a show or movie title.'); return }
    if (form.interests.length === 0) { setError('Select at least one ad interest.'); return }
    if (form.content_preferences.length === 0) { setError('Select at least one preferred genre.'); return }
    resetSession(); setLoading(true)
    try {
      const payload = { ...form, show_duration_minutes: parseInt(durationStr, 10) || 45 }
      const base = (await abApi.startCustom(payload)).data as Session
      // Fetch full session detail to get all profile/context data
      try {
        const detail = (await abApi.session(base.session_id)).data as Session
        setSession({ ...base, ...detail })
      } catch { setSession(base) }
    } catch { setError('Failed to start session. Please try again.') }
    finally { setLoading(false) }
  }

  async function submitRatings() {
    if (!session) return
    if (Object.values(xRating).some(v => v === 0) || Object.values(yRating).some(v => v === 0)) {
      setError('Please rate all three fields (1–10) for both sessions.'); return
    }
    setLoading(true); setError(null)
    try {
      await abApi.rate(session.session_id, { session_label: 'X', ...xRating })
      await abApi.rate(session.session_id, { session_label: 'Y', ...yRating })
      setResults((await abApi.results()).data)
      setSubmitted(true)
    } catch { setError('Failed to submit ratings.') }
    finally { setLoading(false) }
  }

  // Reveal scoring
  let adaptadScore = 0, baselineScore = 0
  let winner: 'adaptad' | 'baseline' | 'tie' | null = null
  if (submitted && session?.x_is_adaptad !== undefined) {
    const ar = session.x_is_adaptad ? xRating : yRating
    const br = session.x_is_adaptad ? yRating : xRating
    adaptadScore = ar.willingness + ar.relevance - ar.annoyance
    baselineScore = br.willingness + br.relevance - br.annoyance
    winner = adaptadScore > baselineScore ? 'adaptad' : adaptadScore < baselineScore ? 'baseline' : 'tie'
  }
  const aggregate = (results as Record<string, unknown> | null)?.aggregate as Record<string, unknown> | undefined

  const inputCls = "w-full bg-slate-800 border border-slate-700 rounded-lg px-3 py-2 text-sm text-slate-200 focus:outline-none focus:border-sky-600"

  return (
    <div className="space-y-6">

      {/* Header */}
      <div className="page-header flex flex-col sm:flex-row sm:items-start sm:justify-between gap-3">
        <div>
          <h1 className="page-title">A/B Testing</h1>
          <p className="page-sub">
            Fill in your profile and what you're watching — AdaptAd will run a blind test so you can rate
            two ad experiences without knowing which was AI-optimised.
          </p>
        </div>
        {session && (
          <button className="btn-secondary shrink-0" onClick={resetAll}>New Test</button>
        )}
      </div>

      {error && <div className="card border-red-700/40 bg-red-950/20 text-red-400 text-sm">{error}</div>}

      {/* ── INTAKE FORM (shown when no session is running) ─────────────────── */}
      {!session && (
        <div className="space-y-5">

          {/* About You */}
          <div className="card space-y-4">
            <h2 className="section-title text-base">About You</h2>

            <div className="grid grid-cols-1 sm:grid-cols-3 gap-4">
              <div className="space-y-1">
                <label className="label">Your name</label>
                <input className={inputCls} placeholder="e.g. Priya Sharma"
                  value={form.person_name}
                  onChange={e => setForm(f => ({ ...f, person_name: e.target.value }))} />
              </div>
              <div className="space-y-1">
                <label className="label">Age group</label>
                <select className={inputCls} value={form.age_group}
                  onChange={e => setForm(f => ({ ...f, age_group: e.target.value }))}>
                  {AGE_GROUPS.map(g => <option key={g}>{g}</option>)}
                </select>
              </div>
              <div className="space-y-1">
                <label className="label">Occupation</label>
                <input className={inputCls} placeholder="e.g. Doctor"
                  value={form.occupation}
                  onChange={e => setForm(f => ({ ...f, occupation: e.target.value }))} />
              </div>
            </div>

            <div className="grid grid-cols-1 sm:grid-cols-2 gap-4">
              <div className="space-y-1">
                <label className="label">Preferred watch time</label>
                <select className={inputCls} value={form.preferred_watch_time}
                  onChange={e => setForm(f => ({ ...f, preferred_watch_time: e.target.value }))}>
                  {WATCH_TIMES.map(t => <option key={t} value={t}>{t.charAt(0).toUpperCase() + t.slice(1)}</option>)}
                </select>
              </div>
              <div className="space-y-1">
                <label className="label">
                  Ad tolerance — <span className="text-sky-400 font-mono normal-case">{form.ad_tolerance.toFixed(2)}</span>
                  <span className="text-slate-600 font-normal ml-2">(how much you mind ads)</span>
                </label>
                <input type="range" min="0" max="1" step="0.05" className="w-full accent-sky-500 mt-2"
                  value={form.ad_tolerance}
                  onChange={e => setForm(f => ({ ...f, ad_tolerance: parseFloat(e.target.value) }))} />
                <div className="flex justify-between text-xs text-slate-600 mt-0.5">
                  <span>0 — hate ads</span><span>1 — don't mind</span>
                </div>
              </div>
            </div>

            <div className="space-y-1">
              <label className="label">
                Binge tendency — <span className="text-sky-400 font-mono normal-case">{form.binge_tendency.toFixed(2)}</span>
                <span className="text-slate-600 font-normal ml-2">(how often you watch multiple episodes in a row)</span>
              </label>
              <input type="range" min="0" max="1" step="0.05" className="w-full accent-sky-500 mt-1"
                value={form.binge_tendency}
                onChange={e => setForm(f => ({ ...f, binge_tendency: parseFloat(e.target.value) }))} />
              <div className="flex justify-between text-xs text-slate-600 mt-0.5">
                <span>0 — one episode at a time</span><span>1 — always binge</span>
              </div>
            </div>

            <div className="space-y-2">
              <label className="label">Ad interests <span className="text-slate-600 font-normal">(what ads are relevant to you)</span></label>
              <div className="flex flex-wrap gap-2">
                {AD_CATEGORIES.map(cat => (
                  <ToggleChip key={cat} label={cat}
                    active={form.interests.includes(cat)}
                    onClick={() => toggleList('interests', cat)} />
                ))}
              </div>
            </div>

            <div className="space-y-2">
              <label className="label">Preferred genres <span className="text-slate-600 font-normal">(what you enjoy watching)</span></label>
              <div className="flex flex-wrap gap-2">
                {GENRES.map(g => (
                  <ToggleChip key={g} label={g}
                    active={form.content_preferences.includes(g)}
                    onClick={() => toggleList('content_preferences', g)} />
                ))}
              </div>
            </div>
          </div>

          {/* What are you watching */}
          <div className="card space-y-4">
            <h2 className="section-title text-base">What Are You Watching?</h2>

            <div className="grid grid-cols-1 sm:grid-cols-3 gap-4">
              <div className="space-y-1 sm:col-span-1">
                <label className="label">Show or movie title</label>
                <div className="flex gap-2">
                  <input className="flex-1 bg-slate-800 border border-slate-700 rounded-lg px-3 py-2 text-sm text-slate-200 focus:outline-none focus:border-sky-600"
                    placeholder="e.g. Stranger Things"
                    value={form.show_title}
                    onChange={e => { setForm(f => ({ ...f, show_title: e.target.value })); setShowDescription('') }} />
                  <button onClick={lookupShow} disabled={lookupLoading || !form.show_title.trim()}
                    className="shrink-0 px-3 py-2 bg-sky-700/30 hover:bg-sky-600/40 border border-sky-600/40 text-sky-300 text-xs font-semibold rounded-lg transition-colors disabled:opacity-40 disabled:cursor-not-allowed">
                    {lookupLoading ? '…' : 'Auto-fill'}
                  </button>
                </div>
                {showDescription && <p className="text-xs text-slate-500 italic mt-1">{showDescription}</p>}
              </div>

              <div className="space-y-1">
                <label className="label">Genre</label>
                <select className={inputCls} value={form.show_genre}
                  onChange={e => setForm(f => ({ ...f, show_genre: e.target.value }))}>
                  {GENRES.map(g => <option key={g}>{g}</option>)}
                </select>
              </div>

              <div className="space-y-1">
                <label className="label">Duration (minutes)</label>
                <input type="text" inputMode="numeric" placeholder="e.g. 45" className={inputCls}
                  value={durationStr}
                  onChange={e => {
                    const raw = e.target.value.replace(/[^0-9]/g, '')
                    setDurationStr(raw)
                    const n = parseInt(raw, 10)
                    if (!isNaN(n) && n >= 10 && n <= 240)
                      setForm(f => ({ ...f, show_duration_minutes: n }))
                  }}
                  onBlur={() => {
                    const n = parseInt(durationStr, 10)
                    const v = isNaN(n) || n < 10 ? 45 : Math.min(240, n)
                    setDurationStr(String(v)); setForm(f => ({ ...f, show_duration_minutes: v }))
                  }} />
                <p className="text-xs text-slate-600">10–240 min</p>
              </div>
            </div>

            <div className="flex items-center gap-3">
              <input type="checkbox" id="is-series" className="accent-sky-500 w-4 h-4"
                checked={form.is_series}
                onChange={e => setForm(f => ({ ...f, is_series: e.target.checked }))} />
              <label htmlFor="is-series" className="text-sm text-slate-400">
                This is a series episode (fewer, shorter ad breaks)
              </label>
            </div>
          </div>

          <button className="btn-primary w-full sm:w-auto" onClick={startSession} disabled={loading}>
            {loading ? 'Setting up your session…' : 'Start My A/B Test'}
          </button>
        </div>
      )}

      {/* ── SESSION ACTIVE ────────────────────────────────────────────────── */}
      {session && (
        <>
          {/* Info banner */}
          <div className="card bg-slate-800/60 border-slate-700/40">
            <p className="text-sm text-slate-300 font-medium mb-1">Rate each session honestly.</p>
            <p className="text-xs text-slate-500 leading-relaxed">
              You do not know which system generated which schedule. Consider whether the ads feel
              disruptive and whether they fit you and what you're watching.
            </p>
          </div>

          {/* Three info panels */}
          <div className="flex flex-col sm:flex-row gap-4">
            {session.user_profile && <UserPanel p={session.user_profile} />}
            {session.content_profile && <ContentPanel p={session.content_profile} />}
            {session.session_context && <ContextPanel c={session.session_context} />}
          </div>

          {/* Rating guide */}
          {!submitted && (
            <div className="card bg-slate-800/40 border-slate-700/30 text-xs text-slate-500">
              <span className="text-slate-300 font-semibold">How to rate (1–10): </span>
              <span className="text-sky-400">Annoyance</span> — 1 = very annoying, 10 = barely noticeable ·{' '}
              <span className="text-sky-400">Relevance</span> — 1 = irrelevant to you, 10 = spot on ·{' '}
              <span className="text-sky-400">Would Continue</span> — 1 = would stop watching, 10 = definitely keep going
            </div>
          )}

          {/* Two session cards */}
          <div className="flex flex-col sm:flex-row gap-4">
            <SessionCard label="X" breaks={session.session_x as Break[]} rating={xRating}
              onRate={(f, v) => setXRating(r => ({ ...r, [f]: v }))} readonly={submitted} />
            <SessionCard label="Y" breaks={session.session_y as Break[]} rating={yRating}
              onRate={(f, v) => setYRating(r => ({ ...r, [f]: v }))} readonly={submitted} />
          </div>

          {!submitted && (
            <button className="btn-primary" onClick={submitRatings} disabled={loading}>
              {loading ? 'Submitting…' : 'Submit Ratings & Reveal'}
            </button>
          )}

          {/* Reveal */}
          {submitted && winner && (
            <div className={`card space-y-4 ${
              winner === 'adaptad' ? 'border-sky-500/40 bg-sky-900/10' :
              winner === 'baseline' ? 'border-red-500/40 bg-red-900/10' : 'border-slate-600/40'
            }`}>
              {winner === 'adaptad' && <p className="text-sky-400 font-bold text-lg">AdaptAd won this round</p>}
              {winner === 'baseline' && <p className="text-red-400 font-bold text-lg">Baseline won this round</p>}
              {winner === 'tie' && <p className="text-slate-300 font-bold text-lg">This round was a tie</p>}

              <div className="grid grid-cols-1 sm:grid-cols-2 gap-3">
                <div className="bg-slate-800/60 rounded-xl px-4 py-3">
                  <p className="text-xs text-sky-400 font-semibold mb-1">
                    AdaptAd score: <span className="font-mono text-white">{adaptadScore > 0 ? '+' : ''}{adaptadScore} / 19</span>
                  </p>
                  <p className="text-xs text-slate-500">Uses your profile to decide when and whether to show each ad.</p>
                </div>
                <div className="bg-slate-800/60 rounded-xl px-4 py-3">
                  <p className="text-xs text-slate-300 font-semibold mb-1">
                    Random baseline score: <span className="font-mono text-white">{baselineScore > 0 ? '+' : ''}{baselineScore} / 19</span>
                  </p>
                  <p className="text-xs text-slate-500">No intelligence — randomly shows or suppresses with no context.</p>
                </div>
              </div>

              <div className="bg-slate-800/40 rounded-xl px-4 py-3 text-xs text-slate-400">
                Score = Willingness + Relevance − Annoyance &nbsp;·&nbsp; Range: −8 to +19 &nbsp;·&nbsp; Higher wins.
              </div>

              {aggregate && (
                <div className="grid grid-cols-3 gap-3 pt-2 border-t border-slate-700/40">
                  <div className="text-center"><p className="text-xs text-slate-500 mb-1">AdaptAd Wins</p><p className="text-2xl font-bold text-sky-400">{String(aggregate.adaptad_wins)}</p></div>
                  <div className="text-center"><p className="text-xs text-slate-500 mb-1">Baseline Wins</p><p className="text-2xl font-bold text-red-400">{String(aggregate.baseline_wins)}</p></div>
                  <div className="text-center"><p className="text-xs text-slate-500 mb-1">Ties</p><p className="text-2xl font-bold text-slate-400">{String(aggregate.ties)}</p></div>
                </div>
              )}

              <button className="btn-secondary" onClick={resetAll}>Run Another Test</button>
            </div>
          )}
        </>
      )}
    </div>
  )
}
