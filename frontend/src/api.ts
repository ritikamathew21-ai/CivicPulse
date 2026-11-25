export type Dataset = 'demo' | 'live'
export type SignalType = 'rainfall' | 'traffic' | 'incident'
export type AlertStatus = 'new' | 'acknowledged' | 'resolved'

export interface Signal {
  id: number
  type: SignalType
  lat: number
  lon: number
  value: number
  observed_at: string
  source: string
  description: string
  hypothesis_id: string | null
  reason: string
}

export interface Evidence {
  factor: string
  weight: number
  points: number
  detail: string
}

export interface Asset {
  kind: string
  name: string
  distance_m: number
  lat: number
  lon: number
}

export interface Hypothesis {
  id: string
  title: string
  score: number
  lat: number
  lon: number
  started_at: string
  ended_at: string
  signal_ids: number[]
  aligned_pairs: number
  evidence: Evidence[]
  assets: Asset[]
  rain_anomaly: 'unusual' | 'extreme' | null
  priority: { level: 'high' | 'medium' | 'low'; value: number; reasons: string[] }
  status: AlertStatus
  new_signals: number
}

export interface Analysis {
  radius_km: number
  window_min: number
  stats: { received: number; aligned: number; excluded: number; aligned_pairs: number }
  signals: Signal[]
  hypotheses: Hypothesis[]
}

export interface NewSignal {
  dataset: Dataset
  type: SignalType
  lat: number
  lon: number
  value: number
  observed_at: string
  description: string
}

async function request<T>(path: string, init?: RequestInit): Promise<T> {
  const response = await fetch(`/api${path}`, {
    ...init,
    headers: { 'Content-Type': 'application/json' },
  })
  if (!response.ok) {
    const detail = (await response.json().catch(() => null))?.detail
    const message = Array.isArray(detail) ? detail.map((d) => d.msg).join('; ') : detail
    throw new Error(message || `The CivicPulse server is not responding (${response.status})`)
  }
  return response.json()
}

const post = (path: string, body?: unknown) =>
  request(path, { method: 'POST', body: body ? JSON.stringify(body) : undefined })

export const api = {
  analysis: (dataset: Dataset, radiusKm: number, windowMin: number, signal: AbortSignal) =>
    request<Analysis>(
      `/analysis?dataset=${dataset}&radius_km=${radiusKm}&window_min=${windowMin}`,
      { signal },
    ),
  loadDemo: (scenario: 'single' | 'multi') => post(`/demo/${scenario}`),
  refreshRainfall: () => post('/live/rainfall'),
  report: (signal: NewSignal) => post('/signals', signal),
  decide: (dataset: Dataset, status: AlertStatus, signal_ids: number[]) =>
    post('/decisions', { dataset, status, signal_ids }),
}

export const TYPES: Record<
  SignalType,
  { label: string; letter: string; unit: string; min: number; max: number; initial: number }
> = {
  rainfall: { label: 'Rainfall', letter: 'R', unit: 'mm/h', min: 0, max: 500, initial: 20 },
  traffic: { label: 'Traffic slowdown', letter: 'T', unit: '%', min: 0, max: 100, initial: 50 },
  incident: { label: 'Road incident', letter: 'I', unit: 'severity (1–5)', min: 1, max: 5, initial: 3 },
}

export const clock = (iso: string) =>
  new Date(iso).toLocaleTimeString([], { hour: '2-digit', minute: '2-digit' })

export const percent = (score: number) => `${Math.round(score * 100)}%`
