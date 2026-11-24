/**
 * HTTP client for the FastAPI backend.
 *
 * Requests are same-origin by default. During `vite dev`, Vite proxies
 * `/api` to FastAPI (see vite.config.ts). Set `VITE_API_BASE_URL` when the
 * frontend is served from a different origin than the backend.
 */

export interface HealthResponse {
  status: string
}

export interface SerialConnectOptions {
  port: string
  baudrate?: number
  timeout?: number
}

export interface SerialConnection {
  connected: boolean
  port: string
  baudrate: number
}

const API_BASE_URL = (import.meta.env.VITE_API_BASE_URL ?? '').replace(/\/+$/, '')

export class ApiError extends Error {
  readonly status: number
  readonly detail: unknown

  constructor(status: number, message: string, detail?: unknown) {
    super(message)
    this.name = 'ApiError'
    this.status = status
    this.detail = detail
  }
}

function describeDetail(detail: unknown): string {
  if (typeof detail === 'string') return detail

  // FastAPI validation errors are arrays of { loc, msg, type } objects.
  if (Array.isArray(detail)) {
    const messages = detail
      .map((entry) => {
        if (typeof entry === 'object' && entry !== null && 'msg' in entry) {
          const message = (entry as { msg?: unknown }).msg
          if (typeof message === 'string') return message
        }
        return null
      })
      .filter((message): message is string => message !== null)

    if (messages.length > 0) return messages.join('; ')
  }

  if (detail !== undefined && detail !== null) {
    try {
      return JSON.stringify(detail)
    } catch {
      return String(detail)
    }
  }

  return ''
}

async function request<T>(path: string, init?: RequestInit): Promise<T> {
  let response: Response

  try {
    response = await fetch(`${API_BASE_URL}${path}`, init)
  } catch (error) {
    const target = API_BASE_URL || window.location.origin
    throw new ApiError(0, `Could not reach the server at ${target}`, error)
  }

  if (!response.ok) {
    const body = await response.text()
    let detail: unknown = body

    if (body) {
      try {
        detail = JSON.parse(body)
      } catch {
        // Keep the raw response text as the detail.
      }
    }

    const apiDetail =
      typeof detail === 'object' && detail !== null && 'detail' in detail
        ? (detail as { detail: unknown }).detail
        : detail
    const message =
      describeDetail(apiDetail) || `Request failed with status ${response.status}`

    throw new ApiError(response.status, message, apiDetail)
  }

  if (response.status === 204) {
    return undefined as T
  }

  return (await response.json()) as T
}

function postJson<T>(path: string, body: unknown): Promise<T> {
  return request<T>(path, {
    method: 'POST',
    headers: { 'Content-Type': 'application/json' },
    body: JSON.stringify(body),
  })
}

export const api = {
  getHealth: () => request<HealthResponse>('/api/health'),

  serial: {
    getPorts: () => request<string[]>('/api/serial/ports'),
    getStatus: () => request<boolean>('/api/serial/status'),

    connect: (options: SerialConnectOptions) =>
      postJson<SerialConnection>('/api/serial/connect', {
        baudrate: 115200,
        timeout: 1,
        ...options,
      }),

    disconnect: () =>
      request<boolean>('/api/serial/disconnect', { method: 'POST' }),

    send: (data: string) => postJson<number>('/api/serial/send', { data }),

    sendRaw: (data: Uint8Array | ArrayBuffer | Blob) =>
      request<number>('/api/serial/send_raw', {
        method: 'POST',
        headers: { 'Content-Type': 'application/octet-stream' },
        body: data as BodyInit,
      }),
  },
}
