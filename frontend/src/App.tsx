import { BrowserRouter, Routes, Route } from 'react-router-dom'
import Layout from './components/Layout'
import Dashboard from './pages/Dashboard'
import Evolution from './pages/Evolution'
import DecisionExplorer from './pages/DecisionExplorer'
import SessionSimulator from './pages/SessionSimulator'
import BatchResults from './pages/BatchResults'
import ABTesting from './pages/ABTesting'
import Settings from './pages/Settings'

export default function App() {
  return (
    <BrowserRouter>
      <Routes>
        <Route path="/" element={<Layout />}>
          <Route index element={<Dashboard />} />
          <Route path="evolve" element={<Evolution />} />
          <Route path="decide" element={<DecisionExplorer />} />
          <Route path="simulate" element={<SessionSimulator />} />
          <Route path="batch" element={<BatchResults />} />
          <Route path="ab-test" element={<ABTesting />} />
          <Route path="settings" element={<Settings />} />
        </Route>
      </Routes>
    </BrowserRouter>
  )
}
