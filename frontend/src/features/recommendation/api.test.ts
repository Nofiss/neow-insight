import { afterEach, describe, expect, it, vi } from 'vitest'

import {
  fetchLiveContext,
  fetchRecommendation,
  recoverLiveCards,
  fetchRunCharacters,
  fetchRunCompleteness,
  fetchRunDetail,
  fetchRuns,
  fetchRunTimeline,
} from './api'

describe('fetchRecommendation', () => {
  afterEach(() => {
    vi.restoreAllMocks()
  })

  it('builds recommendation query with full contextual params', async () => {
    const fetchMock = vi.fn().mockResolvedValue({
      ok: true,
      json: async () => ({
        best_pick: 'CARD.BASH',
        llm_pick: 'CARD.CLOTHESLINE',
        llm_rationale: 'Mantiene pressione offensiva.',
        llm_strategy_tags: ['damage', 'tempo'],
        llm_confidence: 0.72,
        llm_model: 'gemma3:latest',
        llm_used: true,
        llm_error: null,
        source: 'hybrid',
      }),
    })
    vi.stubGlobal('fetch', fetchMock)

    await fetchRecommendation(['CARD.BASH', 'CARD.CLOTHESLINE'], {
      character: 'IRONCLAD',
      ascension: 10,
      floor: 5,
    })

    expect(fetchMock).toHaveBeenCalledTimes(1)
    expect(fetchMock).toHaveBeenCalledWith(
      '/api/recommendation?cards=CARD.BASH%2CCARD.CLOTHESLINE&character=IRONCLAD&ascension=10&floor=5',
    )
  })

  it('omits empty contextual params', async () => {
    const fetchMock = vi.fn().mockResolvedValue({
      ok: true,
      json: async () => ({
        best_pick: 'CARD.BASH',
        llm_pick: null,
        llm_rationale: null,
        llm_strategy_tags: [],
        llm_confidence: null,
        llm_model: null,
        llm_used: false,
        llm_error: null,
        source: 'statistical',
      }),
    })
    vi.stubGlobal('fetch', fetchMock)

    await fetchRecommendation(['CARD.BASH'], {
      character: '',
      ascension: undefined,
      floor: undefined,
    })

    expect(fetchMock).toHaveBeenCalledWith('/api/recommendation?cards=CARD.BASH')
  })

  it('throws on non-ok response', async () => {
    const fetchMock = vi.fn().mockResolvedValue({ ok: false, status: 503 })
    vi.stubGlobal('fetch', fetchMock)

    await expect(fetchRecommendation(['CARD.BASH'])).rejects.toThrow('API error 503')
  })
})

describe('fetchLiveContext', () => {
  afterEach(() => {
    vi.restoreAllMocks()
  })

  it('requests live context endpoint', async () => {
    const payload = {
      available: true,
      run_id: 'run-42',
      character: 'IRONCLAD',
      ascension: 10,
      floor: 7,
      offered_cards: ['CARD.BASH', 'CARD.CLOTHESLINE'],
      picked_card: 'CARD.BASH',
    }
    const fetchMock = vi.fn().mockResolvedValue({
      ok: true,
      json: async () => payload,
    })
    vi.stubGlobal('fetch', fetchMock)

    const result = await fetchLiveContext()

    expect(fetchMock).toHaveBeenCalledWith('/api/live/context')
    expect(result).toEqual(payload)
  })
})

describe('recoverLiveCards', () => {
  afterEach(() => {
    vi.restoreAllMocks()
  })

  it('posts screenshot payload to recovery endpoint', async () => {
    const payload = {
      success: true,
      offered_cards: ['CARD.BASH', 'CARD.CLOTHESLINE', 'CARD.OFF_BALANCE'],
      source: 'llm_vision',
      llm_model: 'gemma:8b',
      llm_error: null,
    }
    const fetchMock = vi.fn().mockResolvedValue({
      ok: true,
      json: async () => payload,
    })
    vi.stubGlobal('fetch', fetchMock)

    const result = await recoverLiveCards('base64-image')

    expect(fetchMock).toHaveBeenCalledWith('/api/live/recover-cards', {
      method: 'POST',
      headers: { 'Content-Type': 'application/json' },
      body: JSON.stringify({ image_base64: 'base64-image' }),
    })
    expect(result).toEqual(payload)
  })
})

describe('runs history api', () => {
  afterEach(() => {
    vi.restoreAllMocks()
  })

  it('builds runs query with filters', async () => {
    const fetchMock = vi.fn().mockResolvedValue({
      ok: true,
      json: async () => ({ page: 1, page_size: 20, total: 0, total_pages: 1, items: [] }),
    })
    vi.stubGlobal('fetch', fetchMock)

    await fetchRuns({
      page: 2,
      pageSize: 10,
      character: 'ironclad',
      ascension: 12,
      win: true,
      query: 'run-1',
    })

    expect(fetchMock).toHaveBeenCalledWith(
      '/api/runs?page=2&page_size=10&character=IRONCLAD&ascension=12&win=true&query=run-1',
    )
  })

  it('requests run detail endpoint', async () => {
    const fetchMock = vi.fn().mockResolvedValue({
      ok: true,
      json: async () => ({ run_id: 'run-1' }),
    })
    vi.stubGlobal('fetch', fetchMock)

    await fetchRunDetail('run-1')

    expect(fetchMock).toHaveBeenCalledWith('/api/runs/run-1')
  })

  it('requests run timeline endpoint', async () => {
    const fetchMock = vi.fn().mockResolvedValue({
      ok: true,
      json: async () => ({ run_id: 'run-1', events: [] }),
    })
    vi.stubGlobal('fetch', fetchMock)

    await fetchRunTimeline('run-1')

    expect(fetchMock).toHaveBeenCalledWith('/api/runs/run-1/timeline')
  })

  it('requests run completeness endpoint', async () => {
    const fetchMock = vi.fn().mockResolvedValue({
      ok: true,
      json: async () => ({ run_id: 'run-1', available: 5, total: 12, missing: [] }),
    })
    vi.stubGlobal('fetch', fetchMock)

    await fetchRunCompleteness('run-1')

    expect(fetchMock).toHaveBeenCalledWith('/api/runs/run-1/completeness')
  })

  it('requests available characters endpoint', async () => {
    const payload = { items: ['CHARACTER.NECROBINDER', 'IRONCLAD', 'SILENT'] }
    const fetchMock = vi.fn().mockResolvedValue({
      ok: true,
      json: async () => payload,
    })
    vi.stubGlobal('fetch', fetchMock)

    const result = await fetchRunCharacters()

    expect(fetchMock).toHaveBeenCalledWith('/api/runs/characters')
    expect(result).toEqual(payload)
  })
})
