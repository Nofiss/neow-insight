import { useQuery } from '@tanstack/react-query'

import {
  fetchCardInsights,
  fetchHealth,
  fetchIngestStatus,
  fetchLiveContext,
  fetchRecommendation,
  fetchRunCompleteness,
  fetchRunCharacters,
  fetchRunDetail,
  fetchRuns,
  fetchRunTimeline,
  fetchStats,
  type RunsQuery,
} from './api'
import type { RecommendationContext } from './types'

const DEFAULT_OFFERED = ['CARD.BASH', 'CARD.CLOTHESLINE', 'CARD.OFF_BALANCE']

export function useHealth() {
  return useQuery({
    queryKey: ['health'],
    queryFn: fetchHealth,
    refetchInterval: 15000,
  })
}

export function useStats() {
  return useQuery({
    queryKey: ['runs-stats'],
    queryFn: fetchStats,
    refetchInterval: 10000,
  })
}

export function useRecommendation(offered = DEFAULT_OFFERED, context?: RecommendationContext) {
  return useQuery({
    queryKey: ['recommendation', offered, context ?? null],
    queryFn: () => fetchRecommendation(offered, context),
    refetchInterval: 7000,
    enabled: offered.length > 0,
  })
}

export function useIngestStatus() {
  return useQuery({
    queryKey: ['ingest-status'],
    queryFn: fetchIngestStatus,
    refetchInterval: 5000,
  })
}

export function useCardInsights(offered = DEFAULT_OFFERED) {
  return useQuery({
    queryKey: ['card-insights', offered],
    queryFn: () => fetchCardInsights(offered),
    refetchInterval: 7000,
    enabled: offered.length > 0,
  })
}

export function useLiveContext() {
  return useQuery({
    queryKey: ['live-context'],
    queryFn: fetchLiveContext,
    refetchInterval: 3000,
  })
}

export function useRuns(query: RunsQuery) {
  return useQuery({
    queryKey: ['runs-list', query],
    queryFn: () => fetchRuns(query),
    refetchInterval: 15000,
  })
}

export function useRunDetail(runId: string | null) {
  return useQuery({
    queryKey: ['run-detail', runId],
    queryFn: () => fetchRunDetail(runId as string),
    enabled: Boolean(runId),
    refetchInterval: 15000,
  })
}

export function useRunCharacters() {
  return useQuery({
    queryKey: ['run-characters'],
    queryFn: fetchRunCharacters,
    refetchInterval: 15000,
  })
}

export function useRunTimeline(runId: string | null) {
  return useQuery({
    queryKey: ['run-timeline', runId],
    queryFn: () => fetchRunTimeline(runId as string),
    enabled: Boolean(runId),
    refetchInterval: 15000,
  })
}

export function useRunCompleteness(runId: string | null) {
  return useQuery({
    queryKey: ['run-completeness', runId],
    queryFn: () => fetchRunCompleteness(runId as string),
    enabled: Boolean(runId),
    refetchInterval: 15000,
  })
}

export { DEFAULT_OFFERED }
