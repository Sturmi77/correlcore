<script lang="ts">
  import { createEventDispatcher } from 'svelte';
  import { _ } from 'svelte-i18n';
  import type { InsightMaturity, InsightMaturityPhase } from '$lib/api/insights';
  import { maturityMilestoneKey } from '$lib/utils/insightMaturityMilestones';
  import InsightJourneyExplainer from './InsightJourneyExplainer.svelte';

  export let maturity: InsightMaturity;
  export let showMilestone = false;

  const dispatch = createEventDispatcher<{ dismissMilestone: { key: string } }>();

  let explainerOpen = false;

  const phaseStart: Record<InsightMaturityPhase, number> = {
    collecting: 0,
    early_patterns: 7,
    provisional: 14,
    robust: 30,
  };

  function progressPercent(current: InsightMaturity): number {
    if (current.next_phase_at === null || current.phase === 'robust') return 100;
    const start = phaseStart[current.phase];
    const span = Math.max(1, current.next_phase_at - start);
    const completed = Math.min(span, Math.max(0, current.current_entries - start));
    return Math.round((completed / span) * 100);
  }

  $: phaseLabel = $_(`maturity.${maturity.phase}.label`);
  $: phaseDescription = $_(maturity.user_message_key);
  $: fillPercent = progressPercent(maturity);
  $: milestoneKey = maturityMilestoneKey(maturity.phase);
  $: milestoneTitle = milestoneKey ? $_(`maturity.milestone_card.${maturity.phase}.title`) : '';
  $: milestoneBody = milestoneKey
    ? $_(`maturity.milestone_card.${maturity.phase}.body`, {
        values: { n: maturity.current_entries },
      })
    : '';
</script>

<section
  class="stage"
  data-testid="insight-stage-header"
  data-phase={maturity.phase}
  aria-label={$_('insights.stage.aria_label')}
>
  <div class="stage__main">
    <div class="stage__marker" aria-hidden="true">{maturity.phase_index}</div>
    <div class="stage__copy">
      <p class="stage__label">
        {$_('maturity.journey.phase_heading', {
          values: { phaseIndex: maturity.phase_index, label: phaseLabel },
        })}
      </p>
      <h2>{phaseLabel}</h2>
      <p>{phaseDescription}</p>
    </div>
  </div>

  <div class="stage__meta">
    <div
      class="stage__track"
      role="meter"
      aria-valuemin={0}
      aria-valuemax={100}
      aria-valuenow={fillPercent}
      aria-label={$_('maturity.journey.progress_aria')}
    >
      <span style={`width: ${fillPercent}%`}></span>
    </div>
    <p data-testid="insight-stage-meta">
      {#if maturity.phase === 'robust'}
        {$_('maturity.journey.robust_meta', {
          values: { current: maturity.current_entries },
        })}
      {:else}
        {$_('maturity.journey.entries_until_next', {
          values: {
            current: maturity.current_entries,
            remaining: maturity.entries_until_next ?? 0,
            nextPhase: maturity.next_phase_label ?? '',
          },
        })}
      {/if}
    </p>
  </div>

  {#if showMilestone && milestoneKey}
    <div class="stage__milestone" data-testid="insight-stage-milestone">
      <div>
        <strong>{milestoneTitle}</strong>
        <p>{milestoneBody}</p>
      </div>
      <button
        type="button"
        class="stage__text-button"
        on:click={() => dispatch('dismissMilestone', { key: milestoneKey ?? '' })}
      >
        {$_('maturity.milestone_card.dismiss')}
      </button>
    </div>
  {/if}

  <button class="stage__text-button" type="button" on:click={() => (explainerOpen = true)}>
    {$_('maturity.journey.help_cta')}
  </button>

  <InsightJourneyExplainer open={explainerOpen} on:close={() => (explainerOpen = false)} />
</section>

<style>
  .stage {
    display: grid;
    gap: var(--space-3);
    padding: var(--space-4);
    border: 1px solid var(--color-border-chart);
    border-radius: var(--radius-md);
    background: var(--color-surface-chart-bg);
  }

  .stage__main {
    display: flex;
    gap: var(--space-3);
    align-items: flex-start;
  }

  .stage__marker {
    display: inline-flex;
    align-items: center;
    justify-content: center;
    width: 2rem;
    height: 2rem;
    flex: 0 0 auto;
    border-radius: var(--radius-full);
    background: var(--color-primary);
    color: var(--color-text-inverse);
    font-weight: 700;
  }

  .stage__copy {
    min-width: 0;
  }

  .stage__label,
  .stage__copy h2,
  .stage__copy p,
  .stage__meta p,
  .stage__milestone p {
    margin: 0;
  }

  .stage__label {
    color: var(--color-text-muted);
    font-size: var(--text-xs);
    font-weight: 700;
    text-transform: uppercase;
  }

  .stage__copy h2 {
    margin-top: var(--space-1);
    font-size: var(--text-lg);
  }

  .stage__copy p,
  .stage__meta p,
  .stage__milestone p {
    color: var(--color-text-muted);
    font-size: var(--text-sm);
    line-height: 1.45;
  }

  .stage__meta {
    display: grid;
    gap: var(--space-2);
  }

  .stage__track {
    height: 0.5rem;
    overflow: hidden;
    border-radius: var(--radius-full);
    background: color-mix(in srgb, var(--color-border) 55%, transparent);
  }

  .stage__track span {
    display: block;
    height: 100%;
    border-radius: inherit;
    background: var(--color-primary);
  }

  .stage__milestone {
    display: flex;
    justify-content: space-between;
    gap: var(--space-3);
    padding: var(--space-3);
    border: 1px solid color-mix(in srgb, var(--color-primary) 25%, var(--color-border));
    border-radius: var(--radius-sm);
    background: color-mix(in srgb, var(--color-primary) 8%, transparent);
  }

  .stage__text-button {
    justify-self: start;
    color: var(--color-primary);
    font-size: var(--text-sm);
    font-weight: 700;
    text-decoration: underline;
    text-underline-offset: 2px;
  }

  @media (min-width: 48rem) {
    .stage {
      grid-template-columns: minmax(0, 1.35fr) minmax(16rem, 0.65fr);
      align-items: center;
    }

    .stage__milestone,
    .stage__text-button {
      grid-column: 1 / -1;
    }
  }
</style>
