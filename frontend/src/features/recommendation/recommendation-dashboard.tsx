import { useEffect, useMemo, useState } from 'react'
import { Alert, AlertDescription, AlertTitle } from '@/components/ui/alert'
import { Badge } from '@/components/ui/badge'
import { Card, CardContent, CardDescription, CardHeader, CardTitle } from '@/components/ui/card'
import { Skeleton } from '@/components/ui/skeleton'

import {
  DEFAULT_OFFERED,
  useCardInsights,
  useHealth,
  useIngestStatus,
  useLiveContext,
  useRecommendation,
  useRunCompleteness,
  useRunDetail,
  useRuns,
  useRunTimeline,
  useStats,
} from './hooks'
import type { RunTimelineEvent } from './types'

const DEFAULT_CHARACTER = 'IRONCLAD'
const DEFAULT_ASCENSION = 10
const DEFAULT_FLOOR = 1

function asPercent(value: number): string {
  return `${(value * 100).toFixed(1)}%`
}

function parseCardsInput(value: string): string[] {
  return value
    .split(',')
    .map((part) => part.trim())
    .filter(Boolean)
}

function formatUpdatedAt(timestamp: number): string {
  if (!timestamp) {
    return '-'
  }
  return new Intl.DateTimeFormat('it-IT', {
    hour: '2-digit',
    minute: '2-digit',
    second: '2-digit',
  }).format(new Date(timestamp))
}

function formatIsoDate(value: string | null | undefined): string {
  if (!value) {
    return '-'
  }
  const date = new Date(value)
  if (Number.isNaN(date.getTime())) {
    return value
  }
  return date.toLocaleString('it-IT')
}

const REASON_LABELS = {
  low_sample_contextual: 'Campione contestuale ridotto: usa il suggerimento con cautela.',
  ok_contextual: 'Suggerimento contestuale supportato dai dati disponibili.',
  low_sample_global: 'Campione globale ridotto: indicazione ancora debole.',
  ok_global: 'Suggerimento globale stabile sullo storico disponibile.',
  no_history_global: 'Storico assente: suggerimento basato su fallback iniziale.',
  fallback_global_no_context:
    'Nessuno storico nel contesto richiesto: fallback automatico al globale.',
  no_candidates: 'Nessuna carta valida ricevuta in input.',
} as const

const TIMELINE_KIND_STYLES: Record<string, string> = {
  card_choice: 'border-amber-300 bg-amber-100 text-amber-900',
  relic: 'border-blue-300 bg-blue-100 text-blue-900',
  campfire: 'border-orange-300 bg-orange-100 text-orange-900',
  event: 'border-violet-300 bg-violet-100 text-violet-900',
  potion: 'border-emerald-300 bg-emerald-100 text-emerald-900',
  boss_relic: 'border-rose-300 bg-rose-100 text-rose-900',
}

const TIMELINE_KIND_LABELS: Record<string, string> = {
  all: 'Tutti',
  card_choice: 'Card choice',
  relic: 'Relic',
  campfire: 'Campfire',
  event: 'Event',
  potion: 'Potion',
  boss_relic: 'Boss relic',
}

const DECISION_EVENT_KINDS = new Set(['card_choice', 'campfire', 'event', 'boss_relic'])

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

