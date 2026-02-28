/**
 * API client for the Miroir backend.
 * Uses VITE_API_URL or defaults to http://localhost:8000.
 */

const API_BASE =
  (typeof import.meta !== 'undefined' && (import.meta as { env?: { VITE_API_URL?: string } }).env?.VITE_API_URL) ||
  'http://localhost:8000'

export function apiUrl(path: string): string {
  const p = path.startsWith('/') ? path : `/${path}`
  return `${API_BASE}${p}`
}

export async function apiGet<T = unknown>(path: string): Promise<T> {
  const res = await fetch(apiUrl(path))
  if (!res.ok) {
    const text = await res.text()
    throw new Error(`API ${res.status}: ${text || res.statusText}`)
  }
  return res.json() as Promise<T>
}

export async function apiPost<T = unknown>(path: string, body?: unknown): Promise<T> {
  const res = await fetch(apiUrl(path), {
    method: 'POST',
    headers: body ? { 'Content-Type': 'application/json' } : undefined,
    body: body ? JSON.stringify(body) : undefined,
  })
  if (!res.ok) {
    const text = await res.text()
    throw new Error(`API ${res.status}: ${text || res.statusText}`)
  }
  return res.json() as Promise<T>
}

export async function apiPut<T = unknown>(path: string, body: unknown): Promise<T> {
  const res = await fetch(apiUrl(path), {
    method: 'PUT',
    headers: { 'Content-Type': 'application/json' },
    body: JSON.stringify(body),
  })
  if (!res.ok) {
    const text = await res.text()
    throw new Error(`API ${res.status}: ${text || res.statusText}`)
  }
  return res.json() as Promise<T>
}

export type Contact = {
  id: string
  name: string
  email: string
  behavior_profile: Record<string, unknown>
  risk_score?: number
  trust_score?: number
  updated_at?: string
}

export type ContactListItem = Pick<Contact, 'id' | 'name' | 'email'> & {
  risk_score?: number
  trust_score?: number
}

export type BusinessSettings = {
  description: string
  script_or_edge_cases: string
  updated_at?: string
}

export type ContextItem = {
  id: string
  name: string
  type: string
  size?: number | null
  uploaded_at?: string | null
}
