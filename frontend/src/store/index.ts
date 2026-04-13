import { create } from 'zustand'
import { persist } from 'zustand/middleware'

interface Settings {
  llmEnabled: boolean
  llmProvider: 'groq' | 'gemini' | 'off'
  maxGenerations: number
  populationSize: number
  darkMode: boolean
}

interface ABSession {
  session_id: string
  user_name: string
  content_title: string
  session_x: unknown[]
  session_y: unknown[]
  x_is_adaptad?: boolean
  user_profile?: unknown
  content_profile?: unknown
  session_context?: unknown
}

interface ABRating {
  annoyance: number
  relevance: number
  willingness: number
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

  // A/B test state (persisted across reloads)
  abSession: ABSession | null
  abXRating: ABRating
  abYRating: ABRating
  abSubmitted: boolean
  setAbSession: (s: ABSession | null) => void
  setAbXRating: (r: ABRating) => void
  setAbYRating: (r: ABRating) => void
  setAbSubmitted: (v: boolean) => void
  clearAbTest: () => void
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

      abSession: null,
      abXRating: { annoyance: 0, relevance: 0, willingness: 0 },
      abYRating: { annoyance: 0, relevance: 0, willingness: 0 },
      abSubmitted: false,
      setAbSession: (s) => set({ abSession: s }),
      setAbXRating: (r) => set({ abXRating: r }),
      setAbYRating: (r) => set({ abYRating: r }),
      setAbSubmitted: (v) => set({ abSubmitted: v }),
      clearAbTest: () => set({
        abSession: null,
        abXRating: { annoyance: 0, relevance: 0, willingness: 0 },
        abYRating: { annoyance: 0, relevance: 0, willingness: 0 },
        abSubmitted: false,
      }),

      settings: {
        llmEnabled: false,
        llmProvider: 'groq',
        maxGenerations: 50,
        populationSize: 30,
        darkMode: true,
      },
      updateSettings: (partial) => {
        set((s) => ({ settings: { ...s.settings, ...partial } }))
        if (partial.darkMode !== undefined) {
          if (partial.darkMode) {
            document.documentElement.classList.add('dark')
          } else {
            document.documentElement.classList.remove('dark')
          }
        }
      },
    }),
    {
      name: 'adaptad-store',
      onRehydrateStorage: () => (state) => {
        if (state) {
          if (state.settings.darkMode) {
            document.documentElement.classList.add('dark')
          } else {
            document.documentElement.classList.remove('dark')
          }
        }
      },
    }
  )
)
