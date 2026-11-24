/**
 * WebSocket client for the FastAPI `/ws` endpoint.
 *
 * The URL is derived from the current page by default, so the Vite dev proxy
 * and a same-origin production deploy both work without configuration.
 * Set `VITE_WS_URL` to override it, for example `ws://192.168.1.20:8000/ws`.
 */

export type WebSocketState = 'connecting' | 'connected' | 'disconnected'

export interface HelloMessage {
  type: 'hello'
  message: string
}

export interface PongMessage {
  type: 'pong'
}

export interface SerialDataMessage {
  type: 'serial_data'
  timestamp: string
  data: string
}

export interface UnknownMessage {
  type: string
  [key: string]: unknown
}

export type ServerMessage =
  | HelloMessage
  | PongMessage
  | SerialDataMessage
  | UnknownMessage

type Listener<T> = (value: T) => void

const RECONNECT_DELAYS_MS = [1000, 2000, 4000, 8000, 10000]

function resolveWebSocketUrl(): string {
  const configured = import.meta.env.VITE_WS_URL
  if (typeof configured === 'string' && configured.length > 0) {
    return configured
  }

  const protocol = window.location.protocol === 'https:' ? 'wss:' : 'ws:'
  return `${protocol}//${window.location.host}/ws`
}

function isServerMessage(value: unknown): value is ServerMessage {
  return (
    typeof value === 'object' &&
    value !== null &&
    'type' in value &&
    typeof (value as { type?: unknown }).type === 'string'
  )
}

export class WebSocketClient {
  private socket: WebSocket | null = null
  private reconnectTimer: ReturnType<typeof setTimeout> | null = null
  private reconnectAttempt = 0
  private shouldReconnect = true
  private currentState: WebSocketState = 'disconnected'

  private readonly messageListeners = new Set<Listener<ServerMessage>>()
  private readonly serialDataListeners = new Set<Listener<SerialDataMessage>>()
  private readonly stateListeners = new Set<Listener<WebSocketState>>()

  get state(): WebSocketState {
    return this.currentState
  }

  connect(): void {
    this.shouldReconnect = true

    if (
      this.socket &&
      (this.socket.readyState === WebSocket.CONNECTING ||
        this.socket.readyState === WebSocket.OPEN)
    ) {
      return
    }

    this.clearReconnectTimer()
    this.setState('connecting')

    let socket: WebSocket
    try {
      socket = new WebSocket(resolveWebSocketUrl())
    } catch (error) {
      console.error('Failed to create WebSocket:', error)
      this.setState('disconnected')
      this.scheduleReconnect()
      return
    }

    this.socket = socket

    socket.addEventListener('open', () => {
      if (this.socket !== socket) return
      this.reconnectAttempt = 0
      this.setState('connected')
    })

    socket.addEventListener('message', (event: MessageEvent) => {
      if (this.socket !== socket) return
      this.handleMessage(event.data)
    })

    socket.addEventListener('close', () => {
      if (this.socket !== socket) return
      this.socket = null
      this.setState('disconnected')
      this.scheduleReconnect()
    })

    socket.addEventListener('error', () => {
      // The browser follows an error with a close event, which updates the
      // state and schedules the reconnect.
      console.warn('WebSocket connection error')
    })
  }

  disconnect(): void {
    this.shouldReconnect = false
    this.clearReconnectTimer()

    const socket = this.socket
    this.socket = null

    if (socket && socket.readyState <= WebSocket.OPEN) {
      socket.close()
    }

    this.setState('disconnected')
  }

  send(data: string): boolean {
    if (!this.socket || this.socket.readyState !== WebSocket.OPEN) {
      return false
    }

    this.socket.send(data)
    return true
  }

  ping(): boolean {
    return this.send('ping')
  }

  onMessage(listener: Listener<ServerMessage>): () => void {
    this.messageListeners.add(listener)
    return () => {
      this.messageListeners.delete(listener)
    }
  }

  onSerialData(listener: Listener<SerialDataMessage>): () => void {
    this.serialDataListeners.add(listener)
    return () => {
      this.serialDataListeners.delete(listener)
    }
  }

  onStateChange(listener: Listener<WebSocketState>): () => void {
    this.stateListeners.add(listener)
    listener(this.currentState)
    return () => {
      this.stateListeners.delete(listener)
    }
  }

  private handleMessage(raw: unknown): void {
    if (typeof raw !== 'string') {
      console.debug('Ignoring non-text WebSocket message')
      return
    }

    let parsed: unknown
    try {
      parsed = JSON.parse(raw)
    } catch {
      console.warn('Ignoring non-JSON WebSocket message:', raw)
      return
    }

    if (!isServerMessage(parsed)) {
      console.warn('Ignoring WebSocket message without a type:', parsed)
      return
    }

    for (const listener of this.messageListeners) {
      listener(parsed)
    }

    if (parsed.type === 'serial_data') {
      const message = parsed as SerialDataMessage
      if (
        typeof message.timestamp === 'string' &&
        typeof message.data === 'string'
      ) {
        for (const listener of this.serialDataListeners) {
          listener(message)
        }
      }
    }
  }

  private setState(state: WebSocketState): void {
    if (this.currentState === state) return

    this.currentState = state
    for (const listener of this.stateListeners) {
      listener(state)
    }
  }

  private scheduleReconnect(): void {
    if (!this.shouldReconnect || this.reconnectTimer !== null) return

    const delay =
      RECONNECT_DELAYS_MS[
        Math.min(this.reconnectAttempt, RECONNECT_DELAYS_MS.length - 1)
      ]
    this.reconnectAttempt += 1

    this.reconnectTimer = setTimeout(() => {
      this.reconnectTimer = null
      this.connect()
    }, delay)
  }

  private clearReconnectTimer(): void {
    if (this.reconnectTimer === null) return

    clearTimeout(this.reconnectTimer)
    this.reconnectTimer = null
  }
}

export const websocket = new WebSocketClient()
