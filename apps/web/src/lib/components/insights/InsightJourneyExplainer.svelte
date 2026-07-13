<script lang="ts">
  import { createEventDispatcher } from 'svelte';
  import { _ } from 'svelte-i18n';
  import BottomSheet from '$lib/components/common/BottomSheet.svelte';

  export let open = false;

  const dispatch = createEventDispatcher<{ close: void }>();

  const phases = ['collecting', 'early_patterns', 'provisional', 'robust'] as const;

  function close() {
    dispatch('close');
  }
</script>

<BottomSheet
  {open}
  labelledBy="insight-journey-explainer-title"
  testId="insight-journey-explainer"
  closeAriaLabel={$_('maturity.explainer.close')}
  on:close={close}
>
  <header class="journey-explainer__header">
    <h2 id="insight-journey-explainer-title">{$_('maturity.explainer.title')}</h2>
    <button
      class="journey-explainer__close"
      type="button"
      aria-label={$_('maturity.explainer.close')}
      on:click={close}
    >
      x
    </button>
  </header>

  <p class="journey-explainer__intro">{$_('maturity.explainer.intro')}</p>

  <ol class="journey-explainer__phases">
    {#each phases as phase, index}
      <li class="journey-explainer__phase">
        <span class="journey-explainer__index">{index + 1}</span>
        <div>
          <h3>{$_(`maturity.${phase}.label`)}</h3>
          <p class="journey-explainer__range">{$_(`maturity.${phase}.range`)}</p>
          <p>{$_(`maturity.${phase}.description`)}</p>
        </div>
      </li>
    {/each}
  </ol>

  <button class="btn btn-sm btn--primary" type="button" on:click={close}>
    {$_('maturity.explainer.close')}
  </button>
</BottomSheet>

<style>
  .journey-explainer__header {
    display: flex;
    align-items: flex-start;
    justify-content: space-between;
    gap: var(--space-4);
    margin-bottom: var(--space-4);
  }

  .journey-explainer__header h2 {
    margin: 0;
    font-size: var(--text-lg);
    font-weight: 700;
  }

  .journey-explainer__close {
    display: inline-flex;
    align-items: center;
    justify-content: center;
    min-width: var(--tap-target);
    min-height: var(--tap-target);
    border-radius: var(--radius-full);
    color: var(--color-text-muted);
    background: var(--color-surface-offset);
  }

  .journey-explainer__intro,
  .journey-explainer__phase p {
    margin: 0;
    color: var(--color-text-muted);
    line-height: 1.5;
  }

  .journey-explainer__intro {
    margin-bottom: var(--space-4);
  }

  .journey-explainer__phases {
    display: flex;
    flex-direction: column;
    gap: var(--space-3);
    padding: 0;
    margin: 0 0 var(--space-4);
    list-style: none;
  }

  .journey-explainer__phase {
    display: grid;
    grid-template-columns: auto 1fr;
    gap: var(--space-3);
    padding: var(--space-3);
    border: 1px solid var(--color-border);
    border-radius: var(--radius-lg);
    background: var(--color-surface-chart-bg);
  }

  .journey-explainer__index {
    display: inline-flex;
    align-items: center;
    justify-content: center;
    width: 1.75rem;
    height: 1.75rem;
    border-radius: var(--radius-full);
    background: var(--color-primary-highlight);
    color: var(--color-primary);
    font-size: var(--text-sm);
    font-weight: 700;
  }

  .journey-explainer__phase h3 {
    margin: 0 0 var(--space-1);
    font-size: var(--text-sm);
    font-weight: 700;
  }

  .journey-explainer__range {
    font-size: var(--text-xs);
  }
</style>
