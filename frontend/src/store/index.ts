import { create } from 'zustand'
import { persist } from 'zustand/middleware'

interface Settings {
  llmEnabled: boolean
  llmProvider: 'groq' | 'gemini' | 'off'
  maxGenerations: number
  populationSize: number
  darkMode: boolean
}

interface AdaptAdStore {
  // Active chromosome
  chromosomeGenes: number[] | null
  chromosomeFitness: number | null
  setChromosome: (genes: number[], fitness?: number) => void
  clearChromosome: () => void

  // Current evolution job
  activeJobId: string | null
  setActiveJobId: (id: string | null) => void

  // Settings
  settings: Settings
  updateSettings: (partial: Partial<Settings>) => void

  // Total decisions made this session
  totalDecisions: number
  incrementDecisions: () => void
}

export const useStore = create<AdaptAdStore>()(
  persist(
    (set) => ({
      chromosomeGenes: null,
      chromosomeFitness: null,
      setChromosome: (genes, fitness) =>
        set({ chromosomeGenes: genes, chromosomeFitness: fitness ?? null }),
      clearChromosome: () => set({ chromosomeGenes: null, chromosomeFitness: null }),

      activeJobId: null,
      setActiveJobId: (id) => set({ activeJobId: id }),

      totalDecisions: 0,
      incrementDecisions: () => set((s) => ({ totalDecisions: s.totalDecisions + 1 })),

      settings: {
        llmEnabled: false,
        llmProvider: 'groq',
        maxGenerations: 50,
        populationSize: 30,
        darkMode: true,
      },
      updateSettings: (partial) =>
        set((s) => ({ settings: { ...s.settings, ...partial } })),
    }),
    { name: 'adaptad-store' }
  )
)
