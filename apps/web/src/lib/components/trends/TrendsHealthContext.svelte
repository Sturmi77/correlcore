<script lang="ts">
  import { _ } from 'svelte-i18n';
  import Lock from '@lucide/svelte/icons/lock';
  import { ICON_SIZE_SM } from '$lib/constants/iconSizes';
  import type { EntryResponse } from '$lib/api/entries';
  import type { InsightMaturity } from '$lib/api/insights';
  import type {
    HealthContextResponse,
    HealthContextSection,
    HealthContextSectionId,
  } from '$lib/api/stats';
  import InsightStageHeader from '$lib/components/insights/InsightStageHeader.svelte';

  export let healthContext: HealthContextResponse | null = null;
  // Reuse the shared maturity surface (spec G1 — no second readiness surface).
  export let maturity: InsightMaturity | null = null;
  export let cycleEntries: EntryResponse[] = [];

  interface CoverageRow {
    id: 'entry' | HealthContextSectionId;
    labelKey: string;
    pct: number;
    daysWithData: number;
    windowDays: number;
    section: HealthContextSection | null;
    href: string | null;
    deepLinkKey: string | null;
  }

  function sectionById(id: HealthContextSectionId): HealthContextSection | null {
    return healthContext?.sections.find((section) => section.id === id) ?? null;
  }

  function pctLabel(pct: number): number {
    return Math.round(pct * 100);
  }

  $: coverageRows = healthContext
    ? ([
        {
          id: 'entry',
          labelKey: 'trends.maturity.entry.label',
          pct: healthContext.coverage.entry.pct,
          daysWithData: healthContext.coverage.entry.days_with_data,
          windowDays: healthContext.coverage.entry.window_days,
          section: null,
          href: null,
          deepLinkKey: null,
        },
        {
          id: 'symptom',
          labelKey: 'trends.maturity.symptom.label',
          pct: healthContext.coverage.symptom.pct,
          daysWithData: healthContext.coverage.symptom.days_with_data,
          windowDays: healthContext.coverage.symptom.window_days,
          section: sectionById('symptom'),
          href: '/insights',
          deepLinkKey: 'trends.maturity.symptom.deep_link',
        },
        {
          id: 'sleep',
          labelKey: 'trends.maturity.sleep.label',
          pct: healthContext.coverage.sleep.pct,
          daysWithData: healthContext.coverage.sleep.days_with_data,
          windowDays: healthContext.coverage.sleep.window_days,
          section: sectionById('sleep'),
          href: '/health-connect',
          deepLinkKey: 'trends.maturity.sleep.deep_link',
        },
      ] satisfies CoverageRow[])
    : [];

  function isLocked(row: CoverageRow): boolean {
    return row.section !== null && !row.section.unlocked;
  }
</script>

<section
  class="trends-health"
  data-testid="trends-health-context"
  aria-label={$_('trends.maturity.heading')}
