<script lang="ts">
  import { _ } from 'svelte-i18n';

  /**
   * Last onboarding screen: explains the cycle-day function in its current,
   * shipped form (E5 wording — cycle day 1–35 treated as a metric, no
   * prediction/diagnosis) and lets the user switch the whole function off.
   * The choice persists as `cycle_tracking_enabled` and stays re-toggleable in
   * Settings. Scope is deliberately Stage 1 (ADR-0034): toggle only — no
   * bleeding strength / phase inference (#547 stays deferred).
   */
  export let enabled = true;
  export let headingId = 'onboarding-cycle-step-title';
</script>

<section class="cycle-step" data-testid="cycle-function-explainer" aria-labelledby={headingId}>
  <h2 id={headingId} class="cycle-step__title">{$_('onboarding.cycle_step.title')}</h2>
  <p class="cycle-step__body">{$_('onboarding.cycle_step.body')}</p>
  <p class="cycle-step__tag-hint">{$_('onboarding.cycle_step.tag_hint')}</p>

  <label class="cycle-step__toggle-label">
    <input
      type="checkbox"
      class="cycle-step__toggle"
      bind:checked={enabled}
      data-testid="cycle-onboarding-toggle"
    />
    <span>{$_('onboarding.cycle_step.toggle_label')}</span>
  </label>
  <p class="cycle-step__toggle-hint">
    {enabled
      ? $_('onboarding.cycle_step.toggle_hint_on')
      : $_('onboarding.cycle_step.toggle_hint_off')}
  </p>

  <p class="cycle-step__disclaimer">{$_('onboarding.cycle_step.disclaimer')}</p>
</section>

<style>
  .cycle-step {
    display: flex;
    flex-direction: column;
    gap: var(--space-3);
  }

  .cycle-step__title {
    margin: 0;
    font-size: var(--text-base);
    font-weight: 700;
  }

  .cycle-step__body,
  .cycle-step__tag-hint,
  .cycle-step__toggle-hint,
  .cycle-step__disclaimer {
    margin: 0;
    line-height: 1.5;
    color: var(--color-text-muted);
  }

  .cycle-step__body,
  .cycle-step__tag-hint {
    font-size: var(--text-sm);
    color: var(--color-text);
  }

  .cycle-step__tag-hint {
    padding: var(--space-3);
    border-radius: var(--radius-sm);
    background: color-mix(in srgb, var(--color-primary) 8%, transparent);
    border: 1px solid color-mix(in srgb, var(--color-primary) 18%, transparent);
  }

  .cycle-step__toggle-label {
    display: flex;
    align-items: center;
    gap: var(--space-3);
    min-height: 44px;
    padding: var(--space-3);
    border: 1px solid var(--color-border);
    border-radius: var(--radius-md);
    background: var(--color-surface);
    font-size: var(--text-sm);
    font-weight: 600;
    cursor: pointer;
  }

  .cycle-step__toggle {
    width: 1.25rem;
    height: 1.25rem;
    accent-color: var(--color-primary);
    flex-shrink: 0;
  }

  .cycle-step__toggle-hint,
  .cycle-step__disclaimer {
    font-size: var(--text-xs);
  }
</style>
