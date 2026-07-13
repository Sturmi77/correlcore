<script lang="ts">
  import { createEventDispatcher } from 'svelte';
  import { _ } from 'svelte-i18n';
  import type { InsightResponse } from '$lib/api/insights';

  export let insight: InsightResponse | null = null;

  const dispatch = createEventDispatcher<{ dismiss: void }>();

  $: isWorkContext =
    insight?.insight_type === 'work_context_pattern' ||
    insight?.insight_type === 'weekday_context_pattern';
  $: titleKey = isWorkContext ? 'home.context_banner.title' : 'home.first_week_banner.title';
  $: bodyKey = isWorkContext ? 'home.context_banner.body' : 'home.first_week_banner.body';
</script>

<section class="first-week-banner" data-testid="first-week-banner">
  <div class="first-week-banner__copy">
    <p class="first-week-banner__title">{$_(titleKey)}</p>
    <p class="first-week-banner__body">
      {insight?.statement ?? $_(bodyKey)}
    </p>
  </div>
  <div class="first-week-banner__actions">
    <button
      class="first-week-banner__dismiss"
      type="button"
      aria-label={$_('home.first_week_banner.dismiss')}
      on:click={() => dispatch('dismiss')}
    >
      ×
    </button>
  </div>
</section>

<style>
  .first-week-banner {
    display: flex;
    align-items: center;
    justify-content: space-between;
    gap: 1rem;
    padding: 0.85rem;
    border: 1px solid color-mix(in srgb, var(--color-primary) 20%, transparent);
    border-radius: 0.45rem;
    background: color-mix(in srgb, var(--color-primary) 8%, transparent);
  }

  .first-week-banner__copy {
    min-width: 0;
  }

  .first-week-banner__title,
  .first-week-banner__body {
    margin: 0;
  }

  .first-week-banner__title {
    font-size: var(--text-sm, 0.88rem);
    font-weight: 700;
  }

  .first-week-banner__body {
    font-size: 0.78rem;
  }

  .first-week-banner__body {
    margin-top: 0.15rem;
    color: var(--color-text-muted);
  }

  .first-week-banner__actions {
    flex: 0 0 auto;
    display: flex;
    align-items: center;
    gap: 0.5rem;
  }

  .first-week-banner__dismiss {
    width: 2rem;
    height: 2rem;
    border: 0;
    border-radius: 999px;
    background: var(--color-surface-offset);
    color: inherit;
    cursor: pointer;
    font-size: 1.1rem;
    line-height: 1;
  }

  @media (max-width: 480px) {
    .first-week-banner {
      align-items: flex-start;
      flex-direction: column;
    }

    .first-week-banner__actions {
      width: 100%;
      justify-content: space-between;
    }
  }
</style>
