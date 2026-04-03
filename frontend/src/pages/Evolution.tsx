import { useState, useCallback, useEffect, useRef } from 'react'
import { evolveApi } from '../api/client'
import { useStore } from '../store'
import { useWebSocket, type WsMessage } from '../hooks/useWebSocket'
import FitnessChart from '../components/FitnessChart'

interface GenPoint { generation: number; best_fitness: number; avg_fitness: number; diversity: number }

// ── Gene metadata ─────────────────────────────────────────────────────────────
const GENE_NAMES = [
  'Relevance Wt', 'Timing Wt', 'Fatigue Wt', 'Session Depth',
  'Freq Threshold', 'Category Boost', 'Soften Thresh', 'Delay Prob',
]

// ── Seeded PRNG (simple mulberry32) ──────────────────────────────────────────
function mulberry32(seed: number) {
  return function () {
    seed |= 0; seed = seed + 0x6D2B79F5 | 0
    let t = Math.imul(seed ^ seed >>> 15, 1 | seed)
    t = t + Math.imul(t ^ t >>> 7, 61 | t) ^ t
    return ((t ^ t >>> 14) >>> 0) / 4294967296
  }
}

// ── Population grid ───────────────────────────────────────────────────────────
const POP_SIZE = 30
const ELITE_COUNT = 6
const GENE_COLORS = [
  '#00d4ff', '#00ff88', '#ffb800', '#ff6b00',
  '#a78bfa', '#f472b6', '#34d399', '#fb923c',
]

function geneColor(geneIdx: number, value: number): string {
  const base = GENE_COLORS[geneIdx % GENE_COLORS.length]
  const opacity = Math.round(30 + value * 70)
  return `${base}${opacity.toString(16).padStart(2, '0')}`
}

interface PopGridProps {
  bestGenes: number[]
  diversity: number
  generation: number
  flashIdx: number | null
}

function PopulationGrid({ bestGenes, diversity, generation, flashIdx }: PopGridProps) {
  const rng = mulberry32(generation * 9999 + 1)

  const population = Array.from({ length: POP_SIZE }, (_, i) => {
    if (i === 0) return bestGenes
    const noise = diversity * 0.6
    return bestGenes.map(g => Math.max(0, Math.min(1, g + (rng() - 0.5) * noise)))
  })

  return (
    <div>
      <div className="flex items-center justify-between mb-3">
        <p className="text-xs font-semibold text-zinc-400 uppercase tracking-widest">Population · {POP_SIZE} chromosomes</p>
        <div className="flex items-center gap-3 text-[10px] text-zinc-600">
          <span className="flex items-center gap-1"><span className="w-2 h-2 rounded-sm bg-[#00d4ff]/60 border border-[#00d4ff]/80" />Elite</span>
          <span className="flex items-center gap-1"><span className="w-2 h-2 rounded-sm bg-zinc-700 border border-zinc-600" />Offspring</span>
        </div>
      </div>
      <div className="grid grid-cols-6 gap-1.5">
        {population.map((genes, i) => {
          const isElite = i < ELITE_COUNT
          const isFlashing = flashIdx === i
          const isBest = i === 0
          return (
            <div
              key={i}
              className={`rounded-md overflow-hidden transition-all duration-300 ${
                isBest
                  ? 'ring-2 ring-[#00d4ff]/60 shadow-lg shadow-[#00d4ff]/20 scale-105'
                  : isElite
                  ? 'ring-1 ring-[#00d4ff]/25'
                  : 'opacity-70'
              } ${isFlashing ? 'ring-2 ring-[#ffb800] shadow-[#ffb800]/30 shadow-md scale-105' : ''}`}
            >
              {/* 8 gene segments stacked */}
              {genes.map((val, gi) => (
                <div
                  key={gi}
                  className="h-2 transition-all duration-500"
                  style={{ backgroundColor: geneColor(gi, val) }}
                />
              ))}
            </div>
          )
        })}
      </div>
      <p className="text-[10px] text-zinc-600 mt-2">
        Top {ELITE_COUNT} survive unchanged · remaining {POP_SIZE - ELITE_COUNT} crossover + mutate
      </p>
    </div>
  )
}

