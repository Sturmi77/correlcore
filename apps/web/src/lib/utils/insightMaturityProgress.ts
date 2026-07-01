import type { InsightMaturity } from '$lib/api/insights';

type TranslateFn = (key: string, options?: { values?: Record<string, string | number> }) => string;

/** Compact progress copy reused on Home brief and Insights stage header. */
export function maturityProgressMessage(maturity: InsightMaturity, translate: TranslateFn): string {
  if (maturity.phase === 'robust') {
    return translate('maturity.journey.robust_meta', {
      values: { current: maturity.current_entries },
    });
  }

  return translate('maturity.journey.compact_entries_until_next', {
    values: {
      current: maturity.current_entries,
      next: maturity.next_phase_at ?? maturity.current_entries,
      remaining: maturity.entries_until_next ?? 0,
      nextPhase: maturity.next_phase_label ?? '',
    },
  });
}

export function maturityProgressPercent(maturity: InsightMaturity): number {
  const phaseStart: Record<InsightMaturity['phase'], number> = {
    collecting: 0,
    early_patterns: 7,
    provisional: 14,
    robust: 30,
  };

  if (maturity.next_phase_at === null || maturity.phase === 'robust') return 100;

  const start = phaseStart[maturity.phase];
  const span = Math.max(1, maturity.next_phase_at - start);
  const completed = Math.min(span, Math.max(0, maturity.current_entries - start));
  return Math.round((completed / span) * 100);
}
