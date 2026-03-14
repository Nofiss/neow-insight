import { Alert, AlertDescription, AlertTitle } from '@/components/ui/alert'
import { Badge } from '@/components/ui/badge'
import { Card, CardContent, CardDescription, CardHeader, CardTitle } from '@/components/ui/card'
import { Skeleton } from '@/components/ui/skeleton'
import {
  DEFAULT_OFFERED,
  useHealth,
  useIngestStatus,
  useLiveContext,
  useRecommendation,
  useStats,
} from '@/features/recommendation/hooks'
import { asPercent, formatUpdatedAt } from '@/features/recommendation/utils'

export function OverviewPage() {
  const health = useHealth()
  const stats = useStats()
  const liveContext = useLiveContext()
  const ingestStatus = useIngestStatus()

  const recommendation = useRecommendation(DEFAULT_OFFERED, {
    character: liveContext.data?.character?.trim().toUpperCase() ?? undefined,
    ascension: liveContext.data?.ascension ?? undefined,
    floor: liveContext.data?.floor ?? undefined,
  })

  const hasError =
    health.isError ||
    stats.isError ||
    recommendation.isError ||
    ingestStatus.isError ||
    liveContext.isError

  return (
    <main className="mx-auto flex w-full max-w-6xl flex-col gap-6 px-4 py-8 sm:px-6 lg:py-10">
      <section className="rounded-2xl border border-zinc-300/80 bg-gradient-to-r from-amber-50 via-orange-50 to-red-50 p-6 shadow-sm">
        <h2 className="text-3xl leading-tight font-semibold text-zinc-900 sm:text-4xl">Overview</h2>
        <p className="mt-2 max-w-2xl text-sm text-zinc-600 sm:text-base">
          Stato API, trend storico e contesto live in una vista rapida.
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
                <span className="text-sm text-zinc-500">v{health.data?.version ?? '-'}</span>
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
                <p className="text-sm text-zinc-500">
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
                  {liveContext.data?.available ? 'live' : 'manuale'}
                </p>
                <p className="text-sm text-zinc-500">
                  {liveContext.data?.available
                    ? `run ${liveContext.data.run_id ?? '-'} - sync ${formatUpdatedAt(liveContext.dataUpdatedAt)}`
                    : 'nessun contesto live disponibile'}
                </p>
                <p className="text-xs text-zinc-500">
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
    </main>
  )
}
