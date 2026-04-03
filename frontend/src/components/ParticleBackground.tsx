import { useEffect, useRef } from 'react'

interface Particle {
  x: number; y: number; z: number   // z: 0 (far) → 1 (close)
  vx: number; vy: number; vz: number
  r: number                          // base radius
  color: string
}

const COLORS = ['#00d4ff', '#00ff88', '#00d4ff', '#a78bfa', '#00d4ff']

export default function ParticleBackground() {
  const canvasRef = useRef<HTMLCanvasElement>(null)

  useEffect(() => {
    const canvas = canvasRef.current
    if (!canvas) return
    const ctx = canvas.getContext('2d')
    if (!ctx) return

    const c = canvas   // non-null alias
    const g = ctx      // non-null alias
    let animId: number
    let W = 0, H = 0

    function resize() {
      W = c.width  = window.innerWidth
      H = c.height = window.innerHeight
    }
    resize()
    window.addEventListener('resize', resize)

    // Build particle cloud
    const N = 70
    const particles: Particle[] = Array.from({ length: N }, () => ({
      x:  Math.random() * W,
      y:  Math.random() * H,
      z:  Math.random(),                          // depth
      vx: (Math.random() - 0.5) * 0.3,
      vy: (Math.random() - 0.5) * 0.3,
      vz: (Math.random() - 0.5) * 0.002,         // slow depth drift
      r:  Math.random() * 1.5 + 0.5,
      color: COLORS[Math.floor(Math.random() * COLORS.length)],
    }))

    function project(p: Particle) {
      // Perspective: far particles are smaller, dimmer, slower
      const scale = 0.3 + p.z * 0.7
      return { scale, alpha: 0.08 + p.z * 0.35 }
    }

    function draw() {
      g.clearRect(0, 0, W, H)

      // Sort by depth so far particles draw first (painter's algorithm)
      const sorted = [...particles].sort((a, b) => a.z - b.z)

      // Draw connections between nearby particles
      for (let i = 0; i < sorted.length; i++) {
        for (let j = i + 1; j < sorted.length; j++) {
          const a = sorted[i], b = sorted[j]
          const dx = a.x - b.x, dy = a.y - b.y
          const dist = Math.sqrt(dx * dx + dy * dy)
          const maxDist = 160

          if (dist < maxDist) {
            const depthFactor = (a.z + b.z) / 2
            const alpha = (1 - dist / maxDist) * depthFactor * 0.12
            g.beginPath()
            g.strokeStyle = `rgba(0,212,255,${alpha.toFixed(3)})`
            g.lineWidth = depthFactor * 0.8
            g.moveTo(a.x, a.y)
            g.lineTo(b.x, b.y)
            g.stroke()
          }
        }
      }

      // Draw particles
      for (const p of sorted) {
        const { scale, alpha } = project(p)
        const radius = p.r * scale * 2.5

        // Glow for closer particles
        if (p.z > 0.6) {
          const grd = g.createRadialGradient(p.x, p.y, 0, p.x, p.y, radius * 3)
          grd.addColorStop(0, `${p.color}${Math.round(alpha * 80).toString(16).padStart(2, '0')}`)
          grd.addColorStop(1, 'transparent')
          g.beginPath()
          g.arc(p.x, p.y, radius * 3, 0, Math.PI * 2)
          g.fillStyle = grd
          g.fill()
        }

        g.beginPath()
        g.arc(p.x, p.y, radius, 0, Math.PI * 2)
        g.fillStyle = `${p.color}${Math.round(alpha * 255).toString(16).padStart(2, '0')}`
        g.fill()
      }

      // Update positions
      for (const p of particles) {
        p.x += p.vx * (0.4 + p.z * 0.6)    // far particles move slower
        p.y += p.vy * (0.4 + p.z * 0.6)
        p.z += p.vz
        if (p.z < 0) { p.z = 0; p.vz *= -1 }
        if (p.z > 1) { p.z = 1; p.vz *= -1 }
        if (p.x < -20) p.x = W + 20
        if (p.x > W + 20) p.x = -20
        if (p.y < -20) p.y = H + 20
        if (p.y > H + 20) p.y = -20
      }

      animId = requestAnimationFrame(draw)
    }

    draw()

    return () => {
      cancelAnimationFrame(animId)
      window.removeEventListener('resize', resize)
    }
  }, [])

  return (
    <canvas
      ref={canvasRef}
      className="fixed inset-0 w-full h-full pointer-events-none"
      style={{ zIndex: 0, opacity: 1 }}
    />
  )
}
