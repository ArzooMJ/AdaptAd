import { useEffect, useState } from 'react'
import { useNavigate } from 'react-router-dom'
import { dataApi } from '../api/client'
import { useStore } from '../store'

export default function Dashboard() {
  const navigate = useNavigate()
  const fitness = useStore((s) => s.chromosomeFitness)
  const genes = useStore((s) => s.chromosomeGenes)
  const totalDecisions = useStore((s) => s.totalDecisions)
  const [health, setHealth] = useState<{ users: number; ads: number; content: number } | null>(null)

  useEffect(() => {
    dataApi.health().then((r) => setHealth(r.data)).catch(() => {})
  }, [])

  const cards = [
    { label: 'Chromosome Fitness', value: fitness != null ? fitness.toFixed(4) : 'None', sub: fitness != null ? 'Evolved chromosome loaded' : 'Run evolution first', color: 'text-indigo-400' },
    { label: 'Total Decisions', value: totalDecisions.toString(), sub: 'This session', color: 'text-show' },
    { label: 'Users', value: health?.users ?? '...', sub: 'Synthetic profiles', color: 'text-blue-400' },
    { label: 'Ads', value: health?.ads ?? '...', sub: '8 categories', color: 'text-purple-400' },
  ]

  return (
    <div className="space-y-6">
      <div>
        <h1 className="text-2xl font-bold">Dashboard</h1>
        <p className="text-sm text-gray-400 mt-1">AdaptAd: human-centered ad decision system</p>
      </div>

      <div className="grid grid-cols-2 lg:grid-cols-4 gap-4">
        {cards.map((c) => (
          <div key={c.label} className="card">
            <p className="label mb-1">{c.label}</p>
            <p className={`text-3xl font-bold font-mono ${c.color}`}>{c.value}</p>
            <p className="text-xs text-gray-500 mt-1">{c.sub}</p>
          </div>
        ))}
      </div>

      <div className="card">
        <h2 className="font-semibold mb-3">Quick Actions</h2>
        <div className="flex flex-wrap gap-3">
          <button className="btn-primary" onClick={() => navigate('/evolve')}>Run Evolution</button>
          <button className="btn-secondary" onClick={() => navigate('/decide')}>Try a Decision</button>
          <button className="btn-secondary" onClick={() => navigate('/simulate')}>Simulate Session</button>
          <button className="btn-secondary" onClick={() => navigate('/batch')}>Batch Decisions</button>
          <button className="btn-secondary" onClick={() => navigate('/ab-test')}>Start A/B Test</button>
        </div>
      </div>

      <div className="card">
        <h2 className="font-semibold mb-2">Decision Color Guide</h2>
        <div className="flex flex-wrap gap-4 text-sm">
          {(['SHOW', 'SOFTEN', 'DELAY', 'SUPPRESS'] as const).map((d) => (
            <span key={d} className={`font-semibold ${
              d === 'SHOW' ? 'text-show' : d === 'SOFTEN' ? 'text-soften' : d === 'DELAY' ? 'text-delay' : 'text-suppress'
            }`}>{d}</span>
          ))}
        </div>
        <p className="text-xs text-gray-500 mt-2">
          SHOW = favorable conditions. SOFTEN = shorter version. DELAY = wait for better moment. SUPPRESS = skip entirely.
        </p>
      </div>

      {genes && (
        <div className="card">
          <h2 className="font-semibold mb-1">Active Chromosome</h2>
          <p className="text-xs font-mono text-gray-400">[{genes.map((g) => g.toFixed(3)).join(', ')}]</p>
        </div>
      )}
    </div>
  )
}
