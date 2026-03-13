export interface Recommendation {
  best_pick: string | null
  win_rate_boost: number
  confidence: number
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
