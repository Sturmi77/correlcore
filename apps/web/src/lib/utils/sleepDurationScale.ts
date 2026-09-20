/**
 * Sleep-duration colour scale — #928 D3.
 *
 * Every other strip metric is logged on a 1–5 scale whose midpoint is part of
 * the scale itself: a 3 is the middle of what the user was asked. Sleep
 * duration has no such midpoint. The strip nonetheless encoded it divergently
 * around a fixed `midpoint: 3`, which after the 0–720 min normalisation is
 * exactly 6 hours — so every night under six hours was drawn on the "negative"
 * side and every night over it on the "positive" side. That is a health norm,
 * and the app had implemented it as an axis configuration.
 *
 * The replacement uses the user's own median as the neutral point, so a cell
 * reads "longer / shorter than your usual night" — a statement about their own
 * data. Until there is enough history for a median to mean anything, there is
 * no neutral point to use and the caller falls back to a sequential ramp that
 * encodes duration only.
 */

/** Below this many logged nights, a personal median is not worth standing on. */
export const SLEEP_BASELINE_MIN_DAYS = 14;

/**
 * Smallest spread the divergent scale will stretch across. Without it, a week
 * of near-identical nights would saturate the strip on a few minutes of
 * variation. 45 minutes is roughly "the same night, give or take".
 */
export const SLEEP_SPREAD_FLOOR_MINUTES = 45;

export type SleepDurationScale =
  | {
      mode: 'divergent';
      loggedDays: number;
      /** Neutral point: the user's own median night, in minutes. */
      medianMinutes: number;
      /** Half-width of the scale, in minutes. Encodes to ±1 at the extremes. */
      spreadMinutes: number;
    }
  | {
      mode: 'sequential';
      loggedDays: number;
      minMinutes: number;
      maxMinutes: number;
    };

function median(sorted: readonly number[]): number {
  const mid = Math.floor(sorted.length / 2);
  return sorted.length % 2 === 1 ? sorted[mid] : (sorted[mid - 1] + sorted[mid]) / 2;
}

/**
 * Derive the scale for the sleep-duration row from the nights actually shown.
 *
 * Values are minutes; `null` / `undefined` / non-finite entries are days with
 * no sleep logged and take no part in the baseline.
 */
export function sleepDurationScale(
  values: readonly (number | null | undefined)[]
): SleepDurationScale {
  const logged = values.filter(
    (value): value is number => typeof value === 'number' && Number.isFinite(value)
  );
  const sorted = [...logged].sort((a, b) => a - b);
  const loggedDays = sorted.length;

  if (loggedDays < SLEEP_BASELINE_MIN_DAYS) {
    return {
      mode: 'sequential',
      loggedDays,
      minMinutes: sorted[0] ?? 0,
      maxMinutes: sorted[sorted.length - 1] ?? 0,
    };
  }

  const medianMinutes = median(sorted);
  // Max absolute deviation, so the most unusual night in the window sits at
  // full strength and everything else is read against it.
  const maxDeviation = sorted.reduce(
    (worst, value) => Math.max(worst, Math.abs(value - medianMinutes)),
    0
  );

  return {
    mode: 'divergent',
    loggedDays,
    medianMinutes,
    spreadMinutes: Math.max(SLEEP_SPREAD_FLOOR_MINUTES, maxDeviation),
  };
}

/** "7 h 20 min" / "45 min" — the duration a cell actually stands for. */
export function formatSleepMinutes(minutes: number): string {
  const rounded = Math.round(minutes);
  const hours = Math.floor(rounded / 60);
  const rest = rounded % 60;
  if (hours === 0) return `${rest} min`;
  return rest === 0 ? `${hours} h` : `${hours} h ${rest} min`;
}
