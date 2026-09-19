<script lang="ts">
  /**
   * G2 with/without distribution strips (Phase 7 / ADR-0043).
   * Natural frequencies with two denominators; lift stays out of the primary view.
   */
  import { _ } from 'svelte-i18n';
  import type { WithWithoutView } from '$lib/utils/withWithoutDistribution';

  export let view: WithWithoutView;
  export let compact = false;

  $: maxWith = Math.max(1, ...view.withDistribution);
  $: maxWithout = Math.max(1, ...view.withoutDistribution);
  $: levels = view.withDistribution.map((_, index) => view.scaleMin + index);
</script>

<section
  class="ww"
  class:ww--compact={compact}
  data-testid="with-without-distribution"
  aria-label={$_('insights.card.with_without_aria', { values: { subject: view.subjectLabel } })}
>
  <header class="ww__header">
    <h3 class="ww__title">
      {$_('insights.card.with_without_title', { values: { subject: view.subjectLabel } })}
    </h3>
    {#if !compact}
      <p class="ww__sub">{$_('insights.card.with_without_subtitle')}</p>
    {/if}
  </header>

  <p class="ww__freq" data-testid="with-without-frequencies">
    {$_('insights.card.with_without_freq', {
      values: {
        withGood: view.withGood,
        withN: view.withN,
        withoutGood: view.withoutGood,
        withoutN: view.withoutN,
        subject: view.subjectLabel,
      },
    })}
  </p>

  <div class="ww__strips" role="img" aria-hidden="true">
    <div class="ww__row">
      <span class="ww__label">
        {$_('insights.card.with_label', {
          values: { subject: view.subjectLabel, n: view.withN },
        })}
      </span>
      <div class="ww__bars">
        {#each view.withDistribution as count, i}
          <span
            class="ww__bar ww__bar--with"
            style={`height: ${Math.max(8, (count / maxWith) * 100)}%`}
            title={`${levels[i]}: ${count}`}
          ></span>
        {/each}
      </div>
    </div>
    <div class="ww__row">
      <span class="ww__label">
        {$_('insights.card.without_label', {
          values: { subject: view.subjectLabel, n: view.withoutN },
        })}
      </span>
      <div class="ww__bars">
        {#each view.withoutDistribution as count, i}
          <span
            class="ww__bar ww__bar--without"
            style={`height: ${Math.max(8, (count / maxWithout) * 100)}%`}
            title={`${levels[i]}: ${count}`}
          ></span>
        {/each}
      </div>
    </div>
    <div class="ww__scale">
      <span>{view.scaleMin}</span>
      <span>{view.scaleMax}</span>
    </div>
  </div>

  <ul class="ww__meta">
    <li data-testid="with-without-overlap">
      {$_(`insights.card.overlap_${view.overlap}`)}
    </li>
    {#if view.meanShift != null && !view.isNullResult}
      <li data-testid="with-without-shift">
        {$_('insights.card.mean_shift', { values: { shift: view.meanShift } })}
      </li>
    {/if}
  </ul>
</section>

<style>
  .ww {
    display: flex;
    flex-direction: column;
    gap: var(--space-2, 0.5rem);
  }
  .ww__header {
    display: flex;
    flex-direction: column;
    gap: 0.15rem;
  }
  .ww__title {
    margin: 0;
    font-size: var(--text-sm, 0.875rem);
    font-weight: 600;
  }
  .ww__sub {
    margin: 0;
    font-size: var(--text-xs, 0.75rem);
    color: var(--color-text-muted);
  }
  .ww__freq {
    margin: 0;
    font-size: var(--text-sm, 0.875rem);
    line-height: 1.4;
    color: var(--color-text);
  }
  .ww__strips {
    display: flex;
    flex-direction: column;
    gap: 0.35rem;
  }
  .ww__row {
    display: grid;
    grid-template-columns: minmax(5.5rem, 7.5rem) 1fr;
    gap: 0.5rem;
    align-items: end;
  }
  .ww__label {
    font-size: var(--text-xs, 0.75rem);
    color: var(--color-text-muted);
    text-align: right;
    line-height: 1.2;
  }
  .ww__bars {
    display: flex;
    align-items: flex-end;
    gap: 3px;
    height: 2.75rem;
    padding: 0 0.15rem;
    border-bottom: 1px solid oklch(from var(--color-text) l c h / 0.12);
  }
  .ww--compact .ww__bars {
    height: 2rem;
  }
  .ww__bar {
    flex: 1;
    min-width: 0;
    /* token-exempt: 2px micro-bar cap; sm is the closest token */
    border-radius: var(--radius-sm) var(--radius-sm) 0 0;
  }
  .ww__bar--with {
    background: var(--color-primary);
  }
  .ww__bar--without {
    background: oklch(from var(--color-text-muted) l c h / 0.55);
  }
  .ww__scale {
    display: flex;
    justify-content: space-between;
    margin-left: 8rem;
    font-size: var(--text-2xs);
    color: var(--color-text-faint);
    font-variant-numeric: tabular-nums;
  }
  .ww__meta {
    list-style: none;
    margin: 0;
    padding: 0;
    display: flex;
    flex-wrap: wrap;
    gap: 0.75rem;
    font-size: var(--text-xs, 0.75rem);
    color: var(--color-text-muted);
  }
</style>
