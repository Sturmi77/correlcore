<script lang="ts">
  /**
   * Legacy/inactive: route screens now use the compact InsightStageHeader.
   * Keep this component only for reference tests until the old phase UI is removed.
   */
  import { _ } from 'svelte-i18n';
  import type { InsightMaturity, InsightMaturityPhase } from '$lib/api/insights';
  import InsightJourneyExplainer from './InsightJourneyExplainer.svelte';

  export let maturity: InsightMaturity;
  export let collapsible = false;
  export let initialCollapsed = false;

  let collapsed = initialCollapsed;
  let explainerOpen = false;

  const phaseStart: Record<InsightMaturityPhase, number> = {
    collecting: 0,
    early_patterns: 7,
    provisional: 14,
    robust: 30,
  };

  const nextPhaseKey: Record<Exclude<InsightMaturityPhase, 'robust'>, InsightMaturityPhase> = {
    collecting: 'early_patterns',
    early_patterns: 'provisional',
    provisional: 'robust',
  };

  function progressPercent(current: InsightMaturity): number {
    if (current.next_phase_at === null || current.phase === 'robust') return 100;
    const start = phaseStart[current.phase];
    const span = Math.max(1, current.next_phase_at - start);
    const completed = Math.min(span, Math.max(0, current.current_entries - start));
    return Math.round((completed / span) * 100);
  }

  function nextLabelKey(phase: InsightMaturityPhase): string | null {
    if (phase === 'robust') return null;
    return `maturity.${nextPhaseKey[phase]}.label`;
  }

  $: phaseLabel = $_(`maturity.${maturity.phase}.label`);
  $: phaseDescription = $_(maturity.user_message_key);
  $: nextLabel = nextLabelKey(maturity.phase);
  $: fillPercent = progressPercent(maturity);
  $: collapsedLabel = collapsed ? $_('maturity.journey.expand') : $_('maturity.journey.collapse');
</script>

<section
  class="journey"
  class:journey--collapsed={collapsed}
  data-testid="insight-journey-banner"
  data-phase={maturity.phase}
  aria-label={$_('maturity.journey.aria_label')}
>
  <header class="journey__header">
    <span class="journey__icon" aria-hidden="true">{maturity.phase_index}</span>
    <div class="journey__heading">
      <p class="journey__eyebrow">
        {$_('maturity.journey.phase_heading', {
          values: { phaseIndex: maturity.phase_index, label: phaseLabel },
        })}
      </p>
      <h2>{phaseLabel}</h2>
    </div>
    {#if collapsible}
      <button
        class="journey__collapse"
        type="button"
        aria-expanded={!collapsed}
        on:click={() => (collapsed = !collapsed)}
      >
        {collapsedLabel}
      </button>
    {/if}
  </header>

  {#if !collapsed}
    <div
      class="journey__track"
      role="meter"
      aria-valuemin={0}
      aria-valuemax={100}
      aria-valuenow={fillPercent}
      aria-label={$_('maturity.journey.progress_aria')}
    >
      <span class="journey__fill" style={`width: ${fillPercent}%`}></span>
    </div>

    <p class="journey__meta" data-testid="insight-journey-meta">
      {#if maturity.phase === 'robust'}
        {$_('maturity.journey.robust_meta', {
          values: { current: maturity.current_entries },
        })}
      {:else if nextLabel}
        {$_('maturity.journey.entries_until_next', {
          values: {
            current: maturity.current_entries,
            remaining: maturity.entries_until_next ?? 0,
            nextPhase: $_(nextLabel),
          },
        })}
      {/if}
    </p>

    <p class="journey__description">{phaseDescription}</p>

    <button class="journey__help" type="button" on:click={() => (explainerOpen = true)}>
      {$_('maturity.journey.help_cta')}
    </button>
  {/if}

  <InsightJourneyExplainer open={explainerOpen} on:close={() => (explainerOpen = false)} />
</section>

<style>
  .journey {
    display: flex;
    flex-direction: column;
    gap: var(--space-3);
    padding: var(--space-4);
    border: 1px solid var(--color-border-chart);
    border-radius: var(--radius-lg);
    background: var(--color-surface-chart-bg);
    color: var(--color-text);
    box-shadow: var(--shadow-sm);
  }

  .journey__header {
    display: flex;
    align-items: center;
    gap: var(--space-3);
  }

  .journey__icon {
    display: inline-flex;
    align-items: center;
    justify-content: center;
    width: 2.25rem;
    height: 2.25rem;
    flex: 0 0 auto;
    border-radius: var(--radius-full);
    background: var(--color-primary);
    color: var(--color-text-inverse);
    font-weight: 700;
  }

  .journey__heading {
    min-width: 0;
    flex: 1;
  }

  .journey__eyebrow,
  .journey__meta,
  .journey__description {
    margin: 0;
  }

  .journey__eyebrow {
    color: var(--color-text-muted);
    font-size: var(--text-xs);
    font-weight: 600;
    letter-spacing: 0.02em;
    text-transform: uppercase;
  }

  .journey__heading h2 {
    margin: 0;
    font-size: var(--text-base);
    font-weight: 700;
  }

  .journey__collapse,
  .journey__help {
    color: var(--color-primary);
    font-size: var(--text-sm);
    font-weight: 600;
    text-decoration: underline;
    text-underline-offset: 2px;
  }

  .journey__track {
    height: 0.55rem;
    overflow: hidden;
    border-radius: var(--radius-full);
    background: color-mix(in srgb, var(--color-border) 55%, transparent);
  }

  .journey__fill {
    display: block;
    height: 100%;
    border-radius: inherit;
    background: var(--color-primary);
    transition: width 220ms ease;
  }

  .journey__meta {
    color: var(--color-text);
    font-size: var(--text-sm);
    font-weight: 600;
  }

  .journey__description {
    color: var(--color-text-muted);
    font-size: var(--text-sm);
    line-height: 1.5;
  }

  .journey__help {
    align-self: flex-start;
  }

  @media (prefers-reduced-motion: reduce) {
    .journey__fill {
      transition: none;
    }
  }
</style>
