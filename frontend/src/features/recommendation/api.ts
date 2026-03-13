import type {
  HealthStatus,
  IngestStatus,
  Recommendation,
  RunStats,
} from './types'

const API_BASE = '/api'

async function fetchJson<T>(path: string): Promise<T> {
  const response = await fetch(`${API_BASE}${path}`)
  if (!response.ok) {
    throw new Error(`API error ${response.status}`)
  }
  return (await response.json()) as T
}

export function fetchHealth(): Promise<HealthStatus> {
  return fetchJson<HealthStatus>('/health')
}

export function fetchStats(): Promise<RunStats> {
  return fetchJson<RunStats>('/runs/stats')
}

export function fetchRecommendation(cards: string[]): Promise<Recommendation> {
  const query = new URLSearchParams({ cards: cards.join(',') }).toString()
  return fetchJson<Recommendation>(`/recommendation?${query}`)
}

export function fetchIngestStatus(): Promise<IngestStatus> {
  return fetchJson<IngestStatus>('/ingest/status')
}
