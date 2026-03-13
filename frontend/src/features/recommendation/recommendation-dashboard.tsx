import { useMemo, useState } from 'react'
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
  useStats,
} from './hooks'

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

export function RecommendationDashboard() {
  const [cardsInput, setCardsInput] = useState(DEFAULT_OFFERED.join(', '))
  const [characterInput, setCharacterInput] = useState(DEFAULT_CHARACTER)
  const [ascensionInput, setAscensionInput] = useState(DEFAULT_ASCENSION)
  const [floorInput, setFloorInput] = useState(DEFAULT_FLOOR)
  const [useLiveInput, setUseLiveInput] = useState(true)
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

  const hasError =
    health.isError ||
    stats.isError ||
    recommendation.isError ||
    cardInsights.isError ||
    ingestStatus.isError

  const recommendationReason = recommendation.data?.reason
  const reasonLabel = REASON_LABELS[recommendationReason ?? 'ok_global']
  const liveUpdatedAt = formatUpdatedAt(liveContext.dataUpdatedAt)

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
    </main>
  )
}