// ── Gene tracker ──────────────────────────────────────────────────────────────
function GeneTracker({ genes, prevGenes }: { genes: number[]; prevGenes: number[] | null }) {
  return (
    <div>
      <p className="text-xs font-semibold text-zinc-400 uppercase tracking-widest mb-3">Best Chromosome Genes</p>
      <div className="space-y-2">
        {genes.map((val, i) => {
          const prev = prevGenes?.[i] ?? val
          const delta = val - prev
          const changed = Math.abs(delta) > 0.0001
          return (
            <div key={i} className={`transition-all duration-300 ${changed ? 'opacity-100' : 'opacity-80'}`}>
              <div className="flex items-center justify-between mb-0.5">
                <span className="text-[10px] text-zinc-500 font-mono">{GENE_NAMES[i]}</span>
                <div className="flex items-center gap-1.5">
                  {changed && (
                    <span className={`text-[10px] font-bold font-mono ${delta > 0 ? 'text-[#00ff88]' : 'text-[#ff2d55]'}`}>
                      {delta > 0 ? '↑' : '↓'}{Math.abs(delta).toFixed(3)}
                    </span>
                  )}
                  <span className={`text-[10px] font-mono font-semibold ${changed ? 'text-[#00d4ff]' : 'text-zinc-400'}`}>
                    {val.toFixed(3)}
                  </span>
                </div>
              </div>
              <div className="h-1.5 bg-[#1a2332] rounded-full overflow-hidden">
                <div
                  className="h-full rounded-full transition-all duration-500"
                  style={{
                    width: `${val * 100}%`,
                    backgroundColor: GENE_COLORS[i % GENE_COLORS.length],
                    boxShadow: changed ? `0 0 8px ${GENE_COLORS[i % GENE_COLORS.length]}80` : 'none',
                  }}
                />
              </div>
            </div>
          )
        })}
      </div>
    </div>
  )
}

// ── Event log ─────────────────────────────────────────────────────────────────
interface LogEntry { id: number; text: string; type: 'best' | 'info' | 'warn' | 'done' }

function EventLog({ entries }: { entries: LogEntry[] }) {
  const ref = useRef<HTMLDivElement>(null)
  useEffect(() => {
    if (ref.current) ref.current.scrollTop = ref.current.scrollHeight
  }, [entries])

  return (
    <div>
      <p className="text-xs font-semibold text-zinc-400 uppercase tracking-widest mb-2">Event Log</p>
      <div ref={ref} className="h-36 overflow-y-auto font-mono text-[11px] space-y-0.5 pr-1">
        {entries.length === 0 && (
          <p className="text-zinc-700 italic">Waiting for evolution to start…</p>
        )}
        {entries.map(e => (
          <div key={e.id} className={`animate-ticker-in leading-relaxed ${
            e.type === 'best' ? 'text-[#00ff88]' :
            e.type === 'warn' ? 'text-[#ffb800]' :
            e.type === 'done' ? 'text-[#00d4ff] font-bold' :
            'text-zinc-500'
          }`}>
            {e.text}
          </div>
        ))}
      </div>
    </div>
  )
}

