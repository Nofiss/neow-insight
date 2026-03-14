import { render, screen } from '@testing-library/react'
import { MemoryRouter } from 'react-router-dom'
import { describe, expect, it, vi } from 'vitest'
import App from './App'

vi.mock('@/features/recommendation/hooks', () => ({
  DEFAULT_OFFERED: ['CARD.BASH', 'CARD.CLOTHESLINE', 'CARD.OFF_BALANCE'],
  useHealth: () => ({
    isLoading: false,
    isError: false,
    data: { status: 'ok', version: '0.1.0', watcher_enabled: true },
  }),
  useStats: () => ({
    isLoading: false,
    isError: false,
    data: { total_runs: 10, wins: 6, win_rate: 0.6 },
  }),
  useRecommendation: () => ({
    isLoading: false,
    isError: false,
    data: {
      best_pick: 'CARD.BASH',
      win_rate_boost: 0.1,
      confidence: 0.5,
      sample_size: 12,
      card_win_rate: 0.7,
      global_win_rate: 0.6,
      reason: 'ok_contextual',
      scope: 'character_ascension_floor',
      applied_filters: ['character', 'ascension', 'floor'],
      fallback_used: false,
    },
  }),
  useCardInsights: () => ({
    isLoading: false,
    isError: false,
    data: {
      global_win_rate: 0.6,
      insights: [
        {
          card: 'CARD.BASH',
          sample_size: 12,
          card_win_rate: 0.7,
          win_rate_boost: 0.1,
        },
      ],
    },
  }),
  useIngestStatus: () => ({
    isLoading: false,
    isError: false,
    data: {
      scanned: 2,
      imported: 1,
      updated: 1,
      parse_errors: 0,
      skipped: 0,
      recent_issues: [],
      last_processed_run_id: 'run-42',
      last_processed_file: 'test.run',
      last_event_at: '2026-01-01T12:00:00Z',
    },
  }),
  useLiveContext: () => ({
    isLoading: false,
    isError: false,
    dataUpdatedAt: Date.now(),
    data: {
      available: true,
      run_id: 'run-42',
      character: 'IRONCLAD',
      ascension: 10,
      floor: 5,
      offered_cards: ['CARD.BASH', 'CARD.CLOTHESLINE'],
      picked_card: 'CARD.BASH',
    },
  }),
  useRuns: () => ({
    isLoading: false,
    isError: false,
    data: {
      page: 1,
      page_size: 20,
      total: 1,
      total_pages: 1,
      items: [
        {
          run_id: 'run-42',
          seed: 'SEED',
          character: 'IRONCLAD',
          ascension: 10,
          win: true,
          raw_timestamp: '2026-01-01T10:00:00Z',
          imported_at: '2026-01-01T10:01:00Z',
          source_file: 'run-42.run',
          card_choice_count: 2,
          relic_count: 1,
        },
      ],
    },
  }),
  useRunDetail: () => ({
    isLoading: false,
    isError: false,
    data: {
      run_id: 'run-42',
      seed: 'SEED',
      character: 'IRONCLAD',
      ascension: 10,
      win: true,
      raw_timestamp: '2026-01-01T10:00:00Z',
      imported_at: '2026-01-01T10:01:00Z',
      source_file: 'run-42.run',
      card_choices: [
        {
          floor: 1,
          offered_cards: ['CARD.A', 'CARD.B'],
          picked_card: 'CARD.A',
          is_shop: false,
        },
      ],
      relic_history: [{ relic_id: 'RELIC.ANCHOR', floor: 3 }],
      raw_payload: { run_id: 'run-42', value: 123 },
    },
  }),
  useRunTimeline: () => ({
    isLoading: false,
    isError: false,
    data: {
      run_id: 'run-42',
      events: [{ floor: 1, kind: 'card_choice', summary: 'Picked CARD.A', data: {} }],
    },
  }),
  useRunCompleteness: () => ({
    isLoading: false,
    isError: false,
    data: {
      run_id: 'run-42',
      available: 4,
      available_direct: 3,
      available_inferred: 1,
      total: 12,
      missing: ['Campfire choices'],
      inferred: ['Gold'],
    },
  }),
}))

describe('App routing', () => {
  it('renders overview route', () => {
    render(
      <MemoryRouter initialEntries={['/overview']}>
        <App />
      </MemoryRouter>,
    )

    expect(screen.getByRole('heading', { level: 2, name: 'Overview' })).toBeInTheDocument()
    expect(screen.getByText('Sorgente consigli')).toBeInTheDocument()
  })

  it('renders recommendation route', () => {
    render(
      <MemoryRouter initialEntries={['/recommendation']}>
        <App />
      </MemoryRouter>,
    )

    expect(screen.getAllByText('Recommendation').length).toBeGreaterThan(0)
    expect(screen.getByText('Raccomandazione corrente')).toBeInTheDocument()
  })

  it('renders runs route', () => {
    render(
      <MemoryRouter initialEntries={['/runs']}>
        <App />
      </MemoryRouter>,
    )

    expect(screen.getByText('Run History Explorer')).toBeInTheDocument()
    expect(screen.getByText('Apri dettaglio')).toBeInTheDocument()
  })

  it('renders run detail route', () => {
    render(
      <MemoryRouter initialEntries={['/runs/run-42']}>
        <App />
      </MemoryRouter>,
    )

    expect(screen.getByText('Run Detail')).toBeInTheDocument()
    expect(screen.getByText('Timeline floor-by-floor')).toBeInTheDocument()
    expect(screen.getByText('Raw JSON completo')).toBeInTheDocument()
  })
})
