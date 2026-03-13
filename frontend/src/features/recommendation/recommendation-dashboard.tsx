import { Alert, AlertDescription, AlertTitle } from '@/components/ui/alert'
import { Badge } from '@/components/ui/badge'
import {
  Card,
  CardContent,
  CardDescription,
  CardHeader,
  CardTitle,
} from '@/components/ui/card'
import { Skeleton } from '@/components/ui/skeleton'
import { useMemo, useState } from 'react'

import {
  DEFAULT_OFFERED,
  useHealth,
  useIngestStatus,
  useRecommendation,
  useStats,
} from './hooks'

function asPercent(value: number): string {
  return `${(value * 100).toFixed(1)}%`
}

function parseCardsInput(value: string): string[] {
  return value
    .split(',')
    .map((part) => part.trim())
    .filter(Boolean)
}

export function RecommendationDashboard() {
  const [cardsInput, setCardsInput] = useState(DEFAULT_OFFERED.join(', '))
  const offeredCards = useMemo(() => parseCardsInput(cardsInput), [cardsInput])

  const health = useHealth()
  const stats = useStats()
  const recommendation = useRecommendation(offeredCards)
  const ingestStatus = useIngestStatus()

  const hasError =
    health.isError ||
    stats.isError ||
    recommendation.isError ||
    ingestStatus.isError

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
                {recommendation.data
                  ? asPercent(recommendation.data.confidence)
                  : '--'}
              </p>
            )}
          </CardContent>
        </Card>

        <Card>
          <CardHeader>
            <CardDescription>Ingestion live</CardDescription>
            <CardTitle>Ultimo import</CardTitle>
          </CardHeader>
          <CardContent>
            {ingestStatus.isLoading ? (
              <Skeleton className="h-7 w-36" />
            ) : (
              <div className="space-y-1">
                <p className="text-2xl font-semibold text-zinc-900">
                  {ingestStatus.data?.updated ?? 0}
                </p>
                <p className="text-muted-foreground text-sm">
                  update, {ingestStatus.data?.imported ?? 0} nuovi,{' '}
                  {ingestStatus.data?.parse_errors ?? 0} errori parse
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
            />
          </div>

          <div className="flex flex-wrap gap-2">
            {offeredCards.map((card) => (
              <Badge key={card} className="border-zinc-300 bg-white text-zinc-700">
                {card}
              </Badge>
            ))}
            {offeredCards.length === 0 ? (
              <p className="text-sm text-zinc-500">Aggiungi almeno una carta per ottenere un suggerimento.</p>
            ) : null}
          </div>

          {offeredCards.length === 0 ? (
            <div className="rounded-lg border border-zinc-300 bg-white p-4">
              <p className="text-sm text-zinc-500">Best pick</p>
              <p className="mt-1 text-xl font-semibold text-zinc-900">N/A</p>
              <p className="mt-2 text-sm text-zinc-600">Inserisci un set valido di carte offerte.</p>
            </div>
          ) : recommendation.isLoading ? (
            <Skeleton className="h-20 w-full" />
          ) : (
            <div className="rounded-lg border border-zinc-300 bg-white p-4">
              <p className="text-sm text-zinc-500">Best pick</p>
              <p className="mt-1 text-xl font-semibold text-zinc-900">
                {recommendation.data?.best_pick ?? 'N/A'}
              </p>
              <p className="mt-2 text-sm text-zinc-600">
                Win rate boost stimato:{' '}
                <span className="font-medium text-emerald-700">
                  {recommendation.data
                    ? asPercent(recommendation.data.win_rate_boost)
                    : '--'}
                </span>
              </p>
            </div>
          )}
        </CardContent>
      </Card>
    </main>
  )
}
