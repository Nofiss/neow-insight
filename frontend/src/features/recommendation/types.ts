export interface Recommendation {
  best_pick: string | null
  win_rate_boost: number
  confidence: number
  sample_size: number
  card_win_rate: number
  global_win_rate: number
  reason: 'ok' | 'low_sample' | 'no_history' | 'no_candidates'
}

export interface CardInsight {
  card: string
  sample_size: number
  card_win_rate: number
  win_rate_boost: number
}

export interface CardInsights {
  global_win_rate: number
  insights: CardInsight[]
}

export interface RunStats {
  total_runs: number
  wins: number
  win_rate: number
}

export interface HealthStatus {
  status: string
  version: string
  watcher_enabled: boolean
}

export interface IngestStatus {
  scanned: number
  imported: number
  updated: number
  parse_errors: number
  skipped: number
}
