import { useEffect, useRef, useState, useCallback } from 'react'

export type WsMessage =
  | { type: 'generation'; data: { generation: number; best_fitness: number; avg_fitness: number; diversity: number } }
  | { type: 'converged'; data: { final_generation: number; best_chromosome: number[]; fitness: number } }
  | { type: 'error'; data: { message: string } }
  | { type: 'stopped'; data: Record<string, never> }

interface Options {
  onMessage?: (msg: WsMessage) => void
  autoReconnect?: boolean
  reconnectDelayMs?: number
}

export function useWebSocket(jobId: string | null, options: Options = {}) {
  const { onMessage, autoReconnect = true, reconnectDelayMs = 3000 } = options
  const wsRef = useRef<WebSocket | null>(null)
  const [connected, setConnected] = useState(false)
  const reconnectTimer = useRef<ReturnType<typeof setTimeout> | null>(null)
  const stoppedRef = useRef(false)

  const connect = useCallback(() => {
    if (!jobId || stoppedRef.current) return
    const proto = window.location.protocol === 'https:' ? 'wss' : 'ws'
    const ws = new WebSocket(`${proto}://${window.location.host}/ws/evolve/${jobId}`)
    wsRef.current = ws

    ws.onopen = () => setConnected(true)
    ws.onclose = () => {
      setConnected(false)
      if (autoReconnect && !stoppedRef.current) {
        reconnectTimer.current = setTimeout(connect, reconnectDelayMs)
      }
    }
    ws.onerror = () => ws.close()
    ws.onmessage = (e) => {
      try {
        const msg = JSON.parse(e.data) as WsMessage
        onMessage?.(msg)
        if (msg.type === 'converged' || msg.type === 'stopped') {
          stoppedRef.current = true
        }
      } catch { /* ignore malformed messages */ }
    }
  }, [jobId, autoReconnect, reconnectDelayMs, onMessage])

  const send = useCallback((msg: object) => {
    if (wsRef.current?.readyState === WebSocket.OPEN) {
      wsRef.current.send(JSON.stringify(msg))
    }
  }, [])

  const disconnect = useCallback(() => {
    stoppedRef.current = true
    if (reconnectTimer.current) clearTimeout(reconnectTimer.current)
    wsRef.current?.close()
  }, [])

  useEffect(() => {
    stoppedRef.current = false
    connect()
    return () => {
      stoppedRef.current = true
      if (reconnectTimer.current) clearTimeout(reconnectTimer.current)
      wsRef.current?.close()
    }
  }, [connect])

  return { connected, send, disconnect }
}
