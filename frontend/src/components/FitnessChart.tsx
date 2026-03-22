import { LineChart, Line, XAxis, YAxis, CartesianGrid, Tooltip, Legend, ResponsiveContainer, ReferenceLine } from 'recharts'

interface DataPoint {
  generation: number
  best_fitness: number
  avg_fitness: number
}

interface Props {
  data: DataPoint[]
  targetFitness?: number
}

export default function FitnessChart({ data, targetFitness = 0.65 }: Props) {
  return (
    <ResponsiveContainer width="100%" height={260}>
      <LineChart data={data} margin={{ top: 8, right: 16, bottom: 0, left: 0 }}>
        <CartesianGrid strokeDasharray="3 3" stroke="#374151" />
        <XAxis dataKey="generation" stroke="#9ca3af" tick={{ fontSize: 11 }} label={{ value: 'Generation', position: 'insideBottom', offset: -2, fill: '#9ca3af', fontSize: 11 }} />
        <YAxis domain={[0, 1]} stroke="#9ca3af" tick={{ fontSize: 11 }} tickFormatter={(v) => v.toFixed(2)} />
        <Tooltip
          contentStyle={{ background: '#111827', border: '1px solid #374151', borderRadius: 8 }}
          labelStyle={{ color: '#e5e7eb' }}
          formatter={(v: number, name: string) => [v.toFixed(4), name]}
        />
        <Legend wrapperStyle={{ fontSize: 12, color: '#9ca3af' }} />
        <ReferenceLine y={targetFitness} stroke="#6366f1" strokeDasharray="4 4" label={{ value: `Target ${targetFitness}`, fill: '#818cf8', fontSize: 10, position: 'right' }} />
        <Line type="monotone" dataKey="best_fitness" stroke="#6366f1" strokeWidth={2} dot={false} name="Best fitness" />
        <Line type="monotone" dataKey="avg_fitness" stroke="#64748b" strokeWidth={1.5} dot={false} strokeDasharray="4 2" name="Avg fitness" />
      </LineChart>
    </ResponsiveContainer>
  )
}
