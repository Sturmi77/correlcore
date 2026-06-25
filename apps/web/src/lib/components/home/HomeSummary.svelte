<script lang="ts">
  /**
   * HomeSummary — ADR-0014 + ADR-0017 (M3.1 No-Gamification).
   *
   * 7-day aggregation of mood / energy / stress plus tracking consistency.
   * The consistency number keeps the existing entry-run calculation
   * (per ADR-0012 — *not* habit logic). All numbers are computed
   * client-side from the entries the parent already loaded; no extra
   * API call.
   *
   * Renamed in M3.1 (#161):
   *   streakEntries      → consistencyEntries
   *   backendStreak      → backendConsistency
   *   streak (local var) → trackingConsistency
   *   formatStreak       → formatConsistency
   *
   * Consistency ≥ 30 is rendered as `30+` because the loader caps the
   * extended window at 30 days (ADR-0014).
   */

  import { _ } from 'svelte-i18n';
  import type { EntryResponse } from '$lib/api/entries';
  import { averageOver, computeEntryStreak, countDayEntries } from '$lib/utils/streak';
  import MetricCard from './MetricCard.svelte';

  /** Entries within the 7-day display window. */
  export let entries: EntryResponse[] = [];
  /**
   * Wider entry list (up to 30 days) used solely for consistency math. The
   * parent passes this when the 7-day window is exhausted.
   */
  export let consistencyEntries: EntryResponse[] = [];
  export let todayIso: string;
  export let loading = false;
  /** True when the loader hit the 30-day cap. */
  export let consistencyCapped = false;
  /** Backend-authoritative M2 entry-run value, if available. */
  export let backendConsistency: number | null = null;

  $: moodAvg = averageOver(entries, 'mood_score');
  $: energyAvg = averageOver(entries, 'energy');
  $: stressAvg = averageOver(entries, 'stress');
  $: count = countDayEntries(entries);
  $: trackingConsistency =
    backendConsistency ??
    computeEntryStreak(consistencyEntries.length ? consistencyEntries : entries, todayIso);

  function formatAvg(v: number | null): string {
    if (v === null) return '–';
    return v.toFixed(1);
  }

  function formatConsistency(n: number): string {
    if (consistencyCapped && n >= 30) return '30+';
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
    <MetricCard
      metric="mood_score"
      label={$_('home.summary.mood_avg')}
      value={formatAvg(moodAvg)}
      {loading}
    />
    <MetricCard
      metric="energy"
      label={$_('home.summary.energy_avg')}
      value={formatAvg(energyAvg)}
      {loading}
    />
    <MetricCard
      metric="stress"
      label={$_('home.summary.stress_avg')}
      value={formatAvg(stressAvg)}
      {loading}
    />
    <MetricCard
      metric="tracking_consistency"
      label={$_('home.summary.tracking_consistency')}
      value={formatConsistency(trackingConsistency)}
      unit={$_('home.summary.streak_unit')}
      {loading}
    />
    <MetricCard
      metric="count"
      label={$_('home.summary.count')}
      value={String(count)}
      unit="/7"
      {loading}
    />
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

  .home-summary__hint {
    margin: 0;
    font-size: 0.72rem;
    color: var(--color-text-muted);
    line-height: 1.35;
  }
</style>
