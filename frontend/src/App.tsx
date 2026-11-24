import { useCallback, useEffect, useState } from 'react'
import RawSerialWidget from './components/RawSerialWidget'
import { ApiError, api } from './services/api'
import { websocket, type WebSocketState } from './services/websocket'
import './App.css'

type HealthState = 'checking' | 'online' | 'offline'
type SerialState = 'checking' | 'connected' | 'disconnected' | 'unknown'

function errorMessage(error: unknown): string {
  if (error instanceof ApiError) return error.message
  if (error instanceof Error) return error.message
  return String(error)
}

interface StatusCardProps {
  title: string
  tone: string
  value: string
  detail: string
}

function StatusCard({ title, tone, value, detail }: StatusCardProps) {
  return (
    <article className={`status-card ${tone}`}>
      <span className="status-title">{title}</span>
      <span className="status-value">
        <span className="status-dot" aria-hidden="true" />
        {value}
      </span>
      <span className="status-detail">{detail}</span>
    </article>
  )
}

function App() {
  const [health, setHealth] = useState<HealthState>('checking')
  const [healthDetail, setHealthDetail] = useState('Contacting the server…')
  const [serial, setSerial] = useState<SerialState>('checking')
  const [serialDetail, setSerialDetail] = useState('Checking the serial port…')
  const [wsState, setWsState] = useState<WebSocketState>(websocket.state)
  const [lastChecked, setLastChecked] = useState<Date | null>(null)

  const refresh = useCallback(async () => {
    const [healthResult, serialResult] = await Promise.allSettled([
      api.getHealth(),
      api.serial.getStatus(),
    ])

    if (healthResult.status === 'fulfilled') {
      setHealth('online')
      setHealthDetail(
        healthResult.value.status === 'ok'
          ? 'FastAPI is responding'
          : `Server says "${healthResult.value.status}"`,
      )
    } else {
      setHealth('offline')
      setHealthDetail(errorMessage(healthResult.reason))
    }

    if (serialResult.status === 'fulfilled') {
      setSerial(serialResult.value ? 'connected' : 'disconnected')
      setSerialDetail(
        serialResult.value
          ? 'A serial port is open'
          : 'No serial port is open',
      )
    } else {
      setSerial('unknown')
      setSerialDetail(errorMessage(serialResult.reason))
    }

    setLastChecked(new Date())
  }, [])

  useEffect(() => {
    // The first status check is intentionally kicked off on mount.
    // oxlint-disable-next-line react/set-state-in-effect
    void refresh()
    const timer = window.setInterval(() => {
      void refresh()
    }, 5000)

    return () => {
      window.clearInterval(timer)
    }
  }, [refresh])

  useEffect(() => {
    const unsubscribe = websocket.onStateChange(setWsState)
    websocket.connect()

    return () => {
      unsubscribe()
      websocket.disconnect()
    }
  }, [])

  const wsLabel =
    wsState === 'connected'
      ? 'Connected'
      : wsState === 'connecting'
        ? 'Connecting…'
        : 'Disconnected'

  const serialLabel =
    serial === 'connected'
      ? 'Connected'
      : serial === 'disconnected'
        ? 'Disconnected'
        : serial === 'unknown'
          ? 'Unknown'
          : 'Checking…'
  const serialTone =
    serial === 'connected'
      ? 'connected'
      : serial === 'checking'
        ? 'checking'
        : serial === 'unknown'
          ? 'unknown'
          : 'neutral'

  return (
    <main className="app">
      <header className="app-header">
        <div>
          <h1>GCGUI Web</h1>
          <p>Browser dashboard for the FastAPI serial server.</p>
        </div>
        <button
          type="button"
          className="refresh-button"
          onClick={() => void refresh()}
        >
          Refresh status
        </button>
      </header>

      <section className="status-grid" aria-label="Server status">
        <StatusCard
          title="HTTP API"
          tone={health}
          value={
            health === 'online'
              ? 'Online'
              : health === 'offline'
                ? 'Offline'
                : 'Checking…'
          }
          detail={healthDetail}
        />
        <StatusCard
          title="WebSocket"
          tone={wsState}
          value={wsLabel}
          detail="Live serial data channel"
        />
        <StatusCard
          title="Serial port"
          tone={serialTone}
          value={serialLabel}
          detail={serialDetail}
        />
      </section>

      <section className="monitor" aria-label="Raw serial data">
        <RawSerialWidget />
      </section>

      <footer className="app-footer">
        {lastChecked
          ? `Last API check: ${lastChecked.toLocaleTimeString()}`
          : 'Waiting for the first API check…'}
      </footer>
    </main>
  )
}

export default App