function formatTimelineFloor(event: RunTimelineEvent): string {
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

function eventMeta(event: RunTimelineEvent): string | null {
  if (event.kind === 'card_choice') {
    const offered = toStringArray(event.data.offered_cards)
    const source = event.data.is_shop === true ? 'shop' : 'reward'
    if (!offered.length) {
      return `source ${source}`
    }
    return `source ${source} • offered ${offered.join(', ')}`
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
    return lines.length ? lines.join(' • ') : null
  }

  if (event.kind === 'boss_relic') {
    const skipped = toStringArray(event.data.not_picked)
    if (skipped.length) {
      return `skipped ${skipped.join(', ')}`
    }
  }

  return null
}

function eventSearchBlob(event: RunTimelineEvent): string {
  return `${event.kind} ${event.summary} ${JSON.stringify(event.data)}`.toLowerCase()
}

function eventStableKey(event: RunTimelineEvent): string {
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

function runQuickStats(rawPayload: Record<string, unknown>): {
  score: number | null
  floorReached: number | null
  finalGold: number | null
} {
  const score = asFiniteNumber(rawPayload.score)
  const floorReached = asFiniteNumber(rawPayload.floor_reached)

  let finalGold = asFiniteNumber(rawPayload.gold)
  if (finalGold === null && Array.isArray(rawPayload.gold_per_floor)) {
    const values = rawPayload.gold_per_floor
      .map((entry) => asFiniteNumber(entry))
      .filter((entry): entry is number => entry !== null)
    finalGold = values.length ? values[values.length - 1] : null
  }

  return { score, floorReached, finalGold }
}

function asNumberLabel(value: number | null): string {
  if (value === null) {
    return '-'
  }
  return new Intl.NumberFormat('it-IT').format(value)
}

function metricAvailabilityLabel(value: number | null): string {
  return value === null ? 'dato assente' : 'dato disponibile'
}

function metricAvailabilityStyle(value: number | null): string {
  if (value === null) {
    return 'border-zinc-300 bg-zinc-100 text-zinc-700'
  }
  return 'border-emerald-300 bg-emerald-100 text-emerald-800'
}

function downloadRunJson(runId: string, payload: Record<string, unknown>): void {
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

function missingSeverity(missingLabels: string[]): 'low' | 'medium' | 'high' {
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

function severityBadgeClass(severity: 'low' | 'medium' | 'high'): string {
  if (severity === 'high') {
    return 'border-red-300 bg-red-100 text-red-800'
  }
  if (severity === 'medium') {
    return 'border-amber-300 bg-amber-100 text-amber-800'
  }
  return 'border-emerald-300 bg-emerald-100 text-emerald-800'
}

export function RecommendationDashboard() {
  const [cardsInput, setCardsInput] = useState(DEFAULT_OFFERED.join(', '))
  const [characterInput, setCharacterInput] = useState(DEFAULT_CHARACTER)
  const [ascensionInput, setAscensionInput] = useState(DEFAULT_ASCENSION)
  const [floorInput, setFloorInput] = useState(DEFAULT_FLOOR)
  const [useLiveInput, setUseLiveInput] = useState(true)
  const [runsPage, setRunsPage] = useState(1)
  const [runsPageSize, setRunsPageSize] = useState(20)
  const [runsCharacterFilter, setRunsCharacterFilter] = useState('')
  const [runsAscensionFilter, setRunsAscensionFilter] = useState('')
  const [runsWinFilter, setRunsWinFilter] = useState<'all' | 'wins' | 'losses'>('all')
  const [runsQueryFilter, setRunsQueryFilter] = useState('')
  const [timelineKindFilter, setTimelineKindFilter] = useState('all')
  const [timelineQueryFilter, setTimelineQueryFilter] = useState('')
  const [showDecisionOnly, setShowDecisionOnly] = useState(false)
  const [selectedRunId, setSelectedRunId] = useState<string | null>(null)
  const offeredCards = useMemo(() => parseCardsInput(cardsInput), [cardsInput])
  const manualRecommendationContext = useMemo(
    () => ({
      character: characterInput.trim().toUpperCase(),
      ascension: Math.max(0, Math.floor(ascensionInput || 0)),
      floor: Math.max(0, Math.floor(floorInput || 0)),
    }),
    [characterInput, ascensionInput, floorInput],
  )

  const liveContext = useLiveContext()
  const liveCards = liveContext.data?.offered_cards ?? []
  const liveIsUsable = Boolean(liveContext.data?.available && liveCards.length > 0)

  const activeCards = useMemo(() => {
    if (useLiveInput && liveIsUsable) {
      return liveCards
    }
    return offeredCards
  }, [liveCards, liveIsUsable, offeredCards, useLiveInput])

  const activeRecommendationContext = useMemo(() => {
    if (useLiveInput && liveIsUsable) {
      return {
        character: liveContext.data?.character?.trim().toUpperCase() ?? '',
        ascension: Math.max(0, Math.floor(liveContext.data?.ascension ?? 0)),
        floor: Math.max(0, Math.floor(liveContext.data?.floor ?? 0)),
      }
    }
    return manualRecommendationContext
  }, [liveContext.data, liveIsUsable, manualRecommendationContext, useLiveInput])

  const health = useHealth()
  const stats = useStats()
  const recommendation = useRecommendation(activeCards, activeRecommendationContext)
  const cardInsights = useCardInsights(activeCards)
  const ingestStatus = useIngestStatus()
  const parsedAscension = Number(runsAscensionFilter)
  const ascensionFilterValue =
    runsAscensionFilter.trim() === '' || !Number.isFinite(parsedAscension)
      ? undefined
      : Math.max(0, Math.floor(parsedAscension))
  const runs = useRuns({
    page: runsPage,
    pageSize: runsPageSize,
    character: runsCharacterFilter.trim() || undefined,
    ascension: ascensionFilterValue,
    win: runsWinFilter === 'all' ? undefined : runsWinFilter === 'wins',
    query: runsQueryFilter.trim() || undefined,
  })
  const runDetail = useRunDetail(selectedRunId)
  const runTimeline = useRunTimeline(selectedRunId)
  const runCompleteness = useRunCompleteness(selectedRunId)

  const hasError =
    health.isError ||
    stats.isError ||
    recommendation.isError ||
    cardInsights.isError ||
    ingestStatus.isError

  const recommendationReason = recommendation.data?.reason
  const reasonLabel = REASON_LABELS[recommendationReason ?? 'ok_global']
  const liveUpdatedAt = formatUpdatedAt(liveContext.dataUpdatedAt)

  const runItems = runs.data?.items ?? []
  const selectedRun = runDetail.data
  const timelineEvents = runTimeline.data?.events ?? []
  const selectedRunStats = useMemo(
    () => (selectedRun ? runQuickStats(selectedRun.raw_payload) : null),
    [selectedRun],
  )
  const selectedRunCompleteness = runCompleteness.data
  const completenessSeverity = selectedRunCompleteness
    ? missingSeverity(selectedRunCompleteness.missing)
    : null
  const hasQuickStats =
    selectedRunStats !== null &&
    (selectedRunStats.score !== null ||
      selectedRunStats.floorReached !== null ||
      selectedRunStats.finalGold !== null)

  const timelineKinds = useMemo(() => {
    const kinds = new Set<string>()
    for (const event of timelineEvents) {
      kinds.add(event.kind)
    }
    return ['all', ...Array.from(kinds).sort()]
  }, [timelineEvents])

  const filteredTimelineEvents = useMemo(() => {
    const query = timelineQueryFilter.trim().toLowerCase()
    return timelineEvents.filter((event) => {
      if (showDecisionOnly && !DECISION_EVENT_KINDS.has(event.kind)) {
        return false
      }
      if (timelineKindFilter !== 'all' && event.kind !== timelineKindFilter) {
        return false
      }
      if (!query) {
        return true
      }
      return eventSearchBlob(event).includes(query)
    })
  }, [timelineEvents, showDecisionOnly, timelineKindFilter, timelineQueryFilter])

  const groupedTimelineEvents = useMemo(() => {
    const groups = new Map<number, RunTimelineEvent[]>()
    for (const event of filteredTimelineEvents) {
      const current = groups.get(event.floor)
      if (current) {
        current.push(event)
      } else {
        groups.set(event.floor, [event])
      }
    }

    return Array.from(groups.entries())
      .sort(([floorA], [floorB]) => floorA - floorB)
      .map(([floor, events]) => ({ floor, events }))
  }, [filteredTimelineEvents])

  useEffect(() => {
    if (selectedRunId && runItems.some((item) => item.run_id === selectedRunId)) {
      return
    }
    setSelectedRunId(runItems[0]?.run_id ?? null)
  }, [runItems, selectedRunId])

  useEffect(() => {
    if (timelineKinds.includes(timelineKindFilter)) {
      return
    }
    setTimelineKindFilter('all')
  }, [timelineKindFilter, timelineKinds])

  return (
    <main className="mx-auto flex min-h-dvh w-full max-w-5xl flex-col gap-6 px-4 py-8 sm:px-6 lg:py-12">
      <section className="rounded-2xl border border-zinc-300/80 bg-gradient-to-r from-amber-50 via-orange-50 to-red-50 p-6 shadow-sm">
        <p className="mb-2 text-xs font-semibold tracking-[0.2em] text-zinc-500 uppercase">
          Neow's Insight
        </p>
        <h1 className="text-3xl leading-tight font-semibold text-zinc-900 sm:text-4xl">
          Decision dashboard live per Slay the Spire 2
        </h1>
        <p className="mt-3 max-w-2xl text-sm text-zinc-600 sm:text-base">
          Suggerimenti carta e trend storico ricavati dalle tue run locali.
        </p>
      </section>

      {hasError ? (
        <Alert className="border-red-300 bg-red-50/80">
          <AlertTitle>Backend non raggiungibile</AlertTitle>
          <AlertDescription>
            Avvia l'API con `uv run api-dev` nella cartella `backend` e riprova.
          </AlertDescription>
        </Alert>
      ) : null}

      <section className="grid gap-4 sm:grid-cols-2 xl:grid-cols-4">
        <Card>
          <CardHeader>
            <CardDescription>Stato servizio</CardDescription>
            <CardTitle>API</CardTitle>
          </CardHeader>
          <CardContent>
            {health.isLoading ? (
              <Skeleton className="h-7 w-32" />
            ) : (
              <div className="flex items-center gap-2">
                <Badge className="border-emerald-300 bg-emerald-100 text-emerald-800">
                  {health.data?.status ?? 'unknown'}
                </Badge>
                <Badge className="border-zinc-300 bg-zinc-100 text-zinc-700">
                  watcher {health.data?.watcher_enabled ? 'on' : 'off'}
                </Badge>
                <span className="text-muted-foreground text-sm">
                  v{health.data?.version ?? '-'}
                </span>
              </div>
            )}
          </CardContent>
        </Card>

        <Card>
          <CardHeader>
            <CardDescription>Storico run</CardDescription>
            <CardTitle>Win rate globale</CardTitle>
          </CardHeader>
          <CardContent>
            {stats.isLoading ? (
              <Skeleton className="h-7 w-28" />
            ) : (
              <div className="space-y-1">
                <p className="text-2xl font-semibold text-zinc-900">
                  {stats.data ? asPercent(stats.data.win_rate) : '--'}
                </p>
                <p className="text-muted-foreground text-sm">
                  {stats.data?.wins ?? 0} vittorie su {stats.data?.total_runs ?? 0} run
                </p>
              </div>
            )}
          </CardContent>
        </Card>

        <Card>
          <CardHeader>
            <CardDescription>Confidence modello</CardDescription>
            <CardTitle>Affidabilita</CardTitle>
          </CardHeader>
          <CardContent>
            {recommendation.isLoading ? (
              <Skeleton className="h-7 w-24" />
            ) : (
              <p className="text-2xl font-semibold text-zinc-900">
                {recommendation.data ? asPercent(recommendation.data.confidence) : '--'}
              </p>
            )}
          </CardContent>
        </Card>

        <Card>
          <CardHeader>
            <CardDescription>Input live</CardDescription>
            <CardTitle>Sorgente consigli</CardTitle>
          </CardHeader>
          <CardContent>
            {liveContext.isLoading || ingestStatus.isLoading ? (
              <Skeleton className="h-7 w-36" />
            ) : (
              <div className="space-y-1">
                <p className="text-2xl font-semibold text-zinc-900">
                  {useLiveInput ? 'live' : 'manuale'}
                </p>
                <p className="text-muted-foreground text-sm">
                  {liveContext.data?.available
                    ? `run ${liveContext.data.run_id ?? '-'} • sync ${liveUpdatedAt}`
                    : 'nessun contesto live disponibile'}
                </p>
                <p className="text-muted-foreground text-xs">
                  ultimo ingest:{' '}
                  {ingestStatus.data?.last_event_at
                    ? new Date(ingestStatus.data.last_event_at).toLocaleString('it-IT')
                    : '-'}
                </p>
              </div>
            )}
          </CardContent>
        </Card>
      </section>

      <Card className="border-zinc-300/90 bg-zinc-50/70">
        <CardHeader>
          <CardDescription>Carte offerte (input dinamico)</CardDescription>
          <CardTitle>Raccomandazione corrente</CardTitle>
        </CardHeader>
        <CardContent className="space-y-4">
          <div className="flex items-center justify-between gap-3 rounded-md border border-zinc-300 bg-white px-3 py-2">
            <div>
              <p className="text-sm font-medium text-zinc-800">Usa contesto live</p>
              <p className="text-xs text-zinc-500">
                Quando attivo, carte e contesto arrivano da `GET /live/context`.
              </p>
            </div>
            <label className="inline-flex cursor-pointer items-center gap-2 text-sm text-zinc-700">
              <input
                type="checkbox"
                checked={useLiveInput}
                onChange={(event) => setUseLiveInput(event.target.checked)}
              />
              {useLiveInput ? 'live' : 'manuale'}
            </label>
          </div>

          {useLiveInput && !liveIsUsable ? (
            <Alert className="border-amber-300 bg-amber-50/80">
              <AlertTitle>Live non disponibile</AlertTitle>
              <AlertDescription>
                Nessuna scelta carta trovata nel DB: usa temporaneamente l'override manuale.
              </AlertDescription>
            </Alert>
          ) : null}

          <div className="grid gap-3 sm:grid-cols-3">
            <div className="space-y-2">
              <label
                htmlFor="context-character"
                className="text-xs font-semibold tracking-[0.12em] text-zinc-500 uppercase"
              >
                Character
              </label>
              <input
                id="context-character"
                type="text"
                className="w-full rounded-md border border-zinc-300 bg-white px-3 py-2 text-sm text-zinc-900 shadow-xs outline-none transition focus:border-zinc-500"
                placeholder="IRONCLAD"
                value={characterInput}
                onChange={(event) => setCharacterInput(event.target.value)}
                disabled={useLiveInput && liveIsUsable}
              />
            </div>
            <div className="space-y-2">
              <label
                htmlFor="context-ascension"
                className="text-xs font-semibold tracking-[0.12em] text-zinc-500 uppercase"
              >
                Ascension
              </label>
              <input
                id="context-ascension"
                type="number"
                min={0}
                className="w-full rounded-md border border-zinc-300 bg-white px-3 py-2 text-sm text-zinc-900 shadow-xs outline-none transition focus:border-zinc-500"
                value={ascensionInput}
                onChange={(event) => setAscensionInput(Number(event.target.value || 0))}
                disabled={useLiveInput && liveIsUsable}
              />
            </div>
            <div className="space-y-2">
              <label
                htmlFor="context-floor"
                className="text-xs font-semibold tracking-[0.12em] text-zinc-500 uppercase"
              >
                Floor
              </label>
              <input
                id="context-floor"
                type="number"
                min={0}
                className="w-full rounded-md border border-zinc-300 bg-white px-3 py-2 text-sm text-zinc-900 shadow-xs outline-none transition focus:border-zinc-500"
                value={floorInput}
                onChange={(event) => setFloorInput(Number(event.target.value || 0))}
                disabled={useLiveInput && liveIsUsable}
              />
            </div>
          </div>

          <div className="space-y-2">
            <label
              htmlFor="offered-cards"
              className="text-xs font-semibold tracking-[0.12em] text-zinc-500 uppercase"
            >
              Inserisci carte separate da virgola
            </label>
            <input
              id="offered-cards"
              type="text"
              className="w-full rounded-md border border-zinc-300 bg-white px-3 py-2 text-sm text-zinc-900 shadow-xs outline-none transition focus:border-zinc-500"
              placeholder="CARD.BASH, CARD.CLOTHESLINE, CARD.OFF_BALANCE"
              value={cardsInput}
              onChange={(event) => setCardsInput(event.target.value)}
              disabled={useLiveInput && liveIsUsable}
            />
          </div>

          <div className="flex flex-wrap gap-2">
            {activeCards.map((card) => (
              <Badge key={card} className="border-zinc-300 bg-white text-zinc-700">
                {card}
              </Badge>
            ))}
            {activeCards.length === 0 ? (
              <p className="text-sm text-zinc-500">
                Aggiungi almeno una carta per ottenere un suggerimento.
              </p>
            ) : null}
          </div>

          {activeCards.length === 0 ? (
            <div className="rounded-lg border border-zinc-300 bg-white p-4">
              <p className="text-sm text-zinc-500">Best pick</p>
              <p className="mt-1 text-xl font-semibold text-zinc-900">N/A</p>
              <p className="mt-2 text-sm text-zinc-600">
                Inserisci un set valido di carte offerte.
              </p>
            </div>
          ) : recommendation.isLoading ? (
            <Skeleton className="h-20 w-full" />
          ) : (
            <div className="rounded-lg border border-zinc-300 bg-white p-4">
              <p className="text-sm text-zinc-500">Best pick</p>
              <p className="mt-1 text-xl font-semibold text-zinc-900">
                {recommendation.data?.best_pick ?? 'N/A'}
              </p>
              <div className="mt-3 flex flex-wrap gap-2">
                <Badge className="border-zinc-300 bg-zinc-100 text-zinc-800">
                  sample {recommendation.data?.sample_size ?? 0}
                </Badge>
                <Badge className="border-zinc-300 bg-zinc-100 text-zinc-800">
                  scope {recommendation.data?.scope ?? 'global'}
                </Badge>
                {recommendation.data?.fallback_used ? (
                  <Badge className="border-amber-300 bg-amber-100 text-amber-800">fallback</Badge>
                ) : null}
                <Badge
                  className={
                    recommendationReason === 'low_sample_contextual' ||
                    recommendationReason === 'low_sample_global' ||
                    recommendationReason === 'fallback_global_no_context' ||
                    recommendationReason === 'no_history_global'
                      ? 'border-amber-300 bg-amber-100 text-amber-800'
                      : 'border-emerald-300 bg-emerald-100 text-emerald-800'
                  }
                >
                  {recommendationReason ?? 'ok_global'}
                </Badge>
              </div>
              <p className="mt-2 text-sm text-zinc-600">
                Win rate boost stimato:{' '}
                <span className="font-medium text-emerald-700">
                  {recommendation.data ? asPercent(recommendation.data.win_rate_boost) : '--'}
                </span>
              </p>
              <p className="mt-1 text-sm text-zinc-600">
                Carta: {recommendation.data ? asPercent(recommendation.data.card_win_rate) : '--'} |
                Globale:{' '}
                {recommendation.data ? asPercent(recommendation.data.global_win_rate) : '--'}
              </p>
              <p className="mt-2 text-sm text-zinc-500">{reasonLabel}</p>
              <p className="mt-1 text-xs text-zinc-500">
                Filtri applicati:{' '}
                {recommendation.data?.applied_filters.length
                  ? recommendation.data.applied_filters.join(', ')
                  : 'nessuno'}
              </p>
            </div>
          )}

          {activeCards.length > 0 ? (
            <div className="rounded-lg border border-zinc-300 bg-zinc-50 p-4">
              <p className="text-sm font-medium text-zinc-700">Dettaglio carte offerte</p>
              {cardInsights.isLoading ? (
                <Skeleton className="mt-3 h-16 w-full" />
              ) : (
                <div className="mt-3 space-y-2">
                  {cardInsights.data?.insights.map((item) => (
                    <div
                      key={item.card}
                      className="flex flex-wrap items-center justify-between gap-2 rounded-md border border-zinc-200 bg-white px-3 py-2"
                    >
                      <p className="text-sm font-medium text-zinc-800">{item.card}</p>
                      <p className="text-xs text-zinc-600">
                        sample {item.sample_size} | wr {asPercent(item.card_win_rate)} | delta{' '}
                        {asPercent(item.win_rate_boost)}
                      </p>
                    </div>
                  ))}
                </div>
              )}
            </div>
          ) : null}

          <div className="rounded-lg border border-zinc-300 bg-zinc-50 p-4">
            <p className="text-sm font-medium text-zinc-700">Diagnostica ingest recente</p>
            {ingestStatus.isLoading ? (
              <Skeleton className="mt-3 h-14 w-full" />
            ) : ingestStatus.data?.recent_issues.length ? (
              <div className="mt-3 space-y-2">
                {ingestStatus.data.recent_issues.map((issue) => (
                  <div
                    key={`${issue.timestamp}-${issue.file_path}`}
                    className="rounded-md border border-amber-200 bg-amber-50 px-3 py-2"
                  >
                    <p className="text-xs font-semibold text-amber-900">
                      {issue.kind} - {issue.file_path}
                    </p>
                    <p className="mt-1 text-xs text-amber-800">{issue.message}</p>
                    <p className="mt-1 text-[11px] text-amber-700">{issue.timestamp}</p>
                  </div>
                ))}
              </div>
            ) : (
              <p className="mt-2 text-sm text-zinc-500">Nessun errore ingest recente.</p>
            )}
          </div>
        </CardContent>
      </Card>

      <Card className="border-zinc-300/90 bg-zinc-50/70">
        <CardHeader>
          <CardDescription>Run storiche indicizzate</CardDescription>
          <CardTitle>Run History Explorer</CardTitle>
        </CardHeader>
        <CardContent className="space-y-4">
          <div className="grid gap-3 sm:grid-cols-2 lg:grid-cols-5">
            <div className="space-y-2">
              <label
                htmlFor="runs-query"
                className="text-xs font-semibold tracking-[0.12em] text-zinc-500 uppercase"
              >
                Ricerca
              </label>
              <input
                id="runs-query"
                type="text"
                className="w-full rounded-md border border-zinc-300 bg-white px-3 py-2 text-sm text-zinc-900 shadow-xs outline-none transition focus:border-zinc-500"
                placeholder="run id, character, seed"
                value={runsQueryFilter}
                onChange={(event) => {
                  setRunsPage(1)
                  setRunsQueryFilter(event.target.value)
                }}
              />
            </div>
            <div className="space-y-2">
              <label
                htmlFor="runs-character"
                className="text-xs font-semibold tracking-[0.12em] text-zinc-500 uppercase"
              >
                Character
              </label>
              <input
                id="runs-character"
                type="text"
                className="w-full rounded-md border border-zinc-300 bg-white px-3 py-2 text-sm text-zinc-900 shadow-xs outline-none transition focus:border-zinc-500"
                placeholder="IRONCLAD"
                value={runsCharacterFilter}
                onChange={(event) => {
                  setRunsPage(1)
                  setRunsCharacterFilter(event.target.value)
                }}
              />
            </div>
            <div className="space-y-2">
              <label
                htmlFor="runs-ascension"
                className="text-xs font-semibold tracking-[0.12em] text-zinc-500 uppercase"
              >
                Ascension
              </label>
              <input
                id="runs-ascension"
                type="number"
                min={0}
                className="w-full rounded-md border border-zinc-300 bg-white px-3 py-2 text-sm text-zinc-900 shadow-xs outline-none transition focus:border-zinc-500"
                value={runsAscensionFilter}
                onChange={(event) => {
                  setRunsPage(1)
                  setRunsAscensionFilter(event.target.value)
                }}
              />
            </div>
            <div className="space-y-2">
              <label
                htmlFor="runs-win"
                className="text-xs font-semibold tracking-[0.12em] text-zinc-500 uppercase"
              >
                Esito
              </label>
              <select
                id="runs-win"
                className="w-full rounded-md border border-zinc-300 bg-white px-3 py-2 text-sm text-zinc-900 shadow-xs outline-none transition focus:border-zinc-500"
                value={runsWinFilter}
                onChange={(event) => {
                  setRunsPage(1)
                  setRunsWinFilter(event.target.value as 'all' | 'wins' | 'losses')
                }}
              >
                <option value="all">Tutte</option>
                <option value="wins">Solo vittorie</option>
                <option value="losses">Solo sconfitte</option>
              </select>
            </div>
            <div className="space-y-2">
              <label
                htmlFor="runs-size"
                className="text-xs font-semibold tracking-[0.12em] text-zinc-500 uppercase"
              >
                Page size
              </label>
              <select
                id="runs-size"
                className="w-full rounded-md border border-zinc-300 bg-white px-3 py-2 text-sm text-zinc-900 shadow-xs outline-none transition focus:border-zinc-500"
                value={runsPageSize}
                onChange={(event) => {
                  setRunsPage(1)
                  setRunsPageSize(Number(event.target.value))
                }}
              >
                <option value={10}>10</option>
                <option value={20}>20</option>
                <option value={50}>50</option>
              </select>
            </div>
          </div>

          <div className="rounded-md border border-zinc-300 bg-white">
            <div className="grid grid-cols-5 gap-2 border-b border-zinc-200 px-3 py-2 text-xs font-semibold tracking-[0.1em] text-zinc-500 uppercase">
              <span>Run</span>
              <span>Character</span>
              <span>Asc</span>
              <span>Outcome</span>
              <span>Timestamp</span>
            </div>
            {runs.isLoading ? (
              <div className="space-y-2 p-3">
                <Skeleton className="h-8 w-full" />
                <Skeleton className="h-8 w-full" />
              </div>
            ) : runItems.length === 0 ? (
              <p className="p-3 text-sm text-zinc-500">
                Nessuna run trovata con i filtri correnti.
              </p>
            ) : (
              <div className="max-h-64 overflow-y-auto">
                {runItems.map((item) => (
                  <button
                    key={item.run_id}
                    type="button"
                    onClick={() => setSelectedRunId(item.run_id)}
                    className={`grid w-full grid-cols-5 gap-2 border-b border-zinc-100 px-3 py-2 text-left text-sm transition hover:bg-zinc-50 ${
                      selectedRunId === item.run_id ? 'bg-amber-50/60' : 'bg-white'
                    }`}
                  >
                    <span className="truncate text-zinc-900">{item.run_id}</span>
                    <span className="truncate text-zinc-700">{item.character ?? '-'}</span>
                    <span className="text-zinc-700">{item.ascension ?? '-'}</span>
                    <span>
                      <Badge
                        className={
                          item.win
                            ? 'border-emerald-300 bg-emerald-100 text-emerald-800'
                            : 'border-zinc-300 bg-zinc-100 text-zinc-700'
                        }
                      >
                        {item.win ? 'win' : 'loss'}
                      </Badge>
                    </span>
                    <span className="truncate text-zinc-600">
                      {formatIsoDate(item.raw_timestamp ?? item.imported_at)}
                    </span>
                  </button>
                ))}
              </div>
            )}
          </div>

          <div className="flex items-center justify-between gap-3">
            <p className="text-xs text-zinc-500">
              pagina {runs.data?.page ?? runsPage} di {runs.data?.total_pages ?? 1} • totale run{' '}
              {runs.data?.total ?? 0}
            </p>
            <div className="flex items-center gap-2">
              <button
                type="button"
                className="rounded-md border border-zinc-300 bg-white px-3 py-1 text-sm text-zinc-700 disabled:opacity-50"
                disabled={(runs.data?.page ?? runsPage) <= 1}
                onClick={() => setRunsPage((prev) => Math.max(1, prev - 1))}
              >
                Prev
              </button>
              <button
                type="button"
                className="rounded-md border border-zinc-300 bg-white px-3 py-1 text-sm text-zinc-700 disabled:opacity-50"
                disabled={(runs.data?.page ?? runsPage) >= (runs.data?.total_pages ?? 1)}
                onClick={() => setRunsPage((prev) => prev + 1)}
              >
                Next
              </button>
            </div>
          </div>

          <div className="grid gap-4 lg:grid-cols-2">
            <div className="rounded-lg border border-zinc-300 bg-white p-4">
              <p className="text-sm font-medium text-zinc-700">Dettaglio run</p>
              {!selectedRunId ? (
                <p className="mt-2 text-sm text-zinc-500">Seleziona una run dall'elenco.</p>
              ) : runDetail.isLoading ? (
                <Skeleton className="mt-3 h-24 w-full" />
              ) : selectedRun ? (
                <div className="mt-3 space-y-2 text-sm text-zinc-700">
                  <p>
                    <span className="font-medium text-zinc-900">run id:</span> {selectedRun.run_id}
                  </p>
                  <p>
                    <span className="font-medium text-zinc-900">character:</span>{' '}
                    {selectedRun.character ?? '-'}
                  </p>
                  <p>
                    <span className="font-medium text-zinc-900">ascension:</span>{' '}
                    {selectedRun.ascension ?? '-'}
                  </p>
                  <p>
                    <span className="font-medium text-zinc-900">outcome:</span>{' '}
                    {selectedRun.win ? 'win' : 'loss'}
                  </p>
                  <p>
                    <span className="font-medium text-zinc-900">seed:</span>{' '}
                    {selectedRun.seed ?? '-'}
                  </p>
                  <p>
                    <span className="font-medium text-zinc-900">run timestamp:</span>{' '}
                    {formatIsoDate(selectedRun.raw_timestamp)}
                  </p>
                  <p>
                    <span className="font-medium text-zinc-900">card choices:</span>{' '}
                    {selectedRun.card_choices.length}
                  </p>
                  <p>
                    <span className="font-medium text-zinc-900">relic events:</span>{' '}
                    {selectedRun.relic_history.length}
                  </p>
                  <p>
                    <span className="font-medium text-zinc-900">imported:</span>{' '}
                    {formatIsoDate(selectedRun.imported_at)}
                  </p>
                  <p className="break-all text-xs text-zinc-500">
                    source: {selectedRun.source_file ?? '-'}
                  </p>
                  <div className="grid gap-2 pt-1 sm:grid-cols-3">
                    <div className="rounded-md border border-zinc-200 bg-zinc-50 px-2 py-1">
                      <div className="flex items-center justify-between gap-2">
                        <p className="text-[11px] font-semibold tracking-[0.08em] text-zinc-500 uppercase">
                          Score
                        </p>
                        <Badge
                          className={`text-[10px] uppercase ${metricAvailabilityStyle(selectedRunStats?.score ?? null)}`}
                        >
                          {metricAvailabilityLabel(selectedRunStats?.score ?? null)}
                        </Badge>
                      </div>
                      <p className="text-sm font-medium text-zinc-800">
                        {asNumberLabel(selectedRunStats?.score ?? null)}
                      </p>
                      <p className="text-[11px] text-zinc-500" title="Campo raw usato: score">
                        source: score
                      </p>
                    </div>
                    <div className="rounded-md border border-zinc-200 bg-zinc-50 px-2 py-1">
                      <div className="flex items-center justify-between gap-2">
                        <p className="text-[11px] font-semibold tracking-[0.08em] text-zinc-500 uppercase">
                          Floor reached
                        </p>
                        <Badge
                          className={`text-[10px] uppercase ${metricAvailabilityStyle(selectedRunStats?.floorReached ?? null)}`}
                        >
                          {metricAvailabilityLabel(selectedRunStats?.floorReached ?? null)}
                        </Badge>
                      </div>
                      <p className="text-sm font-medium text-zinc-800">
                        {asNumberLabel(selectedRunStats?.floorReached ?? null)}
                      </p>
                      <p
                        className="text-[11px] text-zinc-500"
                        title="Campo raw usato: floor_reached"
                      >
                        source: floor_reached
                      </p>
                    </div>
                    <div className="rounded-md border border-zinc-200 bg-zinc-50 px-2 py-1">
                      <div className="flex items-center justify-between gap-2">
                        <p className="text-[11px] font-semibold tracking-[0.08em] text-zinc-500 uppercase">
                          Gold finale
                        </p>
                        <Badge
                          className={`text-[10px] uppercase ${metricAvailabilityStyle(selectedRunStats?.finalGold ?? null)}`}
                        >
                          {metricAvailabilityLabel(selectedRunStats?.finalGold ?? null)}
                        </Badge>
                      </div>
                      <p className="text-sm font-medium text-zinc-800">
                        {asNumberLabel(selectedRunStats?.finalGold ?? null)}
                      </p>
                      <p
                        className="text-[11px] text-zinc-500"
                        title="Campo raw usato: gold (fallback: gold_per_floor ultimo valore)"
                      >
                        source: gold {'->'} gold_per_floor[-1]
                      </p>
                    </div>
                  </div>
                  {!hasQuickStats ? (
                    <p className="text-xs text-zinc-500">
                      Quick stats non disponibili in questo payload run.
                    </p>
                  ) : null}
                  <div className="rounded-md border border-zinc-200 bg-zinc-50 p-3">
                    <div className="flex items-center justify-between gap-2">
                      <p className="text-[11px] font-semibold tracking-[0.08em] text-zinc-500 uppercase">
                        Data completeness
                      </p>
                      {completenessSeverity ? (
                        <Badge
                          className={`text-[10px] uppercase ${severityBadgeClass(completenessSeverity)}`}
                        >
                          {completenessSeverity} impact
                        </Badge>
                      ) : null}
                    </div>
                    {runCompleteness.isLoading ? (
                      <Skeleton className="mt-2 h-5 w-48" />
                    ) : runCompleteness.isError ? (
                      <p className="mt-1 text-xs text-zinc-500">
                        Impossibile caricare la completeness da API.
                      </p>
                    ) : selectedRunCompleteness ? (
                      <>
                        <p className="mt-1 text-sm text-zinc-800">
                          campi chiave disponibili {selectedRunCompleteness.available} su{' '}
                          {selectedRunCompleteness.total}
                        </p>
                        {selectedRunCompleteness.missing.length ? (
                          <p className="mt-1 text-xs text-zinc-500">
                            mancanti: {selectedRunCompleteness.missing.join(', ')}
                          </p>
                        ) : (
                          <p className="mt-1 text-xs text-zinc-500">
                            Tutti i campi chiave sono presenti.
                          </p>
                        )}
                      </>
                    ) : (
                      <p className="mt-1 text-xs text-zinc-500">
                        Nessun dato completeness disponibile.
                      </p>
                    )}
                  </div>
                </div>
              ) : (
                <p className="mt-2 text-sm text-zinc-500">Run non trovata.</p>
              )}
            </div>

            <div className="rounded-lg border border-zinc-300 bg-white p-4">
              <p className="text-sm font-medium text-zinc-700">Timeline floor-by-floor</p>
              {!selectedRunId ? (
                <p className="mt-2 text-sm text-zinc-500">Seleziona una run dall'elenco.</p>
              ) : runTimeline.isLoading ? (
                <Skeleton className="mt-3 h-24 w-full" />
              ) : timelineEvents.length ? (
                <div className="mt-3 space-y-3">
                  <div className="grid gap-2 sm:grid-cols-2">
                    <div className="space-y-1">
                      <label
                        htmlFor="timeline-kind"
                        className="text-[11px] font-semibold tracking-[0.12em] text-zinc-500 uppercase"
                      >
                        Tipo evento
                      </label>
                      <select
                        id="timeline-kind"
                        className="w-full rounded-md border border-zinc-300 bg-white px-3 py-2 text-sm text-zinc-900 shadow-xs outline-none transition focus:border-zinc-500"
                        value={timelineKindFilter}
                        onChange={(event) => setTimelineKindFilter(event.target.value)}
                      >
                        {timelineKinds.map((kind) => (
                          <option key={kind} value={kind}>
                            {TIMELINE_KIND_LABELS[kind] ?? kind.replaceAll('_', ' ')}
                          </option>
                        ))}
                      </select>
                    </div>
                    <div className="space-y-1">
                      <label
                        htmlFor="timeline-query"
                        className="text-[11px] font-semibold tracking-[0.12em] text-zinc-500 uppercase"
                      >
                        Cerca evento
                      </label>
                      <input
                        id="timeline-query"
                        type="text"
                        className="w-full rounded-md border border-zinc-300 bg-white px-3 py-2 text-sm text-zinc-900 shadow-xs outline-none transition focus:border-zinc-500"
                        placeholder="es. remove, smith, boss"
                        value={timelineQueryFilter}
                        onChange={(event) => setTimelineQueryFilter(event.target.value)}
                      />
                    </div>
                  </div>

                  <label className="inline-flex items-center gap-2 text-xs text-zinc-600">
                    <input
                      type="checkbox"
                      checked={showDecisionOnly}
                      onChange={(event) => setShowDecisionOnly(event.target.checked)}
                    />
                    Solo eventi decisionali
                  </label>

                  <p className="text-xs text-zinc-500">
                    eventi mostrati {filteredTimelineEvents.length} su {timelineEvents.length}
                  </p>

                  {groupedTimelineEvents.length ? (
                    <div className="max-h-72 space-y-3 overflow-y-auto">
                      {groupedTimelineEvents.map((group) => (
                        <div key={group.floor} className="space-y-2">
                          <p className="text-xs font-semibold tracking-[0.08em] text-zinc-500 uppercase">
                            {group.floor >= 900 ? 'Boss chest' : `Floor ${group.floor}`}
                          </p>
                          {group.events.map((event) => (
                            <div
                              key={eventStableKey(event)}
                              className="rounded-md border border-zinc-200 bg-zinc-50 px-3 py-2"
                            >
                              <div className="flex flex-wrap items-center gap-2">
                                <p className="text-xs font-semibold text-zinc-700 uppercase">
                                  {formatTimelineFloor(event)}
                                </p>
                                <Badge
                                  className={`text-[10px] uppercase ${TIMELINE_KIND_STYLES[event.kind] ?? 'border-zinc-300 bg-zinc-100 text-zinc-700'}`}
                                >
                                  {event.kind.replaceAll('_', ' ')}
                                </Badge>
                              </div>
                              <p className="mt-1 text-sm text-zinc-800">{event.summary}</p>
                              {eventMeta(event) ? (
                                <p className="mt-1 text-xs text-zinc-600">{eventMeta(event)}</p>
                              ) : null}
                            </div>
                          ))}
                        </div>
                      ))}
                    </div>
                  ) : (
                    <p className="text-sm text-zinc-500">
                      Nessun evento con i filtri timeline correnti.
                    </p>
                  )}
                </div>
              ) : (
                <p className="mt-2 text-sm text-zinc-500">Nessun evento timeline disponibile.</p>
              )}
            </div>
          </div>

          <div className="rounded-lg border border-zinc-300 bg-white p-4">
            <div className="flex flex-wrap items-center justify-between gap-3">
              <p className="text-sm font-medium text-zinc-700">Raw JSON completo</p>
              {selectedRun ? (
                <button
                  type="button"
                  className="rounded-md border border-zinc-300 bg-zinc-100 px-3 py-1 text-xs font-medium text-zinc-700 transition hover:bg-zinc-200"
                  onClick={() => downloadRunJson(selectedRun.run_id, selectedRun.raw_payload)}
                >
                  Export JSON run
                </button>
              ) : null}
            </div>
            {!selectedRunId ? (
              <p className="mt-2 text-sm text-zinc-500">Seleziona una run dall'elenco.</p>
            ) : runDetail.isLoading ? (
              <Skeleton className="mt-3 h-32 w-full" />
            ) : selectedRun ? (
              <pre className="mt-3 max-h-72 overflow-auto rounded-md border border-zinc-200 bg-zinc-50 p-3 text-xs text-zinc-800">
                {JSON.stringify(selectedRun.raw_payload, null, 2)}
              </pre>
            ) : (
              <p className="mt-2 text-sm text-zinc-500">Run non trovata.</p>
            )}
          </div>
        </CardContent>
      </Card>
    </main>
  )
}
