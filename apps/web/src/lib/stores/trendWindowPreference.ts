import { writable } from 'svelte/store';
import { updateUserPreferences } from '$lib/api/preferences';
import { analysisRange, setAnalysisRange } from '$lib/stores/analysisRange';
import { TREND_WINDOW_DAYS_DEFAULT, type TrendWindowDays } from '$lib/utils/trendWindowDays';

type SaveStatus = 'idle' | 'saving' | 'error';

/** Serializes PATCHes so a slow older choice cannot win on the server. */
export function createTrendWindowPreference(
  write: (days: TrendWindowDays, signal: AbortSignal) => Promise<TrendWindowDays>,
  apply: (days: TrendWindowDays, source: 'local' | 'server') => void
) {
  const status = writable<SaveStatus>('idle');
  let actor: string | null = null;
  let confirmed: TrendWindowDays | null = null;
  let desired: TrendWindowDays | null = null;
  let failed: TrendWindowDays | null = null;
  let running = false;
  let revision = 0;
  let controller: AbortController | null = null;

  function bind(userId: string | null): void {
    if (actor === userId) return;
    actor = userId;
    revision += 1;
    controller?.abort();
    confirmed = null;
    desired = null;
    failed = null;
    status.set('idle');
    apply(TREND_WINDOW_DAYS_DEFAULT, 'server');
  }

  function hydrate(userId: string, days: TrendWindowDays | undefined, startedAt: number): void {
    if (actor !== userId || revision !== startedAt || running || desired !== null) return;
    confirmed = days ?? TREND_WINDOW_DAYS_DEFAULT;
    failed = null;
    status.set('idle');
    apply(confirmed, 'server');
  }

  async function drain(): Promise<void> {
    if (running) return;
    running = true;
    try {
      while (desired !== null && actor !== null) {
        const target = desired;
        const requestActor = actor;
        desired = null;
        controller = new AbortController();
        try {
          const saved = await write(target, controller.signal);
          if (actor !== requestActor) continue;
          confirmed = saved;
          failed = null;
          if (desired === null) {
            apply(saved, 'server');
            status.set('idle');
          }
        } catch {
          if (actor !== requestActor) continue;
          if (desired !== null) continue;
          failed = target;
          apply(confirmed ?? TREND_WINDOW_DAYS_DEFAULT, 'server');
          status.set('error');
        }
      }
    } finally {
      controller = null;
      running = false;
      // A new choice can arrive between the final loop check and `finally`.
      if (desired !== null && actor !== null) void drain();
    }
  }

  function select(userId: string, days: TrendWindowDays): void {
    bind(userId);
    revision += 1;
    desired = days;
    failed = null;
    apply(days, 'local');
    status.set('saving');
    void drain();
  }

  function retry(): void {
    if (actor !== null && failed !== null) select(actor, failed);
  }

  return { subscribe: status.subscribe, bind, hydrate, select, retry, revision: () => revision };
}

export const trendWindowPreference = createTrendWindowPreference(
  async (days, signal) => {
    const response = await updateUserPreferences({ trend_window_days: days }, { signal });
    return response.trend_window_days ?? days;
  },
  (days, source) => {
    if (source === 'server') analysisRange.hydrateFromServer(days);
    else setAnalysisRange(days);
  }
);
