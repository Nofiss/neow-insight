import type { RunTimelineEvent } from './types'

const HIGH_PRIORITY_MISSING_FIELDS = new Set([
  'Score',
  'Floor reached',
  'Card choices',
  'Event choices',
  'Campfire choices',
])

const MEDIUM_PRIORITY_MISSING_FIELDS = new Set([
  'Gold',
  'Gold per floor',
  'Boss relics',
  'Potions obtained',
])

const DECISION_EVENT_KINDS = new Set(['card_choice', 'campfire', 'event', 'boss_relic'])

export const REASON_LABELS = {
  low_sample_contextual: 'Campione contestuale ridotto: usa il suggerimento con cautela.',
  ok_contextual: 'Suggerimento contestuale supportato dai dati disponibili.',
  low_sample_global: 'Campione globale ridotto: indicazione ancora debole.',
  ok_global: 'Suggerimento globale stabile sullo storico disponibile.',
  no_history_global: 'Storico assente: suggerimento basato su fallback iniziale.',
  fallback_global_no_context:
    'Nessuno storico nel contesto richiesto: fallback automatico al globale.',
  no_candidates: 'Nessuna carta valida ricevuta in input.',
} as const

export const TIMELINE_KIND_STYLES: Record<string, string> = {
  card_choice: 'border-amber-300 bg-amber-100 text-amber-900',
  relic: 'border-blue-300 bg-blue-100 text-blue-900',
  campfire: 'border-orange-300 bg-orange-100 text-orange-900',
  event: 'border-violet-300 bg-violet-100 text-violet-900',
  potion: 'border-emerald-300 bg-emerald-100 text-emerald-900',
  boss_relic: 'border-rose-300 bg-rose-100 text-rose-900',
}

export const TIMELINE_KIND_LABELS: Record<string, string> = {
  all: 'Tutti',
  card_choice: 'Card choice',
  relic: 'Relic',
  campfire: 'Campfire',
  event: 'Event',
  potion: 'Potion',
  boss_relic: 'Boss relic',
}

export function asPercent(value: number): string {
  return `${(value * 100).toFixed(1)}%`
}

export function parseCardsInput(value: string): string[] {
  return value
    .split(',')
    .map((part) => part.trim())
    .filter(Boolean)
}

export function formatUpdatedAt(timestamp: number): string {
  if (!timestamp) {
    return '-'
  }
  return new Intl.DateTimeFormat('it-IT', {
    hour: '2-digit',
    minute: '2-digit',
    second: '2-digit',
  }).format(new Date(timestamp))
}

export function formatIsoDate(value: string | null | undefined): string {
  if (!value) {
    return '-'
  }
  const date = new Date(value)
  if (Number.isNaN(date.getTime())) {
    return value
  }
  return date.toLocaleString('it-IT')
}

export function formatTimelineFloor(event: RunTimelineEvent): string {
  if (event.kind === 'boss_relic' && event.floor >= 900) {
    return 'boss chest'
  }
  return `floor ${event.floor}`
}

function toStringArray(value: unknown): string[] {
  if (!Array.isArray(value)) {
    return []
  }
  return value.filter((item): item is string => typeof item === 'string' && item.length > 0)
}

export function eventMeta(event: RunTimelineEvent): string | null {
  if (event.kind === 'card_choice') {
    const offered = toStringArray(event.data.offered_cards)
    const source = event.data.is_shop === true ? 'shop' : 'reward'
    if (!offered.length) {
      return `source ${source}`
    }
    return `source ${source} - offered ${offered.join(', ')}`
  }

  if (event.kind === 'event') {
    const removed = toStringArray(event.data.cards_removed)
    const obtained = toStringArray(event.data.cards_obtained)
    const lines: string[] = []
    if (removed.length) {
      lines.push(`removed ${removed.join(', ')}`)
    }
    if (obtained.length) {
      lines.push(`obtained ${obtained.join(', ')}`)
    }
    return lines.length ? lines.join(' - ') : null
  }

  if (event.kind === 'boss_relic') {
    const skipped = toStringArray(event.data.not_picked)
    if (skipped.length) {
      return `skipped ${skipped.join(', ')}`
    }
  }

  return null
}

export function eventSearchBlob(event: RunTimelineEvent): string {
  return `${event.kind} ${event.summary} ${JSON.stringify(event.data)}`.toLowerCase()
}

export function eventStableKey(event: RunTimelineEvent): string {
  return `${event.floor}-${event.kind}-${event.summary}-${JSON.stringify(event.data)}`
}

function asFiniteNumber(value: unknown): number | null {
  if (typeof value === 'number' && Number.isFinite(value)) {
    return value
  }
  if (typeof value === 'string') {
    const parsed = Number(value)
    if (Number.isFinite(parsed)) {
      return parsed
    }
  }
  return null
}

function mapPointEntries(rawPayload: Record<string, unknown>): Record<string, unknown>[] {
  const history = rawPayload.map_point_history
  if (!Array.isArray(history)) {
    return []
  }

  const points: Record<string, unknown>[] = []
  for (const act of history) {
    if (!Array.isArray(act)) {
      continue
    }
    for (const point of act) {
      if (point && typeof point === 'object') {
        points.push(point as Record<string, unknown>)
      }
    }
  }
  return points
}

function deriveFloorReachedFromMapHistory(rawPayload: Record<string, unknown>): number | null {
  const points = mapPointEntries(rawPayload)
  return points.length > 0 ? points.length : null
}

