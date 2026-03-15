import { useEffect, useMemo, useState } from 'react'
import { Alert, AlertDescription, AlertTitle } from '@/components/ui/alert'
import { Badge } from '@/components/ui/badge'
import { Card, CardContent, CardDescription, CardHeader, CardTitle } from '@/components/ui/card'
import { Skeleton } from '@/components/ui/skeleton'
import {
  DEFAULT_OFFERED,
  useCardInsights,
  useIngestStatus,
  useLiveContext,
  useRecommendation,
  useRunCharacters,
} from '@/features/recommendation/hooks'
import { asPercent, parseCardsInput, REASON_LABELS } from '@/features/recommendation/utils'

const DEFAULT_CHARACTER = 'IRONCLAD'
const DEFAULT_ASCENSION = 10
const DEFAULT_FLOOR = 1

export function RecommendationPage() {
  const [cardsInput, setCardsInput] = useState(DEFAULT_OFFERED.join(', '))
  const [characterInput, setCharacterInput] = useState(DEFAULT_CHARACTER)
  const [ascensionInput, setAscensionInput] = useState(DEFAULT_ASCENSION)
  const [floorInput, setFloorInput] = useState(DEFAULT_FLOOR)

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
  const runCharacters = useRunCharacters()
  const availableCharacters = runCharacters.data?.items ?? []
  const liveCards = liveContext.data?.offered_cards ?? []
  const liveIsUsable = Boolean(liveContext.data?.available && liveCards.length > 0)

  useEffect(() => {
    if (liveIsUsable) {
      return
    }
    if (availableCharacters.length === 0) {
      return
    }
    if (availableCharacters.includes(characterInput)) {
      return
    }
    const ironcladCharacter = availableCharacters.find((character) => character === 'IRONCLAD')
    setCharacterInput(ironcladCharacter ?? availableCharacters[0])
  }, [availableCharacters, characterInput, liveIsUsable])

  const activeCards = useMemo(() => {
    if (liveIsUsable) {
      return liveCards
    }
    return offeredCards
  }, [liveCards, liveIsUsable, offeredCards])

  const activeRecommendationContext = useMemo(() => {
    if (liveIsUsable) {
      return {
        character: liveContext.data?.character?.trim().toUpperCase() ?? '',
        ascension: Math.max(0, Math.floor(liveContext.data?.ascension ?? 0)),
        floor: Math.max(0, Math.floor(liveContext.data?.floor ?? 0)),
      }
    }
    return manualRecommendationContext
  }, [liveContext.data, liveIsUsable, manualRecommendationContext])

  const recommendation = useRecommendation(activeCards, activeRecommendationContext)
  const cardInsights = useCardInsights(activeCards)
  const ingestStatus = useIngestStatus()
  const recommendationSource = liveIsUsable ? 'live' : 'fallback'
  const liveRunId = liveContext.data?.run_id
  const liveCharacter = liveContext.data?.character
  const liveAscension = liveContext.data?.ascension
  const liveFloor = liveContext.data?.floor
  const recommendationReason = recommendation.data?.reason
  const reasonLabel = REASON_LABELS[recommendationReason ?? 'ok_global']

  return (
    <main className="mx-auto flex w-full max-w-6xl flex-col gap-6 px-4 py-8 sm:px-6 lg:py-10">
      <section className="rounded-2xl border border-zinc-300/80 bg-gradient-to-r from-sky-50 via-cyan-50 to-teal-50 p-6 shadow-sm">
        <h2 className="text-3xl leading-tight font-semibold text-zinc-900 sm:text-4xl">
          Recommendation
        </h2>
        <p className="mt-2 max-w-2xl text-sm text-zinc-600 sm:text-base">
          Flusso live-first da current run con best pick statistica e proposta LLM affiancata.
        </p>
      </section>

      <Card className="border-zinc-300/90 bg-zinc-50/70">
        <CardHeader>
          <CardDescription>Carte offerte dalla run live corrente</CardDescription>
          <CardTitle>Raccomandazione corrente</CardTitle>
        </CardHeader>
        <CardContent className="space-y-4">
          <div className="rounded-md border border-zinc-300 bg-white px-3 py-2">
            <p className="text-sm font-medium text-zinc-800">Contesto attivo</p>
            <p className="mt-1 text-xs text-zinc-500">
              Modalita live-first: carte e contesto arrivano da `GET /live/context`.
            </p>
          </div>

          {!liveIsUsable ? (
            <Alert className="border-amber-300 bg-amber-50/80">
              <AlertTitle>Live non disponibile</AlertTitle>
              <AlertDescription>
                Nessuna scelta carta trovata nel DB: viene usato fallback locale temporaneo.
              </AlertDescription>
            </Alert>
          ) : null}

          <div className="rounded-lg border border-zinc-300 bg-zinc-50 p-4">
            <p className="text-sm font-medium text-zinc-700">Live run</p>
            {liveContext.isLoading ? (
              <Skeleton className="mt-3 h-14 w-full" />
            ) : liveContext.data?.available ? (
              <div className="mt-3 flex flex-wrap items-center gap-2">
                <Badge className="border-sky-300 bg-sky-100 text-sky-900">
                  run {liveRunId ?? 'N/A'}
                </Badge>
                <Badge className="border-zinc-300 bg-white text-zinc-700">
                  {liveCharacter ?? 'N/A'} A{liveAscension ?? 0} F{liveFloor ?? 0}
                </Badge>
                <Badge className="border-zinc-300 bg-white text-zinc-700">
                  source {recommendationSource}
                </Badge>
              </div>
            ) : (
              <p className="mt-2 text-sm text-zinc-500">Nessuna run live disponibile.</p>
            )}
          </div>

          <div className="grid gap-3 sm:grid-cols-3">
            <div className="space-y-2">
              <label
                htmlFor="context-character"
                className="text-xs font-semibold tracking-[0.12em] text-zinc-500 uppercase"
              >
                Character
              </label>
              {availableCharacters.length > 0 ? (
                <select
                  id="context-character"
                  className="w-full rounded-md border border-zinc-300 bg-white px-3 py-2 text-sm text-zinc-900 shadow-xs outline-none transition focus:border-zinc-500"
                  value={characterInput}
                  onChange={(event) => setCharacterInput(event.target.value)}
                  disabled={liveIsUsable}
                >
                  {availableCharacters.map((character) => (
                    <option key={character} value={character}>
                      {character}
                    </option>
                  ))}
                </select>
              ) : (
                <input
                  id="context-character"
                  type="text"
                  className="w-full rounded-md border border-zinc-300 bg-white px-3 py-2 text-sm text-zinc-900 shadow-xs outline-none transition focus:border-zinc-500"
                  placeholder="IRONCLAD"
                  value={characterInput}
                  onChange={(event) => setCharacterInput(event.target.value)}
                  disabled={liveIsUsable}
                />
              )}
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
                disabled={liveIsUsable}
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
                disabled={liveIsUsable}
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
              disabled={liveIsUsable}
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
                <Badge className="border-sky-300 bg-sky-100 text-sky-900">
                  source {recommendationSource}
                </Badge>
                {recommendationSource === 'live' ? (
                  <Badge className="border-sky-300 bg-sky-100 text-sky-900">
                    run {liveRunId ?? 'N/A'}
                  </Badge>
                ) : null}
                <Badge className="border-zinc-300 bg-zinc-100 text-zinc-800">
                  mode {recommendation.data?.source ?? 'statistical'}
                </Badge>
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
              <div className="mt-3 rounded-md border border-zinc-200 bg-zinc-50 px-3 py-2">
                <p className="text-xs font-semibold tracking-[0.08em] text-zinc-500 uppercase">
                  Proposta LLM (affiancata)
                </p>
                <p className="mt-1 text-sm text-zinc-800">
                  Pick:{' '}
                  <span className="font-medium">{recommendation.data?.llm_pick ?? 'N/A'}</span>
                </p>
                <p className="mt-1 text-xs text-zinc-600">
                  {recommendation.data?.llm_rationale ??
                    'LLM non disponibile: fallback statistico.'}
                </p>
                {recommendation.data?.llm_strategy_tags.length ? (
                  <div className="mt-2 flex flex-wrap gap-2">
                    {recommendation.data.llm_strategy_tags.map((tag) => (
                      <Badge key={tag} className="border-zinc-300 bg-white text-zinc-700">
                        {tag}
                      </Badge>
                    ))}
                  </div>
                ) : null}
                <div className="mt-2 flex flex-wrap gap-2">
                  <Badge className="border-zinc-300 bg-white text-zinc-700">
                    used {recommendation.data?.llm_used ? 'yes' : 'no'}
                  </Badge>
                  <Badge className="border-zinc-300 bg-white text-zinc-700">
                    model {recommendation.data?.llm_model ?? 'N/A'}
                  </Badge>
                  {typeof recommendation.data?.llm_confidence === 'number' ? (
                    <Badge className="border-zinc-300 bg-white text-zinc-700">
                      conf {asPercent(recommendation.data.llm_confidence)}
                    </Badge>
                  ) : null}
                  {recommendation.data?.llm_error ? (
                    <Badge className="border-amber-300 bg-amber-100 text-amber-800">
                      err {recommendation.data.llm_error}
                    </Badge>
                  ) : null}
                </div>
              </div>
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
