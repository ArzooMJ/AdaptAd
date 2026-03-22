import type { AgentScore } from '../api/client'

interface Props {
  score: AgentScore
  side: 'user' | 'advertiser'
}

const factorColor = (v: number) => v >= 0 ? 'text-green-400' : 'text-red-400'

export default function AgentPanel({ score, side }: Props) {
  const borderColor = side === 'user' ? 'border-blue-500/40' : 'border-purple-500/40'
  const headerColor = side === 'user' ? 'text-blue-400' : 'text-purple-400'
  const barColor = side === 'user' ? 'bg-blue-500' : 'bg-purple-500'

  const topFactors = Object.entries(score.factors)
    .filter(([k]) => !['base', 'final_score'].includes(k))
    .sort(([, a], [, b]) => Math.abs(b) - Math.abs(a))
    .slice(0, 5)

  return (
    <div className={`card border ${borderColor}`}>
      <div className="flex items-center justify-between mb-3">
        <span className={`font-semibold ${headerColor}`}>{score.agent_name}</span>
        <span className="font-mono text-lg font-bold">{score.score.toFixed(3)}</span>
      </div>

      <div className="bg-gray-800 rounded-full h-2 mb-3">
        <div className={`h-full rounded-full ${barColor} transition-all duration-700`} style={{ width: `${score.score * 100}%` }} />
      </div>

      <div className="space-y-1 mb-3">
        {topFactors.map(([k, v]) => (
          <div key={k} className="flex justify-between text-xs">
            <span className="text-gray-400">{k.replace(/_/g, ' ')}</span>
            <span className={`font-mono ${factorColor(v)}`}>{v >= 0 ? '+' : ''}{v.toFixed(3)}</span>
          </div>
        ))}
      </div>

      <p className="text-xs text-gray-400 leading-relaxed border-t border-gray-800 pt-2">{score.reasoning}</p>
    </div>
  )
}
