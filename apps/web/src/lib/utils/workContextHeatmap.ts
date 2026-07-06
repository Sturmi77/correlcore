import type { EntryResponse, WorkContext } from '$lib/api/entries';
import { ENTRY_CONTRACT } from '$lib/contracts/apiContract';

export interface WorkContextHeatmapDay {
  date: string;
  count: number;
}

export interface WorkContextHeatmapContext {
  context: WorkContext;
  days: WorkContextHeatmapDay[];
}

export interface WorkContextHeatmapResponse {
  start_date: string;
  end_date: string;
  contexts: WorkContextHeatmapContext[];
}

export function buildWorkContextHeatmap(
  entries: readonly EntryResponse[],
  window: { start_date: string; end_date: string }
): WorkContextHeatmapResponse {
  const datesByContext = new Map<WorkContext, Set<string>>();

  for (const entry of entries) {
    if (entry.entry_date < window.start_date || entry.entry_date > window.end_date) continue;
    const context = entry.work_context;
    if (!ENTRY_CONTRACT.workContexts.includes(context)) continue;
    const dates = datesByContext.get(context) ?? new Set<string>();
    dates.add(entry.entry_date);
    datesByContext.set(context, dates);
  }

  const contexts = ENTRY_CONTRACT.workContexts.flatMap((context) => {
    const dates = datesByContext.get(context);
    if (!dates || dates.size === 0) return [];
    return [
      {
        context,
        days: [...dates].sort().map((date) => ({ date, count: 1 })),
      },
    ];
  });

  return {
    start_date: window.start_date,
    end_date: window.end_date,
    contexts,
  };
}
