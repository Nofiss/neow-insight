import { render, screen } from '@testing-library/react'
import { describe, expect, it, vi } from 'vitest'

import { RecommendationDashboard } from './recommendation-dashboard'

vi.mock('./hooks', () => ({
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
}))

describe('RecommendationDashboard', () => {
  it('renders live automation status and recommendation details', () => {
    render(<RecommendationDashboard />)

    expect(screen.getByText('Decision dashboard live per Slay the Spire 2')).toBeInTheDocument()
    expect(screen.getByText('Sorgente consigli')).toBeInTheDocument()
    expect(screen.getByText('Raccomandazione corrente')).toBeInTheDocument()
    expect(screen.getByText('Diagnostica ingest recente')).toBeInTheDocument()
    expect(screen.getByText('Nessun errore ingest recente.')).toBeInTheDocument()
    expect(screen.getAllByText('CARD.BASH').length).toBeGreaterThan(0)
    expect(screen.getByText('scope character_ascension_floor')).toBeInTheDocument()
    expect(screen.getByText(/Filtri applicati:/)).toBeInTheDocument()
  })
})
