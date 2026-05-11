<script lang="ts">
  /**
   * HomeSummary — ADR-0014.
   *
   * 7-day aggregation of mood / energy / stress plus tracking consistency.
   * The consistency number keeps the existing entry-run calculation
   * (per ADR-0012 — *not* habit logic). All numbers are computed
   * client-side from the entries the parent already loaded; no extra
   * API call.
   *
   * Consistency ≥ 30 is rendered as `30+` because the loader caps the
   * extended window at 30 days (ADR-0014).
   */

  import { _ } from 'svelte-i18n';
  import type { EntryResponse } from '$lib/api/entries';
  import { averageOver, computeEntryStreak, countDayEntries } from '$lib/utils/streak';

  /** Entries within the 7-day display window. */
  export let entries: EntryResponse[] = [];
  /**
   * Wider entry list (up to 30 days) used solely for consistency math. The
   * parent passes this when the 7-day window is exhausted.
   */
  export let streakEntries: EntryResponse[] = [];
  export let todayIso: string;
  export let loading = false;
  /** True when the loader hit the 30-day cap. */
  export let streakCapped = false;
  /** Backend-authoritative M2 entry-run value, if available. */
  export let backendStreak: number | null = null;

  $: moodAvg = averageOver(entries, 'mood_score');
  $: energyAvg = averageOver(entries, 'energy');
  $: stressAvg = averageOver(entries, 'stress');
  $: count = countDayEntries(entries);
  $: streak =
    backendStreak ?? computeEntryStreak(streakEntries.length ? streakEntries : entries, todayIso);

  function formatAvg(v: number | null): string {
    if (v === null) return '–';
    return v.toFixed(1);
  }

  function formatStreak(n: number): string {
    if (streakCapped && n >= 30) return '30+';
    return String(n);
  }
</script>

<section
  class="home-summary"
  data-testid="home-summary"
  aria-label={$_('home.summary.heading')}
  data-loading={loading ? 'true' : 'false'}
>
  <h2 class="home-summary__heading">{$_('home.summary.heading')}</h2>

  <dl class="home-summary__grid">
    <div class="home-summary__cell" data-testid="home-summary-mood">
      <dt class="home-summary__label">{$_('home.summary.mood_avg')}</dt>
      <dd class="home-summary__value">{formatAvg(moodAvg)}</dd>
    </div>
    <div class="home-summary__cell" data-testid="home-summary-energy">
      <dt class="home-summary__label">{$_('home.summary.energy_avg')}</dt>
      <dd class="home-summary__value">{formatAvg(energyAvg)}</dd>
    </div>
    <div class="home-summary__cell" data-testid="home-summary-stress">
      <dt class="home-summary__label">{$_('home.summary.stress_avg')}</dt>
      <dd class="home-summary__value">{formatAvg(stressAvg)}</dd>
    </div>
    <div class="home-summary__cell" data-testid="home-summary-streak">
      <dt class="home-summary__label">{$_('home.summary.streak')}</dt>
      <dd class="home-summary__value">
        {formatStreak(streak)}
        <span class="home-summary__unit">{$_('home.summary.streak_unit')}</span>
      </dd>
    </div>
    <div class="home-summary__cell" data-testid="home-summary-count">
      <dt class="home-summary__label">{$_('home.summary.count')}</dt>
      <dd class="home-summary__value">{count}<span class="home-summary__unit">/7</span></dd>
    </div>
  </dl>
  <p class="home-summary__hint">{$_('home.summary.consistency_hint')}</p>
</section>

<style>
  .home-summary {
    width: 100%;
    display: flex;
    flex-direction: column;
    gap: 0.4rem;
  }

  .home-summary__heading {
    font-size: var(--text-sm, 0.85rem);
    font-weight: 600;
    opacity: 0.75;
    letter-spacing: 0.02em;
    text-transform: uppercase;
  }

  .home-summary__grid {
    margin: 0;
    padding: 0;
    display: grid;
    grid-template-columns: repeat(auto-fit, minmax(5rem, 1fr));
    gap: 0.5rem;
  }

  .home-summary__cell {
    display: flex;
    flex-direction: column;
    gap: 0.1rem;
    padding: 0.6rem 0.7rem;
    border-radius: 0.55rem;
    background: rgb(var(--color-surface-100, 243 244 246) / 0.5);
    border: 1px solid rgb(var(--color-surface-300, 209 213 219) / 0.4);
  }

  .home-summary__label {
    font-size: 0.7rem;
    opacity: 0.7;
    margin: 0;
  }

  .home-summary__value {
    font-size: 1.25rem;
    font-weight: 600;
    margin: 0;
    display: flex;
    align-items: baseline;
    gap: 0.25rem;
  }

  .home-summary__unit {
    font-size: 0.7rem;
    opacity: 0.55;
    font-weight: 400;
  }

  .home-summary__hint {
    margin: 0;
    font-size: 0.72rem;
    color: var(--color-text-muted);
    line-height: 1.35;
  }

  .home-summary[data-loading='true'] .home-summary__value {
    opacity: 0.4;
  }
</style>
