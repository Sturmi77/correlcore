import { render, screen, fireEvent } from '@testing-library/svelte';
import { readable } from 'svelte/store';
import { describe, expect, it, vi } from 'vitest';
import HomeTodayContext from './HomeTodayContext.svelte';
import type { EntryResponse } from '$lib/api/entries';

vi.mock('svelte-i18n', () => ({
  _: {
    subscribe: (
      run: (
        formatter: (key: string, options?: { values?: Record<string, unknown> }) => string
      ) => void
    ) => {
      run((key: string, options?: { values?: Record<string, unknown> }) => {
        if (options?.values) return `${key} ${JSON.stringify(options.values)}`;
        return key;
      });
      return () => undefined;
    },
  },
  locale: readable('en'),
}));

const entry: EntryResponse = {
  id: 'e1',
  user_id: 'u1',
  entry_date: '2026-05-15',
  slot: 'day',
  mood_score: 4,
  energy: 3,
  stress: 2,
  cycle_day: null,
  work_context: 'homeoffice',
  source: 'direct',
  note: null,
  created_at: '2026-05-15T10:00:00Z',
  updated_at: '2026-05-15T10:00:00Z',
};

describe('HomeTodayContext', () => {
  it('shows no-entry status and the primary log-today action when today has no entry', () => {
    render(HomeTodayContext, {
      props: { todayIso: '2026-05-15', todayEntry: null, loading: false },
    });
    expect(screen.getByTestId('home-today-status').textContent).toContain('home.no_entry_today');
    expect(screen.queryByTestId('home-work-context')).toBeNull();
    expect(screen.getByTestId('home-today-action').textContent).toContain('home.cta_log_today');
  });

  it('hides the action while loading', () => {
    render(HomeTodayContext, {
      props: { todayIso: '2026-05-15', todayEntry: null, loading: true },
    });
    expect(screen.queryByTestId('home-today-action')).toBeNull();
  });

  it('dispatches logToday from the no-entry state too', async () => {
    const spy = vi.fn();
    render(HomeTodayContext, {
      props: { todayIso: '2026-05-15', todayEntry: null, loading: false },
      events: { logToday: spy },
    });
    await fireEvent.click(screen.getByTestId('home-today-action'));
    expect(spy).toHaveBeenCalled();
  });

  it('shows work context and tracked status when entry exists', () => {
    render(HomeTodayContext, {
      props: { todayIso: '2026-05-15', todayEntry: entry, loading: false },
    });
    expect(screen.getByTestId('home-work-context').textContent).toContain(
      'entry.work_context.homeoffice'
    );
    expect(screen.getByTestId('home-today-status').textContent).toContain(
      'home.entry_today_present'
    );
    expect(screen.getByTestId('home-today-action').textContent).toContain('home.cta_edit_entry');
  });

  it('dispatches logToday from the compact action', async () => {
    const spy = vi.fn();
    render(HomeTodayContext, {
      props: { todayIso: '2026-05-15', todayEntry: entry, loading: false },
      events: { logToday: spy },
    });

    await fireEvent.click(screen.getByTestId('home-today-action'));
    expect(spy).toHaveBeenCalled();
  });

  it('shows analysis badge under the date when lastInsightRun is present', () => {
    render(HomeTodayContext, {
      props: {
        todayIso: '2026-05-15',
        todayEntry: entry,
        loading: false,
        lastInsightRun: {
          status: 'succeeded',
          finished_at: '2026-05-15T03:00:00.000Z',
          started_at: '2026-05-15T02:55:00.000Z',
          insight_count: 8,
          trigger_source: 'scheduled',
          generated_for_date: '2026-05-15',
        },
      },
    });

    const badge = screen.getByTestId('home-analysis-status');
    expect(badge.getAttribute('href')).toBe('/insights');
    expect(badge.textContent).toContain('home.worker_run.label');
    expect(badge.textContent).toContain('badge_succeeded_with_count');
  });

  it('shows defective stack containers next to the date in developer diagnostics', () => {
    render(HomeTodayContext, {
      props: {
        todayIso: '2026-05-15',
        todayEntry: entry,
        loading: false,
        lastInsightRun: {
          status: 'never_run',
          finished_at: null,
          started_at: null,
          insight_count: null,
          trigger_source: null,
          generated_for_date: null,
        },
        faultyContainers: [
          { name: 'worker', issue: 'stopped' },
          { name: 'postgres', issue: 'unhealthy' },
        ],
      },
    });

    const badges = screen.getAllByTestId('home-container-status');
    expect(badges).toHaveLength(2);
    expect(badges[0].getAttribute('href')).toBe('/dev');
    expect(badges[0].textContent).toContain('home.container_health.stopped');
    expect(badges[1].textContent).toContain('home.container_health.unhealthy');
    expect(screen.queryByTestId('home-analysis-status')).toBeNull();
  });
});
