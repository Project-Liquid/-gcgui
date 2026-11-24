import { useEffect, useRef, useState } from 'react'
import {
  websocket,
  type SerialDataMessage,
  type WebSocketState,
} from '../services/websocket'
import './RawSerialWidget.css'

const MAX_LINES = 100

interface SerialLine {
  id: number
  time: string
  data: string
}

function formatTimestamp(timestamp: string): string {
  const date = new Date(timestamp)
  return Number.isNaN(date.getTime()) ? timestamp : date.toLocaleTimeString()
}

function statusLabel(state: WebSocketState): string {
  if (state === 'connected') return '● Live'
  if (state === 'connecting') return '◌ Connecting'
  return '○ Offline'
}

/**
 * Live serial feed, ported from the original RawSerialWidget.
 *
 * This replaces the old `window.electronAPI.onSerialData(...)` usage with a
 * subscription to the FastAPI WebSocket. Recording/replay controls are not
 * ported yet because those backend services do not exist.
 */
export default function RawSerialWidget() {
  const [lines, setLines] = useState<SerialLine[]>([])
  const [autoScroll, setAutoScroll] = useState(true)
  const [connection, setConnection] = useState<WebSocketState>(websocket.state)
  const contentRef = useRef<HTMLDivElement>(null)
  const nextId = useRef(0)

  useEffect(() => {
    // Replaces window.electronAPI.onSerialData(...) from the original widget.
    const unsubscribeData = websocket.onSerialData(
      (message: SerialDataMessage) => {
        setLines((previous) => {
          const next = [
            ...previous,
            {
              id: nextId.current++,
              time: formatTimestamp(message.timestamp),
              data: message.data,
            },
          ]
          return next.slice(-MAX_LINES)
        })
      },
    )
    const unsubscribeState = websocket.onStateChange(setConnection)
    websocket.connect()

    return () => {
      unsubscribeData()
      unsubscribeState()
    }
  }, [])

  useEffect(() => {
    if (autoScroll && contentRef.current) {
      contentRef.current.scrollTop = contentRef.current.scrollHeight
    }
  }, [lines, autoScroll])

  return (
    <div className="raw-serial-widget fill">
      <div className="widget-header">
        <div className="widget-name">Raw Serial Data</div>
        <div className={`connection-status ${connection}`}>
          {statusLabel(connection)}
        </div>
      </div>

      <div className="raw-data-container">
        <div className="raw-data-header">
          <span>Time</span>
          <span>Data</span>
          <button
            type="button"
            className={`lock-button ${autoScroll ? 'active' : ''}`}
            onClick={() => setAutoScroll((value) => !value)}
            title={
              autoScroll
                ? 'Autoscroll locked to bottom (click to unlock)'
                : 'Autoscroll unlocked (click to lock to bottom)'
            }
          >
            {autoScroll ? '🔒 Lock' : '🔓'}
          </button>
          <button
            type="button"
            className="clear-button"
            onClick={() => setLines([])}
            title="Clear data"
          >
            Clear
          </button>
        </div>

        <div className="raw-data-content" ref={contentRef}>
          {lines.length === 0 ? (
            <div className="no-data">
              {connection === 'connected'
                ? 'Listening… Waiting for serial data...'
                : 'Waiting for the server connection...'}
            </div>
          ) : (
            lines.map((line) => (
              <div key={line.id} className="raw-data-line">
                <span className="timestamp">{line.time}</span>
                <span className="data-value">{line.data}</span>
              </div>
            ))
          )}
        </div>
      </div>
    </div>
  )
}
