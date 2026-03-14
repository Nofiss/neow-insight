import type {
  CardInsights,
  HealthStatus,
  IngestStatus,
  LiveContext,
  Recommendation,
  RecommendationContext,
  RunCharacters,
  RunCompleteness,
  RunDetail,
  RunStats,
  RunsListResponse,
  RunTimeline,
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

export interface RunsQuery {
  page?: number
  pageSize?: number
  character?: string
  ascension?: number
  win?: boolean
  query?: string
}

export function fetchRuns(filters: RunsQuery = {}): Promise<RunsListResponse> {
  const params = new URLSearchParams()
  params.set('page', String(filters.page ?? 1))
  params.set('page_size', String(filters.pageSize ?? 20))
  if (filters.character?.trim()) {
    params.set('character', filters.character.trim().toUpperCase())
  }
  if (typeof filters.ascension === 'number') {
    params.set('ascension', String(filters.ascension))
  }
  if (typeof filters.win === 'boolean') {
    params.set('win', String(filters.win))
  }
  if (filters.query?.trim()) {
    params.set('query', filters.query.trim())
  }
  return fetchJson<RunsListResponse>(`/runs?${params.toString()}`)
}

export function fetchRunCharacters(): Promise<RunCharacters> {
  return fetchJson<RunCharacters>('/runs/characters')
}

export function fetchRunDetail(runId: string): Promise<RunDetail> {
  return fetchJson<RunDetail>(`/runs/${encodeURIComponent(runId)}`)
}

export function fetchRunTimeline(runId: string): Promise<RunTimeline> {
  return fetchJson<RunTimeline>(`/runs/${encodeURIComponent(runId)}/timeline`)
}

export function fetchRunCompleteness(runId: string): Promise<RunCompleteness> {
  return fetchJson<RunCompleteness>(`/runs/${encodeURIComponent(runId)}/completeness`)
}
