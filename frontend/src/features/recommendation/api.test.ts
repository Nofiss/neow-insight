import { afterEach, describe, expect, it, vi } from 'vitest'

import { fetchLiveContext, fetchRecommendation } from './api'

describe('fetchRecommendation', () => {
  afterEach(() => {
    vi.restoreAllMocks()
  })

  it('builds recommendation query with full contextual params', async () => {
    const fetchMock = vi.fn().mockResolvedValue({
      ok: true,
      json: async () => ({ best_pick: 'CARD.BASH' }),
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
      json: async () => ({ best_pick: 'CARD.BASH' }),
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
