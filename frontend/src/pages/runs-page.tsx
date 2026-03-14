import { useEffect, useState } from 'react'
import { Link, useSearchParams } from 'react-router-dom'
import { Badge } from '@/components/ui/badge'
import { Card, CardContent, CardDescription, CardHeader, CardTitle } from '@/components/ui/card'
import { Skeleton } from '@/components/ui/skeleton'
import { useRuns } from '@/features/recommendation/hooks'
import { formatIsoDate } from '@/features/recommendation/utils'

type RunsWinFilter = 'all' | 'wins' | 'losses'

function readPositiveInt(value: string | null, fallback: number): number {
  const parsed = Number(value)
  if (!Number.isFinite(parsed) || parsed <= 0) {
    return fallback
  }
  return Math.floor(parsed)
}

function readWinFilter(value: string | null): RunsWinFilter {
  if (value === 'wins' || value === 'losses') {
    return value
  }
  return 'all'
}

export function RunsPage() {
  const [searchParams, setSearchParams] = useSearchParams()

  const page = readPositiveInt(searchParams.get('page'), 1)
  const pageSize = readPositiveInt(searchParams.get('pageSize'), 20)
  const characterFilter = searchParams.get('character') ?? ''
  const ascensionFilter = searchParams.get('ascension') ?? ''
  const winFilter = readWinFilter(searchParams.get('win'))
  const queryFilter = searchParams.get('query') ?? ''

  const [draftQuery, setDraftQuery] = useState(queryFilter)
  const [draftCharacter, setDraftCharacter] = useState(characterFilter)
  const [draftAscension, setDraftAscension] = useState(ascensionFilter)
  const [draftWin, setDraftWin] = useState<RunsWinFilter>(winFilter)
  const [draftPageSize, setDraftPageSize] = useState(String(pageSize))

  useEffect(() => {
    setDraftQuery(queryFilter)
    setDraftCharacter(characterFilter)
    setDraftAscension(ascensionFilter)
    setDraftWin(winFilter)
    setDraftPageSize(String(pageSize))
  }, [queryFilter, characterFilter, ascensionFilter, winFilter, pageSize])

  const parsedAscension = Number(ascensionFilter)
  const ascensionValue =
    ascensionFilter.trim() === '' || !Number.isFinite(parsedAscension)
      ? undefined
      : Math.max(0, Math.floor(parsedAscension))

  const runs = useRuns({
    page,
    pageSize,
    character: characterFilter.trim() || undefined,
    ascension: ascensionValue,
    win: winFilter === 'all' ? undefined : winFilter === 'wins',
    query: queryFilter.trim() || undefined,
  })

  const runItems = runs.data?.items ?? []

  const updateParam = (updates: Record<string, string | null>, resetPage = false) => {
    const next = new URLSearchParams(searchParams)
    for (const [key, value] of Object.entries(updates)) {
      if (value === null || value.trim() === '') {
        next.delete(key)
      } else {
        next.set(key, value)
      }
    }
    if (resetPage) {
      next.set('page', '1')
    }
    setSearchParams(next)
  }

  const applyFilters = () => {
    updateParam(
      {
        query: draftQuery,
        character: draftCharacter,
        ascension: draftAscension,
        win: draftWin === 'all' ? null : draftWin,
        pageSize: draftPageSize,
      },
      true,
    )
  }

  const resetFilters = () => {
    setDraftQuery('')
    setDraftCharacter('')
    setDraftAscension('')
    setDraftWin('all')
    setDraftPageSize('20')
    setSearchParams(new URLSearchParams({ page: '1', pageSize: '20' }))
  }

  return (
    <main className="mx-auto flex w-full max-w-6xl flex-col gap-6 px-4 py-8 sm:px-6 lg:py-10">
      <section className="rounded-2xl border border-zinc-300/80 bg-gradient-to-r from-lime-50 via-emerald-50 to-teal-50 p-6 shadow-sm">
        <h2 className="text-3xl leading-tight font-semibold text-zinc-900 sm:text-4xl">Runs</h2>
        <p className="mt-2 max-w-2xl text-sm text-zinc-600 sm:text-base">
          Filtra e sfoglia lo storico delle run, poi apri il dettaglio dedicato.
        </p>
      </section>

      <Card className="border-zinc-300/90 bg-zinc-50/70">
        <CardHeader>
          <CardDescription>Run storiche indicizzate</CardDescription>
          <CardTitle>Run History Explorer</CardTitle>
        </CardHeader>
        <CardContent className="space-y-4">
          <form
            className="grid gap-3 sm:grid-cols-2 lg:grid-cols-5"
            onSubmit={(event) => {
              event.preventDefault()
              applyFilters()
            }}
          >
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
                value={draftQuery}
                onChange={(event) => setDraftQuery(event.target.value)}
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
                value={draftCharacter}
                onChange={(event) => setDraftCharacter(event.target.value)}
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
                value={draftAscension}
                onChange={(event) => setDraftAscension(event.target.value)}
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
                value={draftWin}
                onChange={(event) => setDraftWin(readWinFilter(event.target.value))}
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
                value={draftPageSize}
                onChange={(event) => setDraftPageSize(event.target.value)}
              >
                <option value={10}>10</option>
                <option value={20}>20</option>
                <option value={50}>50</option>
              </select>
            </div>
            <div className="sm:col-span-2 lg:col-span-5 flex flex-wrap items-center gap-2">
              <button
                type="submit"
                className="rounded-md border border-zinc-300 bg-zinc-100 px-3 py-1 text-xs font-medium text-zinc-700 transition hover:bg-zinc-200"
              >
                Applica filtri
              </button>
              <button
                type="button"
                className="rounded-md border border-zinc-300 bg-white px-3 py-1 text-xs font-medium text-zinc-600 transition hover:bg-zinc-100"
                onClick={resetFilters}
              >
                Reset filtri
              </button>
            </div>
          </form>

          <div className="rounded-md border border-zinc-300 bg-white">
            <div className="grid grid-cols-6 gap-2 border-b border-zinc-200 px-3 py-2 text-xs font-semibold tracking-[0.1em] text-zinc-500 uppercase">
              <span>Run</span>
              <span>Character</span>
              <span>Asc</span>
              <span>Outcome</span>
              <span>Timestamp</span>
              <span>Azioni</span>
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
              <div className="max-h-80 overflow-y-auto">
                {runItems.map((item) => (
                  <div
                    key={item.run_id}
                    className="grid grid-cols-6 gap-2 border-b border-zinc-100 px-3 py-2 text-sm"
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
                    <span>
                      <Link
                        to={`/runs/${encodeURIComponent(item.run_id)}?${searchParams.toString()}`}
                        className="rounded-md border border-zinc-300 bg-zinc-100 px-2 py-1 text-xs font-medium text-zinc-700 transition hover:bg-zinc-200"
                      >
                        Apri dettaglio
                      </Link>
                    </span>
                  </div>
                ))}
              </div>
            )}
          </div>

          <div className="flex items-center justify-between gap-3">
            <p className="text-xs text-zinc-500">
              pagina {runs.data?.page ?? page} di {runs.data?.total_pages ?? 1} - totale run{' '}
              {runs.data?.total ?? 0}
            </p>
            <div className="flex items-center gap-2">
              <button
                type="button"
                className="rounded-md border border-zinc-300 bg-white px-3 py-1 text-sm text-zinc-700 disabled:opacity-50"
                disabled={(runs.data?.page ?? page) <= 1}
                onClick={() => updateParam({ page: String(Math.max(1, page - 1)) })}
              >
                Prev
              </button>
              <button
                type="button"
                className="rounded-md border border-zinc-300 bg-white px-3 py-1 text-sm text-zinc-700 disabled:opacity-50"
                disabled={(runs.data?.page ?? page) >= (runs.data?.total_pages ?? 1)}
                onClick={() => updateParam({ page: String(page + 1) })}
              >
                Next
              </button>
            </div>
          </div>
        </CardContent>
      </Card>
    </main>
  )
}
