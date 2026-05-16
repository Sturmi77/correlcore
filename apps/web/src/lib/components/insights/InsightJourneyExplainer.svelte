<script lang="ts">
  import { createEventDispatcher } from 'svelte';
  import { _ } from 'svelte-i18n';

  export let open = false;

  const dispatch = createEventDispatcher<{ close: void }>();

  const phases = ['collecting', 'early_patterns', 'provisional', 'robust'] as const;

  function close() {
    dispatch('close');
  }
</script>

{#if open}
  <div class="journey-explainer" role="presentation" data-testid="insight-journey-explainer">
    <button
      class="journey-explainer__backdrop"
      type="button"
      aria-label={$_('maturity.explainer.close')}
      on:click={close}
    ></button>
    <section
      class="journey-explainer__sheet"
      role="dialog"
      aria-modal="true"
      aria-labelledby="insight-journey-explainer-title"
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

      <button class="btn btn-sm variant-filled-primary" type="button" on:click={close}>
        {$_('maturity.explainer.close')}
      </button>
    </section>
  </div>
{/if}

<style>
  .journey-explainer {
    position: fixed;
    inset: 0;
    z-index: 60;
    display: flex;
    align-items: flex-end;
    justify-content: center;
  }

  .journey-explainer__backdrop {
    position: absolute;
    inset: 0;
    background: color-mix(in oklch, var(--color-bg) 35%, black);
    opacity: 0.72;
  }

  .journey-explainer__sheet {
    position: relative;
    z-index: 1;
    width: min(100%, 42rem);
    max-height: min(86dvh, 42rem);
    overflow: auto;
    display: flex;
    flex-direction: column;
    gap: var(--space-4);
    padding: var(--space-5);
    border: 1px solid var(--color-border);
    border-radius: var(--radius-xl) var(--radius-xl) 0 0;
    background: var(--color-surface);
    color: var(--color-text);
    box-shadow: var(--shadow-lg);
  }

  .journey-explainer__header {
    display: flex;
    align-items: flex-start;
    justify-content: space-between;
    gap: var(--space-4);
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
    width: 2rem;
    height: 2rem;
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

  .journey-explainer__phases {
    display: flex;
    flex-direction: column;
    gap: var(--space-3);
    padding: 0;
    margin: 0;
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

  @media (min-width: 48rem) {
    .journey-explainer {
      align-items: center;
      padding: var(--space-6);
    }

    .journey-explainer__sheet {
      border-radius: var(--radius-xl);
    }
  }
</style>
