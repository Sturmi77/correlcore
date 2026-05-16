<script lang="ts">
  import { createEventDispatcher } from 'svelte';
  import { _ } from 'svelte-i18n';
  import type { InsightMaturity } from '$lib/api/insights';
  import { maturityMilestoneKey } from '$lib/utils/insightMaturityMilestones';

  export let maturity: InsightMaturity;
  export let href = '/insights';

  const dispatch = createEventDispatcher<{ dismiss: { key: string } }>();

  $: milestoneKey = maturityMilestoneKey(maturity.phase);
  $: phaseLabel = $_(`maturity.${maturity.phase}.label`);
  $: title = $_(`maturity.milestone_card.${maturity.phase}.title`);
  $: body = $_(`maturity.milestone_card.${maturity.phase}.body`, {
    values: { n: maturity.current_entries },
  });
</script>

{#if milestoneKey}
  <section
    class="milestone-card"
    data-testid="insight-phase-milestone-card"
    data-phase={maturity.phase}
    aria-label={title}
  >
    <div class="milestone-card__content">
      <p class="milestone-card__eyebrow">
        {$_('maturity.milestone_card.eyebrow', { values: { label: phaseLabel } })}
      </p>
      <h2>{title}</h2>
      <p>{body}</p>
      <a class="milestone-card__link" {href}>
        {$_('maturity.milestone_card.cta')}
      </a>
    </div>
    <button
      class="milestone-card__dismiss"
      type="button"
      aria-label={$_('maturity.milestone_card.dismiss')}
      on:click={() => dispatch('dismiss', { key: milestoneKey ?? '' })}
    >
      {$_('maturity.milestone_card.dismiss')}
    </button>
  </section>
{/if}

<style>
  .milestone-card {
    display: flex;
    flex-direction: column;
    gap: var(--space-3);
    padding: var(--space-4);
    border: 1px solid color-mix(in srgb, var(--color-primary) 28%, var(--color-border));
    border-radius: var(--radius-lg);
    background:
      linear-gradient(
        135deg,
        color-mix(in srgb, var(--color-primary) 14%, transparent),
        transparent 55%
      ),
      var(--color-surface);
    color: var(--color-text);
    box-shadow: var(--shadow-sm);
  }

  .milestone-card__content {
    display: flex;
    flex-direction: column;
    gap: var(--space-2);
  }

  .milestone-card__eyebrow,
  .milestone-card h2,
  .milestone-card p {
    margin: 0;
  }

  .milestone-card__eyebrow {
    color: var(--color-primary);
    font-size: var(--text-xs);
    font-weight: 700;
    letter-spacing: 0.03em;
    text-transform: uppercase;
  }

  .milestone-card h2 {
    font-size: var(--text-base);
    font-weight: 700;
  }

  .milestone-card p {
    color: var(--color-text-muted);
    font-size: var(--text-sm);
    line-height: 1.5;
  }

  .milestone-card__link,
  .milestone-card__dismiss {
    align-self: flex-start;
    color: var(--color-primary);
    font-size: var(--text-sm);
    font-weight: 700;
    text-decoration: underline;
    text-underline-offset: 2px;
  }

  .milestone-card__dismiss {
    color: var(--color-text-muted);
  }

  @media (min-width: 48rem) {
    .milestone-card {
      flex-direction: row;
      align-items: flex-start;
      justify-content: space-between;
    }

    .milestone-card__dismiss {
      flex-shrink: 0;
    }
  }

  @media (prefers-reduced-motion: reduce) {
    .milestone-card {
      transition: none;
    }
  }
</style>
