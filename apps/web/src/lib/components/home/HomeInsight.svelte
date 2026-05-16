<script lang="ts">
  /**
   * HomeInsight - M3 Sprint 6.
   *
   * Read-only preview of the latest worker-generated insight. This component
   * deliberately avoids manual triggers, dismiss state, onboarding, analytics
   * controls or schema changes; it only renders data already exposed by the
   * Sprint 5 read API.
   */

  import { _ } from 'svelte-i18n';
  import type { InsightResponse } from '$lib/api/insights';

  export let insight: InsightResponse | null = null;
  export let loading = false;

  function formatConfidence(value: number | null): string {
    if (value === null) return $_('home.insight.confidence_unknown');
    return `${Math.round(value * 100)}%`;
  }
</script>

<section
  class="home-insight"
  data-testid="home-insight"
  aria-label={$_('home.insight.heading')}
  data-loading={loading ? 'true' : 'false'}
>
  <header class="home-insight__header">
    <h2 class="home-insight__heading">{$_('home.insight.heading')}</h2>
    {#if insight}
      <span
        class="home-insight__tier"
        data-tier={insight.tier}
        title={$_(`home.insight.tier_help.${insight.tier}`)}
        aria-label={`${$_(`home.insight.tier.${insight.tier}`)}: ${$_(
          `home.insight.tier_help.${insight.tier}`
        )}`}
      >
        {$_(`home.insight.tier.${insight.tier}`)}
      </span>
    {/if}
  </header>

  {#if loading && !insight}
    <div class="home-insight__body home-insight__body--muted">
      <span class="home-insight__line home-insight__line--wide"></span>
      <span class="home-insight__line"></span>
    </div>
  {:else if insight}
    <div class="home-insight__body">
      <p class="home-insight__statement">
        {insight.statement ?? $_('home.insight.empty_statement')}
      </p>
      <dl class="home-insight__meta" aria-label={$_('home.insight.meta_label')}>
        <div>
          <dt>{$_('home.insight.confidence')}</dt>
          <dd>{formatConfidence(insight.confidence)}</dd>
        </div>
        <div>
          <dt>{$_('home.insight.sample_size')}</dt>
          <dd>{insight.sample_n}</dd>
        </div>
        <div>
          <dt>{$_('home.insight.updated')}</dt>
          <dd>{insight.generated_for_date}</dd>
        </div>
      </dl>
      <p class="home-insight__disclaimer">{$_('disclaimer.medical')}</p>
      <a class="home-insight__link" href="/insights">{$_('home.insight.more')}</a>
    </div>
  {:else}
    <div class="home-insight__body home-insight__body--muted">
      <p class="home-insight__empty">{$_('home.insight.empty')}</p>
      <p class="home-insight__hint">{$_('home.insight.empty_hint')}</p>
    </div>
  {/if}
</section>

<style>
  .home-insight {
    width: 100%;
    display: flex;
    flex-direction: column;
    gap: 0.45rem;
  }

  .home-insight__header {
    display: flex;
    align-items: center;
    justify-content: space-between;
    gap: 0.75rem;
  }

  .home-insight__heading {
    font-size: var(--text-sm, 0.85rem);
    font-weight: 600;
    opacity: 0.75;
    letter-spacing: 0.02em;
    text-transform: uppercase;
  }

  .home-insight__tier {
    flex: 0 0 auto;
    max-width: 11rem;
    overflow: hidden;
    text-overflow: ellipsis;
    white-space: nowrap;
    border-radius: 999px;
    padding: 0.18rem 0.55rem;
    font-size: 0.68rem;
    font-weight: 600;
    background: var(--color-surface-offset);
    color: var(--color-text-muted);
  }

  .home-insight__tier[data-tier='early'] {
    background: color-mix(in srgb, var(--color-warning) 14%, transparent);
    color: var(--color-warning);
  }

  .home-insight__tier[data-tier='preliminary'] {
    background: color-mix(in srgb, var(--color-primary) 10%, transparent);
    color: var(--color-primary);
  }

  .home-insight__tier[data-tier='developing'] {
    background: color-mix(in srgb, var(--color-warning) 20%, transparent);
    color: var(--color-warning);
  }

  .home-insight__tier[data-tier='robust'] {
    background: color-mix(in srgb, var(--color-success) 14%, transparent);
    color: var(--color-success);
  }

  .home-insight__body {
    display: flex;
    flex-direction: column;
    gap: 0.6rem;
    padding: 0.75rem 0.85rem;
    border-radius: 0.6rem;
    border: 1px solid var(--color-border-chart);
    background: var(--color-surface-chart-bg);
  }

  .home-insight__body--muted {
    color: var(--color-text-muted);
  }

  .home-insight__statement,
  .home-insight__empty,
  .home-insight__hint,
  .home-insight__disclaimer {
    margin: 0;
  }

  .home-insight__link {
    width: fit-content;
    font-size: 0.78rem;
    font-weight: 700;
    color: var(--color-primary);
  }

  .home-insight__statement {
    font-size: var(--text-sm, 0.88rem);
    line-height: 1.45;
  }

  .home-insight__meta {
    margin: 0;
    display: grid;
    grid-template-columns: repeat(3, minmax(0, 1fr));
    gap: 0.5rem;
  }

  .home-insight__meta div {
    min-width: 0;
  }

  .home-insight__meta dt {
    margin: 0;
    font-size: 0.68rem;
    color: var(--color-text-muted);
  }

  .home-insight__meta dd {
    margin: 0.1rem 0 0;
    font-size: 0.8rem;
    font-weight: 600;
    overflow-wrap: anywhere;
  }

  .home-insight__hint,
  .home-insight__disclaimer {
    font-size: 0.72rem;
    line-height: 1.35;
    color: var(--color-text-muted);
  }

  .home-insight__line {
    display: block;
    width: 62%;
    height: 0.7rem;
    border-radius: 999px;
    background: var(--color-surface-offset);
  }

  .home-insight__line--wide {
    width: 86%;
  }

  .home-insight[data-loading='true'] {
    opacity: 0.75;
  }

  @media (max-width: 420px) {
    .home-insight__header {
      align-items: flex-start;
      flex-direction: column;
      gap: 0.35rem;
    }

    .home-insight__tier {
      max-width: 100%;
    }

    .home-insight__meta {
      grid-template-columns: 1fr;
    }
  }
</style>
