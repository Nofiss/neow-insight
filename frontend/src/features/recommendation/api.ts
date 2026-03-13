import type {
  CardInsights,
  HealthStatus,
  IngestStatus,
  LiveContext,
  Recommendation,
  RecommendationContext,
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

export function fetchRecommendation(
  cards: string[],
  context?: RecommendationContext,
): Promise<Recommendation> {
  const params = new URLSearchParams({ cards: cards.join(',') })
  if (context?.character) {
    params.set('character', context.character)
  }
  if (typeof context?.ascension === 'number') {
    params.set('ascension', String(context.ascension))
  }
  if (typeof context?.floor === 'number') {
    params.set('floor', String(context.floor))
  }
  const query = params.toString()
  return fetchJson<Recommendation>(`/recommendation?${query}`)
}

export function fetchIngestStatus(): Promise<IngestStatus> {
  return fetchJson<IngestStatus>('/ingest/status')
}

export function fetchCardInsights(cards: string[]): Promise<CardInsights> {
  const query = new URLSearchParams({ cards: cards.join(',') }).toString()
  return fetchJson<CardInsights>(`/runs/card-insights?${query}`)
}

export function fetchLiveContext(): Promise<LiveContext> {
  return fetchJson<LiveContext>('/live/context')
}
