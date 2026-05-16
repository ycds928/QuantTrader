import { useEffect, useRef, useCallback, useState } from 'react'

interface UseWebSocketOptions {
  onMessage?: (data: unknown) => void
  onOpen?: () => void
  onClose?: () => void
  onError?: (error: Event) => void
  reconnectInterval?: number
  maxRetries?: number
}

export function useWebSocket(
  path: string,
  options: UseWebSocketOptions = {}
) {
  const {
    onMessage,
    onOpen,
    onClose,
    onError,
    reconnectInterval = 3000,
    maxRetries = 5,
  } = options

  const wsRef = useRef<WebSocket | null>(null)
  const retriesRef = useRef(0)
  const [connected, setConnected] = useState(false)

  const connect = useCallback(() => {
    const protocol = window.location.protocol === 'https:' ? 'wss:' : 'ws:'
    const host = window.location.host
    const url = `${protocol}//${host}${path}`

    const ws = new WebSocket(url)

    ws.onopen = () => {
      setConnected(true)
      retriesRef.current = 0
      onOpen?.()
    }

    ws.onmessage = (event) => {
      try {
        const data = JSON.parse(event.data)
        onMessage?.(data)
      } catch {
        onMessage?.(event.data)
      }
    }

    ws.onclose = () => {
      setConnected(false)
      onClose?.()
      if (retriesRef.current < maxRetries) {
        retriesRef.current++
        setTimeout(connect, reconnectInterval)
      }
    }

    ws.onerror = (error) => {
      onError?.(error)
    }

    wsRef.current = ws
  }, [path, onMessage, onOpen, onClose, onError, reconnectInterval, maxRetries])

  useEffect(() => {
    connect()
    return () => {
      wsRef.current?.close()
    }
  }, [connect])

  const send = useCallback((data: unknown) => {
    if (wsRef.current?.readyState === WebSocket.OPEN) {
      wsRef.current.send(JSON.stringify(data))
    }
  }, [])

  return { connected, send }
}
