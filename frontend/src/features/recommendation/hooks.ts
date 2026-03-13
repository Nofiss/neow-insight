import { useQuery } from '@tanstack/react-query'

import {
  fetchHealth,
  fetchIngestStatus,
  fetchRecommendation,
  fetchStats,
} from './api'

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

export function useRecommendation(offered = DEFAULT_OFFERED) {
  return useQuery({
    queryKey: ['recommendation', offered],
    queryFn: () => fetchRecommendation(offered),
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

export { DEFAULT_OFFERED }
