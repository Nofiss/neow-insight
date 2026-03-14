import { useMemo, useState } from 'react'
import { Link, useParams, useSearchParams } from 'react-router-dom'
import { Badge } from '@/components/ui/badge'
import { Card, CardContent, CardDescription, CardHeader, CardTitle } from '@/components/ui/card'
import { Skeleton } from '@/components/ui/skeleton'
import { useRunCompleteness, useRunDetail, useRunTimeline } from '@/features/recommendation/hooks'
import {
  asNumberLabel,
  completenessInferenceBadgeClass,
  completenessInferenceLevel,
  downloadRunJson,
  eventMeta,
  eventSearchBlob,
  eventStableKey,
  formatIsoDate,
  formatTimelineFloor,
  isDecisionEvent,
  metricAvailabilityLabel,
  metricAvailabilityStyle,
  metricSourceLabel,
  metricSourceStyle,
  missingSeverity,
  runQuickStats,
  severityBadgeClass,
  TIMELINE_KIND_LABELS,
  TIMELINE_KIND_STYLES,
} from '@/features/recommendation/utils'

export function RunDetailPage() {
  const { runId } = useParams()
  const [searchParams] = useSearchParams()
  const [timelineKindFilter, setTimelineKindFilter] = useState('all')
  const [timelineQueryFilter, setTimelineQueryFilter] = useState('')
  const [showDecisionOnly, setShowDecisionOnly] = useState(false)

  const decodedRunId = runId ? decodeURIComponent(runId) : null
  const runDetail = useRunDetail(decodedRunId)
  const runTimeline = useRunTimeline(decodedRunId)
  const runCompleteness = useRunCompleteness(decodedRunId)

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
  const completenessInference = selectedRunCompleteness
    ? completenessInferenceLevel(
        selectedRunCompleteness.available_direct,
        selectedRunCompleteness.available_inferred,
      )
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
      if (showDecisionOnly && !isDecisionEvent(event.kind)) {
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
    const groups = new Map<number, typeof timelineEvents>()
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

  const backQuery = searchParams.toString()

  return (
    <main className="mx-auto flex w-full max-w-6xl flex-col gap-6 px-4 py-8 sm:px-6 lg:py-10">
      <nav
        aria-label="Breadcrumb"
        className="flex flex-wrap items-center gap-2 text-xs font-medium tracking-[0.06em] text-zinc-500 uppercase"
      >
        <Link className="text-zinc-600 transition hover:text-zinc-900" to="/overview">
          Overview
        </Link>
        <span>/</span>
        <Link
          className="text-zinc-600 transition hover:text-zinc-900"
          to={backQuery ? `/runs?${backQuery}` : '/runs'}
        >
          Runs
        </Link>
        <span>/</span>
        <span
          aria-current="page"
          className="rounded-full border border-amber-300 bg-amber-100 px-2 py-0.5 text-amber-900"
        >
          {decodedRunId ?? 'Run'}
        </span>
      </nav>

      <section className="rounded-2xl border border-zinc-300/80 bg-gradient-to-r from-rose-50 via-orange-50 to-amber-50 p-6 shadow-sm">
        <div className="flex flex-wrap items-center justify-between gap-3">
          <div>
            <h2 className="text-3xl leading-tight font-semibold text-zinc-900 sm:text-4xl">
              Run Detail
            </h2>
            <p className="mt-2 max-w-2xl text-sm text-zinc-600 sm:text-base">
              Timeline, completezza e payload grezzo della run selezionata.
            </p>
          </div>
          <Link
            to={backQuery ? `/runs?${backQuery}` : '/runs'}
            className="rounded-md border border-zinc-300 bg-white px-3 py-1.5 text-sm text-zinc-700 transition hover:bg-zinc-100"
          >
            Torna alle run
          </Link>
        </div>
      </section>

      <div className="grid gap-4 lg:grid-cols-2">
        <Card className="border-zinc-300/90 bg-zinc-50/70">
          <CardHeader>
            <CardDescription>Dati principali</CardDescription>
            <CardTitle>Dettaglio run</CardTitle>
          </CardHeader>
          <CardContent>
            {!decodedRunId ? (
              <p className="text-sm text-zinc-500">ID run non valido.</p>
            ) : runDetail.isLoading ? (
              <Skeleton className="h-40 w-full" />
            ) : selectedRun ? (
              <div className="space-y-2 text-sm text-zinc-700">
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
                  <span className="font-medium text-zinc-900">seed:</span> {selectedRun.seed ?? '-'}
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
                    <p className="text-[11px] text-zinc-500">source: score</p>
                  </div>

                  <div className="rounded-md border border-zinc-200 bg-zinc-50 px-2 py-1">
                    <div className="flex items-center justify-between gap-2">
                      <p className="text-[11px] font-semibold tracking-[0.08em] text-zinc-500 uppercase">
                        Floor reached
                      </p>
                      <div className="flex items-center gap-1">
                        <Badge
                          className={`text-[10px] uppercase ${metricSourceStyle(selectedRunStats?.floorReachedDerived ?? false)}`}
                        >
                          {metricSourceLabel(selectedRunStats?.floorReachedDerived ?? false)}
                        </Badge>
                        <Badge
                          className={`text-[10px] uppercase ${metricAvailabilityStyle(selectedRunStats?.floorReached ?? null)}`}
                        >
                          {metricAvailabilityLabel(selectedRunStats?.floorReached ?? null)}
                        </Badge>
                      </div>
                    </div>
                    <p className="text-sm font-medium text-zinc-800">
                      {asNumberLabel(selectedRunStats?.floorReached ?? null)}
                    </p>
                    <p className="text-[11px] text-zinc-500">
                      source: {selectedRunStats?.floorReachedSource ?? 'floor_reached'}
                    </p>
                  </div>

                  <div className="rounded-md border border-zinc-200 bg-zinc-50 px-2 py-1">
                    <div className="flex items-center justify-between gap-2">
                      <p className="text-[11px] font-semibold tracking-[0.08em] text-zinc-500 uppercase">
                        Gold finale
                      </p>
                      <div className="flex items-center gap-1">
                        <Badge
                          className={`text-[10px] uppercase ${metricSourceStyle(selectedRunStats?.finalGoldDerived ?? false)}`}
                        >
                          {metricSourceLabel(selectedRunStats?.finalGoldDerived ?? false)}
                        </Badge>
                        <Badge
                          className={`text-[10px] uppercase ${metricAvailabilityStyle(selectedRunStats?.finalGold ?? null)}`}
                        >
                          {metricAvailabilityLabel(selectedRunStats?.finalGold ?? null)}
                        </Badge>
                      </div>
                    </div>
                    <p className="text-sm font-medium text-zinc-800">
                      {asNumberLabel(selectedRunStats?.finalGold ?? null)}
                    </p>
                    <p className="text-[11px] text-zinc-500">
                      source:{' '}
                      {selectedRunStats?.finalGoldSource ??
                        'gold / gold_per_floor[-1] / current_gold'}
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
                      <div className="flex items-center gap-1">
                        {completenessInference ? (
                          <Badge
                            className={`text-[10px] uppercase ${completenessInferenceBadgeClass(completenessInference)}`}
                          >
                            {completenessInference} source
                          </Badge>
                        ) : null}
                        <Badge
                          className={`text-[10px] uppercase ${severityBadgeClass(completenessSeverity)}`}
                        >
                          {completenessSeverity} impact
                        </Badge>
                      </div>
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
                      <p className="mt-1 text-xs text-zinc-500">
                        diretti {selectedRunCompleteness.available_direct} - inferiti{' '}
                        {selectedRunCompleteness.available_inferred}
                      </p>
                      {selectedRunCompleteness.inferred.length ? (
                        <p className="mt-1 text-xs text-zinc-500">
                          inferiti: {selectedRunCompleteness.inferred.join(', ')}
                        </p>
                      ) : null}
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
              <p className="text-sm text-zinc-500">Run non trovata.</p>
            )}
          </CardContent>
        </Card>

        <Card className="border-zinc-300/90 bg-zinc-50/70">
          <CardHeader>
            <CardDescription>Sequenza eventi</CardDescription>
            <CardTitle>Timeline floor-by-floor</CardTitle>
          </CardHeader>
          <CardContent>
            {!decodedRunId ? (
              <p className="text-sm text-zinc-500">ID run non valido.</p>
            ) : runTimeline.isLoading ? (
              <Skeleton className="h-40 w-full" />
            ) : timelineEvents.length ? (
              <div className="space-y-3">
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
                  <div className="max-h-96 space-y-3 overflow-y-auto">
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
              <p className="text-sm text-zinc-500">Nessun evento timeline disponibile.</p>
            )}
          </CardContent>
        </Card>
      </div>

      <Card className="border-zinc-300/90 bg-zinc-50/70">
        <CardHeader>
          <CardDescription>Payload completo</CardDescription>
          <CardTitle>Raw JSON completo</CardTitle>
        </CardHeader>
        <CardContent>
          {selectedRun ? (
            <button
              type="button"
              className="mb-3 rounded-md border border-zinc-300 bg-zinc-100 px-3 py-1 text-xs font-medium text-zinc-700 transition hover:bg-zinc-200"
              onClick={() => downloadRunJson(selectedRun.run_id, selectedRun.raw_payload)}
            >
              Export JSON run
            </button>
          ) : null}
          {!decodedRunId ? (
            <p className="text-sm text-zinc-500">ID run non valido.</p>
          ) : runDetail.isLoading ? (
            <Skeleton className="h-32 w-full" />
          ) : selectedRun ? (
            <pre className="max-h-72 overflow-auto rounded-md border border-zinc-200 bg-zinc-50 p-3 text-xs text-zinc-800">
              {JSON.stringify(selectedRun.raw_payload, null, 2)}
            </pre>
          ) : (
            <p className="text-sm text-zinc-500">Run non trovata.</p>
          )}
        </CardContent>
      </Card>
    </main>
  )
}
