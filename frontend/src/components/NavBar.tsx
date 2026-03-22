import { NavLink } from 'react-router-dom'
import { useStore } from '../store'

const links = [
  { to: '/', label: 'Dashboard' },
  { to: '/evolve', label: 'Evolution' },
  { to: '/decide', label: 'Decisions' },
  { to: '/simulate', label: 'Simulator' },
  { to: '/batch', label: 'Batch' },
  { to: '/ab-test', label: 'A/B Test' },
  { to: '/settings', label: 'Settings' },
]

export default function NavBar() {
  const fitness = useStore((s) => s.chromosomeFitness)

  return (
    <nav className="flex items-center gap-1 px-4 py-3 bg-gray-900 border-b border-gray-800 sticky top-0 z-50">
      <span className="font-bold text-indigo-400 mr-4 text-lg">AdaptAd</span>
      {links.map((l) => (
        <NavLink
          key={l.to}
          to={l.to}
          end={l.to === '/'}
          className={({ isActive }) =>
            `px-3 py-1.5 rounded-lg text-sm font-medium transition-colors ${
              isActive ? 'bg-indigo-600 text-white' : 'text-gray-400 hover:text-gray-100 hover:bg-gray-800'
            }`
          }
        >
          {l.label}
        </NavLink>
      ))}
      {fitness != null && (
        <span className="ml-auto text-xs text-gray-500">
          Chromosome fitness: <span className="text-indigo-400 font-mono">{fitness.toFixed(4)}</span>
        </span>
      )}
    </nav>
  )
}