// ── Main ──────────────────────────────────────────────────────────────────────
export default function Evolution() {
  const { settings, setChromosome, activeJobId, setActiveJobId } = useStore()
  const chromosomeGenes = useStore((s) => s.chromosomeGenes)
  const chromosomeFitness = useStore((s) => s.chromosomeFitness)

  useEffect(() => { setActiveJobId(null) }, [])

  const [history, setHistory] = useState<GenPoint[]>([])
  const [status, setStatus] = useState<string>('idle')
  const [finalGenes, setFinalGenes] = useState<number[] | null>(null)
  const [liveGenes, setLiveGenes] = useState<number[] | null>(null)
  const [prevGenes, setPrevGenes] = useState<number[] | null>(null)
  const [diversity, setDiversity] = useState<number>(0)
  const [error, setError] = useState<string | null>(null)
  const [newBest, setNewBest] = useState(false)
  const [flashIdx, setFlashIdx] = useState<number | null>(null)
  const [logEntries, setLogEntries] = useState<LogEntry[]>([])
  const logCounter = useRef(0)
  const prevBestRef = useRef<number>(0)

  function addLog(text: string, type: LogEntry['type'] = 'info') {
    logCounter.current += 1
    setLogEntries(prev => [...prev.slice(-60), { id: logCounter.current, text, type }])
  }

  const handleMessage = useCallback((msg: WsMessage) => {
    if (msg.type === 'generation') {
      const d = msg.data
      setHistory(prev => [...prev, d])
      setDiversity(d.diversity)
      setStatus('running')

      // Gene tracking
      if (d.best_chromosome) {
        setPrevGenes(liveGenes)
        setLiveGenes(d.best_chromosome)
      }

      // New best detection
      const isNewBest = d.best_fitness > prevBestRef.current + 0.0001
      if (isNewBest) {
        const delta = d.best_fitness - prevBestRef.current
        addLog(`Gen ${d.generation}: ★ New best → ${d.best_fitness.toFixed(5)}  +${delta.toFixed(5)}`, 'best')
        prevBestRef.current = d.best_fitness
        setNewBest(true)
        setTimeout(() => setNewBest(false), 800)
      } else {
        if (d.generation % 5 === 0) {
          const divPct = (d.diversity * 100).toFixed(1)
          const divMsg = d.diversity > 0.4 ? 'healthy diversity' : d.diversity > 0.2 ? 'converging' : 'low — near convergence'
          addLog(`Gen ${d.generation}: diversity ${divPct}% — ${divMsg}`, d.diversity < 0.2 ? 'warn' : 'info')
        }
        if (d.generation % 3 === 0) {
          const mutIdx = Math.floor(Math.random() * (30 - 6)) + 6
          setFlashIdx(mutIdx)
          setTimeout(() => setFlashIdx(null), 400)
        }
      }

      // Convergence warning
      if (d.diversity < 0.15 && d.generation > 10) {
        addLog(`Gen ${d.generation}: population converging — may restart soon`, 'warn')
      }

    } else if (msg.type === 'converged') {
      setFinalGenes(msg.data.best_chromosome)
      setChromosome(msg.data.best_chromosome, msg.data.fitness)
      setStatus('converged')
      addLog(`━━ Converged at gen ${msg.data.final_generation} · fitness ${msg.data.fitness.toFixed(5)} ━━`, 'done')
    } else if (msg.type === 'error') {
      setError(msg.data.message)
      setStatus('error')
    }
  }, [setChromosome, liveGenes])

  useWebSocket(activeJobId, { onMessage: handleMessage })

  async function startEvolution() {
    setHistory([]); setError(null); setStatus('starting')
    setLiveGenes(null); setPrevGenes(null)
    setLogEntries([]); prevBestRef.current = 0
    addLog('Initialising population of 30 chromosomes…', 'info')
    addLog('Evaluating initial fitness across 1000 users…', 'info')
    try {
      const r = await evolveApi.start(settings.maxGenerations)
      setActiveJobId(r.data.job_id)
      setStatus('queued')
      addLog('Evolution job started — waiting for first generation…', 'info')
    } catch {
      setError('Failed to start evolution. Is the server running?')
      setStatus('error')
    }
  }

  async function stopEvolution() {
    if (!activeJobId) return
    await evolveApi.stop(activeJobId).catch(() => {})
    setStatus('stopped')
    setActiveJobId(null)
    addLog('Evolution stopped by user.', 'warn')
  }

  async function loadBest() {
    try {
      const r = await evolveApi.loadBest()
      const genes = r.data.chromosome?.genes || r.data.genes
      const fitness = r.data.chromosome?.fitness ?? null
      if (genes) { setChromosome(genes, fitness); setFinalGenes(genes); setLiveGenes(genes) }
    } catch { setError('No saved chromosomes found.') }
  }

  const displayGenes = liveGenes ?? finalGenes ?? chromosomeGenes
  const currentBest = history.length > 0 ? history[history.length - 1].best_fitness : null
  const currentGen  = history.length > 0 ? history[history.length - 1].generation : 0
  const isRunning   = status === 'running' || status === 'queued'

  const statusColor =
    status === 'converged' ? 'text-[#00ff88]' :
    status === 'running'   ? 'text-[#00d4ff]' :
    status === 'error'     ? 'text-[#ff2d55]' :
    'text-zinc-500'

  return (
    <div className="space-y-6 animate-fade-in">
      {/* Header */}
      <div className="page-header flex flex-col sm:flex-row sm:items-center sm:justify-between gap-3">
        <div>
          <h1 className="page-title">Evolution</h1>
          <p className="page-sub">Genetic algorithm evolving the 8-gene ad policy chromosome</p>
        </div>
        <div className="flex gap-2.5 shrink-0">
          <button className="btn-secondary" onClick={loadBest}>Load Best</button>
          {isRunning
            ? <button className="btn-danger" onClick={stopEvolution}>Stop</button>
            : <button className="btn-primary" onClick={startEvolution} disabled={status === 'starting'}>
                {status === 'starting' ? 'Starting…' : 'Start Evolution'}
              </button>
          }
        </div>
      </div>

      {error && <div className="card border-[#ff2d55]/30 bg-[#ff2d55]/5 text-[#ff2d55] text-sm">{error}</div>}

      {/* Status row */}
      <div className="grid grid-cols-2 sm:grid-cols-4 gap-4">
        <div className={`card text-center transition-all duration-300 ${newBest ? 'border-[#00ff88]/50 shadow-glow-accent' : ''}`}>
          <p className="label mb-2">Status</p>
          <p className={`font-bold capitalize ${statusColor} flex items-center justify-center gap-2`}>
            {isRunning && <span className="w-2 h-2 rounded-full bg-[#00d4ff] animate-pulse" />}
            {status}
          </p>
        </div>
        <div className="card text-center">
          <p className="label mb-2">Generation</p>
          <p className="font-mono text-2xl text-zinc-100">{currentGen}</p>
        </div>
        <div className={`card text-center transition-all duration-500 ${newBest ? 'border-[#00ff88]/60 shadow-glow-accent' : ''}`}>
          <p className="label mb-2">Best Fitness</p>
          <p className={`font-mono text-2xl stat-glow-brand ${newBest ? 'text-[#00ff88]' : 'text-[#00d4ff]'} transition-colors duration-300`}>
            {currentBest?.toFixed(4) ?? chromosomeFitness?.toFixed(4) ?? '—'}
          </p>
        </div>
        <div className="card text-center">
          <p className="label mb-2">Diversity</p>
          <div className="flex flex-col items-center gap-1.5">
            <p className={`font-mono text-2xl ${diversity < 0.2 ? 'text-[#ffb800]' : 'text-zinc-200'}`}>
              {(diversity * 100).toFixed(1)}%
            </p>
            <div className="w-full h-1 bg-[#1a2332] rounded-full overflow-hidden">
              <div className="h-full rounded-full transition-all duration-500"
                style={{ width: `${diversity * 100}%`, backgroundColor: diversity < 0.2 ? '#ffb800' : '#00d4ff' }} />
            </div>
          </div>
        </div>
      </div>

      {/* Main viz area */}
      {(isRunning || history.length > 0) && (
        <div className="grid grid-cols-1 lg:grid-cols-3 gap-4">

          {/* Population grid */}
          <div className="card lg:col-span-1">
            {displayGenes ? (
              <PopulationGrid
                bestGenes={displayGenes}
                diversity={diversity}
                generation={currentGen}
                flashIdx={flashIdx}
              />
            ) : (
              <p className="text-zinc-600 text-sm text-center py-8">Waiting for first generation…</p>
            )}
          </div>

          {/* Gene tracker + log */}
          <div className="card lg:col-span-1 space-y-5">
            {displayGenes
              ? <GeneTracker genes={displayGenes} prevGenes={prevGenes} />
              : <p className="text-zinc-600 text-sm text-center py-8">Evolving…</p>
            }
          </div>

          {/* Event log */}
          <div className="card lg:col-span-1">
            <EventLog entries={logEntries} />
          </div>
        </div>
      )}

      {/* Fitness chart */}
      <div className="card">
        <div className="flex items-center justify-between mb-4">
          <h2 className="section-title">Fitness over Generations</h2>
          <span className="text-xs text-zinc-500 font-mono">
            {history.length > 0 ? `${history.length} generations` : 'No data yet'}
          </span>
        </div>
        {history.length > 0
          ? <FitnessChart data={history} />
          : <div className="h-48 flex items-center justify-center text-zinc-600 text-sm">
              Start evolution to see live chart
            </div>
        }
      </div>
    </div>
  )
}
