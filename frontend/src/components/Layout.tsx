import { Outlet } from 'react-router-dom'
import NavBar from './NavBar'

function StickPeople() {
  return (
    <div className="fixed bottom-4 right-4 z-50 flex items-end gap-2 select-none pointer-events-none">
      {/* Speech bubble */}
      <div className="relative mb-6 bg-[#0d1117] border border-[#00d4ff]/30 text-[#00d4ff] text-[10px] font-bold px-2.5 py-1.5 rounded-xl whitespace-nowrap shadow-lg shadow-[#00d4ff]/10">
        we built this!
        {/* Bubble tail pointing right-down */}
        <span className="absolute -bottom-1.5 right-5 w-2.5 h-2.5 bg-[#0d1117] border-r border-b border-[#00d4ff]/30 rotate-45" />
      </div>

      {/* Guy 1 */}
      <svg width="22" height="44" viewBox="0 0 22 44" fill="none" xmlns="http://www.w3.org/2000/svg" className="animate-[float_3s_ease-in-out_infinite]">
        {/* head */}
        <circle cx="11" cy="6" r="5" stroke="#00d4ff" strokeWidth="1.8" fill="none"/>
        {/* body */}
        <line x1="11" y1="11" x2="11" y2="27" stroke="#00d4ff" strokeWidth="1.8" strokeLinecap="round"/>
        {/* left arm raised */}
        <line x1="11" y1="16" x2="3" y2="11" stroke="#00d4ff" strokeWidth="1.8" strokeLinecap="round"/>
        {/* right arm */}
        <line x1="11" y1="16" x2="19" y2="20" stroke="#00d4ff" strokeWidth="1.8" strokeLinecap="round"/>
        {/* left leg */}
        <line x1="11" y1="27" x2="5" y2="38" stroke="#00d4ff" strokeWidth="1.8" strokeLinecap="round"/>
        {/* right leg */}
        <line x1="11" y1="27" x2="17" y2="38" stroke="#00d4ff" strokeWidth="1.8" strokeLinecap="round"/>
      </svg>

      {/* Girl (hair) */}
      <svg width="24" height="46" viewBox="0 0 24 46" fill="none" xmlns="http://www.w3.org/2000/svg" className="animate-[float_3.4s_ease-in-out_0.4s_infinite]">
        {/* hair */}
        <path d="M6 8 Q6 2 12 2 Q18 2 18 8 Q20 10 18 13 Q16 7 12 7 Q8 7 6 13 Q4 10 6 8Z" fill="#00ff88" opacity="0.8"/>
        {/* head */}
        <circle cx="12" cy="9" r="5" stroke="#00ff88" strokeWidth="1.8" fill="none"/>
        {/* body — skirt shape */}
        <line x1="12" y1="14" x2="12" y2="28" stroke="#00ff88" strokeWidth="1.8" strokeLinecap="round"/>
        {/* skirt */}
        <path d="M7 28 Q12 32 17 28" stroke="#00ff88" strokeWidth="1.8" strokeLinecap="round" fill="none"/>
        {/* arms both up */}
        <line x1="12" y1="18" x2="3" y2="13" stroke="#00ff88" strokeWidth="1.8" strokeLinecap="round"/>
        <line x1="12" y1="18" x2="21" y2="13" stroke="#00ff88" strokeWidth="1.8" strokeLinecap="round"/>
        {/* legs */}
        <line x1="10" y1="28" x2="6" y2="40" stroke="#00ff88" strokeWidth="1.8" strokeLinecap="round"/>
        <line x1="14" y1="28" x2="18" y2="40" stroke="#00ff88" strokeWidth="1.8" strokeLinecap="round"/>
      </svg>

      {/* Guy 2 */}
      <svg width="22" height="44" viewBox="0 0 22 44" fill="none" xmlns="http://www.w3.org/2000/svg" className="animate-[float_2.8s_ease-in-out_0.8s_infinite]">
        {/* head */}
        <circle cx="11" cy="6" r="5" stroke="#00d4ff" strokeWidth="1.8" fill="none"/>
        {/* body */}
        <line x1="11" y1="11" x2="11" y2="27" stroke="#00d4ff" strokeWidth="1.8" strokeLinecap="round"/>
        {/* arms both raised */}
        <line x1="11" y1="16" x2="2" y2="10" stroke="#00d4ff" strokeWidth="1.8" strokeLinecap="round"/>
        <line x1="11" y1="16" x2="20" y2="10" stroke="#00d4ff" strokeWidth="1.8" strokeLinecap="round"/>
        {/* left leg */}
        <line x1="11" y1="27" x2="4" y2="38" stroke="#00d4ff" strokeWidth="1.8" strokeLinecap="round"/>
        {/* right leg */}
        <line x1="11" y1="27" x2="18" y2="38" stroke="#00d4ff" strokeWidth="1.8" strokeLinecap="round"/>
      </svg>
    </div>
  )
}

export default function Layout() {
  return (
    <div className="min-h-screen bg-[#080b0f]">
      <NavBar />
      <main className="max-w-7xl mx-auto px-4 sm:px-6 py-6 sm:py-8">
        <Outlet />
      </main>
      <StickPeople />
    </div>
  )
}
