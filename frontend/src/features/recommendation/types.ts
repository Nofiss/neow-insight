export interface Recommendation {
  best_pick: string | null
  win_rate_boost: number
  confidence: number
  sample_size: number
  card_win_rate: number
  global_win_rate: number
  reason:
    | 'ok_contextual'
    | 'low_sample_contextual'
    | 'ok_global'
    | 'low_sample_global'
    | 'no_history_global'
    | 'fallback_global_no_context'
    | 'no_candidates'
  scope: 'character_ascension_floor' | 'character_ascension' | 'character' | 'ascension' | 'global'
  applied_filters: string[]
  fallback_used: boolean
}

export interface RecommendationContext {
  character?: string
  ascension?: number
  floor?: number
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
  recent_issues: IngestIssue[]
  last_processed_run_id: string | null
  last_processed_file: string | null
  last_event_at: string | null
}

export interface IngestIssue {
  kind: string
  file_path: string
  message: string
  timestamp: string
}

export interface LiveContext {
  available: boolean
  run_id: string | null
  character: string | null
  ascension: number | null
  floor: number | null
  offered_cards: string[]
  picked_card: string | null
}

export interface RunListItem {
  run_id: string
  seed: string | null
  character: string | null
  ascension: number | null
  win: boolean
  raw_timestamp: string | null
  imported_at: string
  source_file: string | null
  card_choice_count: number
  relic_count: number
}

export interface RunsListResponse {
  page: number
  page_size: number
  total: number
  total_pages: number
  items: RunListItem[]
}

export interface RunCardChoice {
  floor: number
  offered_cards: string[]
  picked_card: string
  is_shop: boolean
}

export interface RunRelic {
  relic_id: string
  floor: number
}

export interface RunDetail {
  run_id: string
  seed: string | null
  character: string | null
  ascension: number | null
  win: boolean
  raw_timestamp: string | null
  imported_at: string
  source_file: string | null
  card_choices: RunCardChoice[]
  relic_history: RunRelic[]
  raw_payload: Record<string, unknown>
}

export interface RunTimelineEvent {
  floor: number
  kind: string
  summary: string
  data: Record<string, unknown>
}

export interface RunTimeline {
  run_id: string
  events: RunTimelineEvent[]
}

export interface RunCompleteness {
  run_id: string
  available: number
  available_direct: number
  available_inferred: number
  total: number
  missing: string[]
  inferred: string[]
}