>
  <div class="trends-health__intro">
    <h2>{$_('trends.maturity.heading')}</h2>
    <p>{$_('trends.maturity.body')}</p>
  </div>

  {#if maturity}
    <InsightStageHeader {maturity} />
  {/if}

  {#if healthContext}
    <div class="trends-health__coverage">
      {#each coverageRows as row (row.id)}
        {@const locked = isLocked(row)}
        <div class="metric" class:metric--locked={locked}>
          <div class="metric__top">
            <span class="metric__name">
              {#if locked}
                <Lock size={ICON_SIZE_SM} class="metric__lock" aria-hidden="true" />
              {/if}
              {$_(row.labelKey)}
            </span>
            <span class="metric__pct" class:metric__pct--locked={locked}>
              {#if locked}
                {$_('trends.maturity.locked')}
              {:else}
                {pctLabel(row.pct)}&nbsp;%
              {/if}
            </span>
          </div>
          <div
            class="bar"
            class:bar--gated={locked}
            role="meter"
            aria-valuemin={0}
            aria-valuemax={100}
            aria-valuenow={pctLabel(row.pct)}
            aria-label={$_(row.labelKey)}
          >
            <span style={`width: ${Math.max(2, pctLabel(row.pct))}%`}></span>
          </div>
          <div class="metric__foot">
            <span class="metric__note">
              {#if row.section}
                {$_(row.section.copy_key, {
                  values: { count: row.section.entries_until_unlock ?? 0 },
                })}
              {:else}
                {$_('trends.maturity.entry.caption', {
                  values: { days: row.daysWithData, window: row.windowDays },
                })}
              {/if}
            </span>
            {#if !locked && row.href && row.deepLinkKey}
              <a class="deep-link" href={row.href}>{$_(row.deepLinkKey)}</a>
            {/if}
          </div>
        </div>
      {/each}
    </div>
  {/if}

  {#if cycleEntries.length > 0}
    <section class="trends-health__cycle" aria-label={$_('trends.cycle.heading')}>
      <div>
        <span class="trends-health__cycle-kicker">{$_('trends.maturity.cycle_context')}</span>
        <h3>{$_('trends.cycle.heading')}</h3>
        <p>{$_('trends.cycle.body')}</p>
      </div>
      <div class="trends-health__cycle-strip">
        {#each cycleEntries.slice(0, 14) as entry}
          <span title={`${entry.entry_date}: ${entry.cycle_day}`}>
            <small>{entry.entry_date.slice(5)}</small>
            <strong>{entry.cycle_day}</strong>
          </span>
        {/each}
      </div>
    </section>
  {/if}
</section>

<style>
  .trends-health {
    display: flex;
    flex-direction: column;
    gap: var(--space-4);
    padding: var(--space-4);
    border-radius: var(--radius-md);
    background: var(--color-surface-chart-bg);
    border: 1px solid var(--color-border-chart);
  }

  .trends-health__intro h2,
  .trends-health__cycle h3,
  .trends-health__cycle p {
    margin: 0;
  }

  .trends-health__intro h2 {
    font-size: var(--text-lg);
  }

  .trends-health__intro p {
    margin-top: var(--space-1);
    color: var(--color-text-muted);
    font-size: var(--text-sm);
  }

  .trends-health__coverage {
    display: flex;
    flex-direction: column;
    gap: var(--space-3);
  }

  .metric {
    padding: var(--space-3);
    border: 1px solid var(--color-border);
    border-radius: var(--radius-md);
    background: color-mix(in srgb, var(--color-surface-2) 72%, transparent);
  }

  .metric--locked {
    border-style: dashed;
    background: color-mix(in srgb, var(--color-surface-2) 45%, transparent);
  }

  .metric__top {
    display: flex;
    align-items: baseline;
    justify-content: space-between;
    gap: var(--space-2);
  }

  .metric__name {
    display: inline-flex;
    align-items: center;
    gap: 0.4rem;
    font-size: var(--text-sm);
    font-weight: 600;
  }

  .metric__name :global(.metric__lock) {
    color: var(--color-text-faint);
    flex: 0 0 auto;
  }

  .metric__pct {
    font-size: var(--text-base);
    font-weight: 700;
    font-variant-numeric: tabular-nums;
  }

  .metric__pct--locked {
    font-size: var(--text-sm);
    font-weight: 600;
    color: var(--color-text-faint);
  }

  .bar {
    height: 0.5rem;
    margin-top: var(--space-2);
    border-radius: var(--radius-full);
    background: color-mix(in srgb, var(--color-border) 55%, transparent);
    overflow: hidden;
  }

  .bar > span {
    display: block;
    height: 100%;
    border-radius: inherit;
    background: var(--color-primary);
  }

  /* Gated sections read as neutral, not a red/green verdict (FRONTEND.md / ADR-0035). */
  .bar--gated > span {
    background: repeating-linear-gradient(
      45deg,
      var(--color-text-faint) 0 5px,
      transparent 5px 10px
    );
    opacity: 0.5;
  }

  .metric__foot {
    display: flex;
    flex-wrap: wrap;
    align-items: center;
    justify-content: space-between;
    gap: var(--space-1) var(--space-2);
    margin-top: var(--space-2);
  }

  .metric__note {
    font-size: var(--text-xs);
    color: var(--color-text-muted);
  }

  .deep-link {
    display: inline-flex;
    align-items: center;
    min-height: 44px;
    padding: 0 var(--space-1);
    font-size: var(--text-xs);
    font-weight: 700;
    color: var(--color-primary);
    text-decoration: none;
    white-space: nowrap;
  }

  .deep-link:hover {
    text-decoration: underline;
    text-underline-offset: 2px;
  }

  .trends-health__cycle {
    display: grid;
    gap: var(--space-3);
    padding: var(--space-3);
    border: 1px solid var(--color-border);
    border-radius: var(--radius-md);
    background: color-mix(in srgb, var(--color-surface-2) 72%, transparent);
  }

  .trends-health__cycle-kicker {
    font-size: var(--text-xs);
    text-transform: uppercase;
    letter-spacing: 0.06em;
    color: var(--color-text-faint);
  }

  .trends-health__cycle h3 {
    font-size: var(--text-base);
  }

  .trends-health__cycle p {
    font-size: var(--text-xs);
    color: var(--color-text-muted);
  }

  .trends-health__cycle-strip {
    display: flex;
    gap: var(--space-2);
    overflow-x: auto;
    padding-bottom: var(--space-1);
  }

  .trends-health__cycle-strip span {
    min-width: 3.75rem;
    min-height: 3.75rem;
    display: grid;
    place-items: center;
    border: 1px solid color-mix(in srgb, var(--color-primary) 22%, var(--color-border));
    border-radius: var(--radius-sm);
    background: var(--color-surface);
  }

  .trends-health__cycle-strip small {
    color: var(--color-text-muted);
    font-size: var(--text-xs);
  }

  .trends-health__cycle-strip strong {
    font-size: var(--text-lg);
  }
</style>