function deriveFinalGoldFromMapHistory(rawPayload: Record<string, unknown>): number | null {
  let lastGold: number | null = null
  for (const point of mapPointEntries(rawPayload)) {
    const playerStats = point.player_stats
    if (!Array.isArray(playerStats)) {
      continue
    }
    for (const stats of playerStats) {
      if (!stats || typeof stats !== 'object') {
        continue
      }
      const candidate = asFiniteNumber((stats as Record<string, unknown>).current_gold)
      if (candidate !== null) {
        lastGold = candidate
      }
    }
  }
  return lastGold
}

export function runQuickStats(rawPayload: Record<string, unknown>): {
  score: number | null
  floorReached: number | null
  finalGold: number | null
  floorReachedSource: string
  finalGoldSource: string
  floorReachedDerived: boolean
  finalGoldDerived: boolean
} {
  const score = asFiniteNumber(rawPayload.score)
  let floorReached = asFiniteNumber(rawPayload.floor_reached)
  let floorReachedSource = 'floor_reached'
  let floorReachedDerived = false
  if (floorReached === null) {
    floorReached = deriveFloorReachedFromMapHistory(rawPayload)
    if (floorReached !== null) {
      floorReachedSource = 'map_point_history length'
      floorReachedDerived = true
    }
  }

  let finalGold = asFiniteNumber(rawPayload.gold)
  let finalGoldSource = 'gold'
  let finalGoldDerived = false
  if (finalGold === null && Array.isArray(rawPayload.gold_per_floor)) {
    const values = rawPayload.gold_per_floor
      .map((entry) => asFiniteNumber(entry))
      .filter((entry): entry is number => entry !== null)
    finalGold = values.length ? values[values.length - 1] : null
    if (finalGold !== null) {
      finalGoldSource = 'gold_per_floor[-1]'
      finalGoldDerived = true
    }
  }

  if (finalGold === null) {
    finalGold = deriveFinalGoldFromMapHistory(rawPayload)
    if (finalGold !== null) {
      finalGoldSource = 'map_point_history[].player_stats[].current_gold'
      finalGoldDerived = true
    }
  }

  return {
    score,
    floorReached,
    finalGold,
    floorReachedSource,
    finalGoldSource,
    floorReachedDerived,
    finalGoldDerived,
  }
}

export function asNumberLabel(value: number | null): string {
  if (value === null) {
    return '-'
  }
  return new Intl.NumberFormat('it-IT').format(value)
}

export function metricAvailabilityLabel(value: number | null): string {
  return value === null ? 'dato assente' : 'dato disponibile'
}

export function metricAvailabilityStyle(value: number | null): string {
  if (value === null) {
    return 'border-zinc-300 bg-zinc-100 text-zinc-700'
  }
  return 'border-emerald-300 bg-emerald-100 text-emerald-800'
}

export function metricSourceLabel(isDerived: boolean): string {
  return isDerived ? 'derived' : 'raw'
}

export function metricSourceStyle(isDerived: boolean): string {
  if (isDerived) {
    return 'border-amber-300 bg-amber-100 text-amber-800'
  }
  return 'border-sky-300 bg-sky-100 text-sky-800'
}

export function downloadRunJson(runId: string, payload: Record<string, unknown>): void {
  const blob = new Blob([JSON.stringify(payload, null, 2)], { type: 'application/json' })
  const objectUrl = URL.createObjectURL(blob)
  const link = document.createElement('a')
  link.href = objectUrl
  link.download = `${runId}.json`
  document.body.appendChild(link)
  link.click()
  document.body.removeChild(link)
  URL.revokeObjectURL(objectUrl)
}

export function missingSeverity(missingLabels: string[]): 'low' | 'medium' | 'high' {
  if (!missingLabels.length) {
    return 'low'
  }

  const hasHigh = missingLabels.some((label) => HIGH_PRIORITY_MISSING_FIELDS.has(label))
  if (hasHigh) {
    return 'high'
  }

  const hasMedium = missingLabels.some((label) => MEDIUM_PRIORITY_MISSING_FIELDS.has(label))
  if (hasMedium) {
    return 'medium'
  }

  return 'low'
}

export function severityBadgeClass(severity: 'low' | 'medium' | 'high'): string {
  if (severity === 'high') {
    return 'border-red-300 bg-red-100 text-red-800'
  }
  if (severity === 'medium') {
    return 'border-amber-300 bg-amber-100 text-amber-800'
  }
  return 'border-emerald-300 bg-emerald-100 text-emerald-800'
}

export function completenessInferenceLevel(
  availableDirect: number,
  availableInferred: number,
): 'direct' | 'mixed' | 'inferred' {
  if (availableInferred <= 0) {
    return 'direct'
  }
  if (availableInferred >= availableDirect) {
    return 'inferred'
  }
  return 'mixed'
}

export function completenessInferenceBadgeClass(level: 'direct' | 'mixed' | 'inferred'): string {
  if (level === 'inferred') {
    return 'border-amber-300 bg-amber-100 text-amber-800'
  }
  if (level === 'mixed') {
    return 'border-sky-300 bg-sky-100 text-sky-800'
  }
  return 'border-emerald-300 bg-emerald-100 text-emerald-800'
}

export function isDecisionEvent(kind: string): boolean {
  return DECISION_EVENT_KINDS.has(kind)
}
