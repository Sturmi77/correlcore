<script lang="ts">
  import { createEventDispatcher } from 'svelte';
  import { _ } from 'svelte-i18n';
  import HelpCircle from 'lucide-svelte/icons/help-circle';
  import type { InsightMaturity, InsightMaturityPhase } from '$lib/api/insights';
  import IconButton from '$lib/components/common/IconButton.svelte';
  import { maturityMilestoneKey } from '$lib/utils/insightMaturityMilestones';
  import InsightJourneyExplainer from './InsightJourneyExplainer.svelte';

  export let maturity: InsightMaturity;
  export let showMilestone = false;
  /** When true, render only the dismissible milestone strip (mobile lead). */
  export let milestoneOnly = false;

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
</script>

<section
  class="stage"
  class:stage--milestone-only={milestoneOnly}
  data-testid="insight-stage-header"
  data-phase={maturity.phase}
  aria-label={$_('insights.stage.aria_label')}
>
  {#if !milestoneOnly}
    <div class="stage__row">
      <div class="stage__status">
        <span class="stage__marker" aria-hidden="true">{maturity.phase_index}/4</span>
        <div class="stage__copy">
          <p class="stage__label">{$_('insights.stage.readiness_label')}</p>
          <p class="stage__line" data-testid="insight-stage-meta">
            <strong>{phaseLabel}</strong>
            <span aria-hidden="true"> · </span>
            {#if maturity.phase === 'robust'}
              {$_('maturity.journey.robust_meta', {
                values: { current: maturity.current_entries },
              })}
            {:else}
              {$_('maturity.journey.compact_entries_until_next', {
                values: {
                  current: maturity.current_entries,
                  next: maturity.next_phase_at ?? maturity.current_entries,
                  remaining: maturity.entries_until_next ?? 0,
                  nextPhase: maturity.next_phase_label ?? '',
                },
              })}
            {/if}
          </p>
        </div>
      </div>

      <div class="stage__controls">
        <div
          class="stage__track"
          role="meter"
          aria-valuemin={0}
          aria-valuemax={100}
          aria-valuenow={fillPercent}
          aria-label={$_('maturity.journey.progress_aria')}
          title={phaseDescription}
        >
          <span style={`width: ${fillPercent}%`}></span>
        </div>
        <IconButton
          ariaLabel={$_('maturity.journey.help_cta')}
          title={$_('maturity.journey.help_cta')}
          size="sm"
          variant="ghost"
          data-testid="insight-stage-help"
          on:click={() => (explainerOpen = true)}
        >
          <HelpCircle size={18} aria-hidden="true" />
        </IconButton>
      </div>
    </div>
  {/if}

  {#if showMilestone && milestoneKey}
    <div
      class="stage__milestone"
      data-testid="insight-stage-milestone"
      role="status"
      aria-label={milestoneTitle}
    >
      <span>{milestoneTitle}</span>
      <button
        type="button"
        class="stage__text-button"
        on:click={() => dispatch('dismissMilestone', { key: milestoneKey ?? '' })}
      >
        {$_('maturity.milestone_card.dismiss')}
      </button>
    </div>
  {/if}

  <InsightJourneyExplainer open={explainerOpen} on:close={() => (explainerOpen = false)} />
</section>

<style>
  .stage {
    display: flex;
    flex-direction: column;
    gap: var(--space-2);
    padding: var(--space-2) var(--space-3);
    border: 1px solid var(--color-border-chart);
    border-radius: var(--radius-md);
    background: var(--color-surface-chart-bg);
  }

  .stage--milestone-only {
    padding: 0;
    border: none;
    background: transparent;
  }

  .stage__row,
  .stage__status,
  .stage__controls,
  .stage__milestone {
    display: flex;
    align-items: center;
    gap: var(--space-2);
  }

  .stage__row {
    justify-content: space-between;
    min-width: 0;
  }

  .stage__status {
    min-width: 0;
  }

  .stage__marker {
    display: inline-flex;
    align-items: center;
    justify-content: center;
    min-width: 2.35rem;
    min-height: 1.6rem;
    flex: 0 0 auto;
    border-radius: var(--radius-full);
    background: var(--color-primary);
    color: var(--color-text-inverse);
    font-size: var(--text-xs);
    font-weight: 700;
  }

  .stage__copy {
    min-width: 0;
  }

  .stage__label,
  .stage__line,
  .stage__milestone {
    margin: 0;
  }

  .stage__label {
    color: var(--color-text-muted);
    font-size: var(--text-xs);
    font-weight: 700;
    text-transform: uppercase;
  }

  .stage__line,
  .stage__milestone {
    color: var(--color-text-muted);
    font-size: var(--text-xs);
    line-height: 1.35;
  }

  .stage__line strong {
    color: var(--color-text);
    font-weight: 700;
  }

  .stage__controls {
    flex: 0 0 auto;
  }

  .stage__track {
    width: 4.5rem;
    height: 0.35rem;
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
    justify-content: space-between;
    padding: var(--space-1) var(--space-2);
    border: 1px solid color-mix(in srgb, var(--color-primary) 25%, var(--color-border));
    border-radius: var(--radius-full);
    background: color-mix(in srgb, var(--color-primary) 8%, transparent);
  }

  .stage__text-button {
    min-height: 44px;
    flex: 0 0 auto;
    color: var(--color-primary);
    font-size: var(--text-xs);
    font-weight: 700;
    text-decoration: underline;
    text-underline-offset: 2px;
  }

  @media (max-width: 767px) {
    .stage {
      gap: var(--space-1);
      padding: var(--space-1) var(--space-2);
    }

    .stage__marker {
      min-width: 2rem;
      min-height: 1.4rem;
    }

    .stage__track {
      width: 3rem;
    }
  }

  @media (max-width: 420px) {
    .stage__row {
      align-items: flex-start;
    }

    .stage__controls {
      flex-direction: column-reverse;
      align-items: flex-end;
    }

    .stage__track {
      width: 3rem;
    }
  }
</style>
