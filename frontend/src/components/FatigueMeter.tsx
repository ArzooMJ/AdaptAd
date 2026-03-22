interface Props {
  value: number
  label?: string
}

export default function FatigueMeter({ value, label = 'Session Fatigue' }: Props) {
  const pct = Math.min(1, Math.max(0, value))
  const color =
    pct > 0.85 ? 'bg-suppress' :
    pct > 0.70 ? 'bg-delay' :
    pct > 0.50 ? 'bg-soften' :
    'bg-show'

  return (
    <div>
      <div className="flex justify-between mb-1">
        <span className="label">{label}</span>
        <span className="text-xs font-mono text-gray-300">{(pct * 100).toFixed(0)}%</span>
      </div>
      <div className="bg-gray-800 rounded-full h-3 overflow-hidden">
        <div className={`h-full ${color} rounded-full transition-all duration-500`} style={{ width: `${pct * 100}%` }} />
      </div>
      {pct > 0.85 && <p className="text-xs text-suppress mt-1">Force suppress active</p>}
      {pct > 0.70 && pct <= 0.85 && <p className="text-xs text-delay mt-1">High fatigue penalty active</p>}
    </div>
  )
}
