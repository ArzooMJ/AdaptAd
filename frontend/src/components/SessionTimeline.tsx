import DecisionBadge from './DecisionBadge'

interface BreakDecision {
  break_minute: number
  ad_category: string
  decision: string
  combined_score: number
  fatigue_at_break: number
  reasoning: string
}

interface Props {
  durationMinutes: number
  decisions: BreakDecision[]
  currentMinute?: number
}

const decisionDotColor: Record<string, string> = {
  SHOW: 'bg-show border-show',
  SOFTEN: 'bg-soften border-soften',
  DELAY: 'bg-delay border-delay',
  SUPPRESS: 'bg-suppress border-suppress',
}

export default function SessionTimeline({ durationMinutes, decisions, currentMinute }: Props) {
  const [selected, setSelected] = useState<number | null>(null)

  return (
    <div>
      <div className="relative h-10 bg-gray-800 rounded-full overflow-visible mb-6">
        {/* Progress bar */}
        {currentMinute != null && (
          <div
            className="absolute top-0 left-0 h-full bg-indigo-900/50 rounded-full transition-all duration-300"
            style={{ width: `${(currentMinute / durationMinutes) * 100}%` }}
          />
        )}
        {/* Break point markers */}
        {decisions.map((d, i) => {
          const pct = (d.break_minute / durationMinutes) * 100
          return (
            <button
              key={i}
              className={`absolute top-1/2 -translate-y-1/2 -translate-x-1/2 w-4 h-4 rounded-full border-2 z-10 transition-transform hover:scale-125 ${decisionDotColor[d.decision] ?? 'bg-gray-500 border-gray-400'}`}
              style={{ left: `${pct}%` }}
              onClick={() => setSelected(selected === i ? null : i)}
              title={`${d.break_minute}min: ${d.decision}`}
            />
          )
        })}
        {/* Time labels */}
        <div className="absolute -bottom-5 left-0 text-xs text-gray-500">0m</div>
        <div className="absolute -bottom-5 right-0 text-xs text-gray-500">{durationMinutes}m</div>
      </div>

      {/* Selected break detail */}
      {selected !== null && decisions[selected] && (
        <div className="card mt-8 space-y-2">
          <div className="flex items-center gap-3">
            <span className="text-sm text-gray-400">{decisions[selected].break_minute}min</span>
            <DecisionBadge decision={decisions[selected].decision} />
            <span className="text-xs text-gray-500">{decisions[selected].ad_category}</span>
            <span className="ml-auto text-xs font-mono text-gray-400">score {decisions[selected].combined_score.toFixed(3)}</span>
          </div>
          <p className="text-xs text-gray-400">{decisions[selected].reasoning}</p>
        </div>
      )}
    </div>
  )
}

import { useState } from 'react'
