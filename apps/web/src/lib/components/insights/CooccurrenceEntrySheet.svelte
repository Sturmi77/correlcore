<script lang="ts">
  import { createEventDispatcher } from 'svelte';
  import { _ } from 'svelte-i18n';
  import type { EntryHistoryDetail } from '$lib/components/trends/EntryHistorySheet.svelte';

  export let open = false;
  export let title = '';
  export let loading = false;
  export let error = '';
  export let details: EntryHistoryDetail[] = [];

  const dispatch = createEventDispatcher<{ close: void }>();
</script>

{#if open}
  <div
    class="cooccurrence-history"
    role="dialog"
    aria-modal="true"
    aria-labelledby="cooccurrence-history-title"
    data-testid="cooccurrence-entry-sheet"
  >
    <button
      type="button"
      class="cooccurrence-history__backdrop"
      aria-label={$_('trends.history.close_aria')}
      on:click={() => dispatch('close')}
    ></button>

    <section class="cooccurrence-history__panel">
      <header class="cooccurrence-history__header">
        <div>
          <p class="cooccurrence-history__eyebrow">{$_('insights.cooccurrence.history_eyebrow')}</p>
          <h2 id="cooccurrence-history-title">{title}</h2>
        </div>
        <button
          type="button"
          class="cooccurrence-history__close"
          aria-label={$_('trends.history.close_aria')}
          data-testid="cooccurrence-entry-close"
          on:click={() => dispatch('close')}
        >
          x
        </button>
      </header>

      {#if loading}
        <p class="cooccurrence-history__muted" role="status">{$_('trends.history.loading')}</p>
      {:else if error}
        <p class="cooccurrence-history__error" role="alert">{error}</p>
      {:else if details.length === 0}
        <p class="cooccurrence-history__muted">{$_('insights.cooccurrence.history_empty')}</p>
      {:else}
        <div class="cooccurrence-history__list">
          {#each details as detail (detail.entry.id)}
            <article class="cooccurrence-history__card">
              <p class="cooccurrence-history__date">{detail.entry.entry_date}</p>
              <dl class="cooccurrence-history__metrics">
                <div>
                  <dt>{$_('trends.metric.mood')}</dt>
                  <dd>{detail.entry.mood_score}</dd>
                </div>
                <div>
                  <dt>{$_('trends.metric.energy')}</dt>
                  <dd>{detail.entry.energy}</dd>
                </div>
                <div>
                  <dt>{$_('trends.metric.stress')}</dt>
                  <dd>{detail.entry.stress}</dd>
                </div>
              </dl>
              <p class="cooccurrence-history__tags">
                {detail.tags.length > 0 ? detail.tags.join(', ') : $_('trends.history.none')}
              </p>
            </article>
          {/each}
        </div>
      {/if}
    </section>
  </div>
{/if}

<style>
  .cooccurrence-history {
    position: fixed;
    inset: 0;
    z-index: 60;
    display: flex;
    align-items: flex-end;
    justify-content: center;
  }

  .cooccurrence-history__backdrop {
    position: absolute;
    inset: 0;
    background: oklch(0 0 0 / 0.48);
  }

  .cooccurrence-history__panel {
    position: relative;
    z-index: 1;
    width: min(100%, 42rem);
    max-height: min(82vh, 42rem);
    overflow: auto;
    padding: var(--space-4);
    border-radius: var(--radius-xl) var(--radius-xl) 0 0;
    background: var(--color-surface);
    border: 1px solid var(--color-border);
    box-shadow: var(--shadow-lg);
  }

  .cooccurrence-history__header {
    display: flex;
    align-items: flex-start;
    justify-content: space-between;
    gap: var(--space-3);
    margin-bottom: var(--space-4);
  }

  .cooccurrence-history__eyebrow {
    margin: 0 0 var(--space-1);
    font-size: var(--text-xs);
    color: var(--color-text-muted);
    text-transform: uppercase;
    letter-spacing: 0.04em;
  }

  .cooccurrence-history__header h2 {
    margin: 0;
    font-size: var(--text-lg);
  }

  .cooccurrence-history__close {
    min-width: 44px;
    min-height: 44px;
    border-radius: var(--radius-full);
    color: var(--color-text-muted);
    font-size: 1.5rem;
  }

  .cooccurrence-history__list {
    display: flex;
    flex-direction: column;
    gap: var(--space-3);
  }

  .cooccurrence-history__card {
    padding: var(--space-3);
    border-radius: var(--radius-lg);
    border: 1px solid oklch(from var(--color-text) l c h / 0.08);
    background: var(--color-surface-offset);
  }

  .cooccurrence-history__date {
    margin: 0 0 var(--space-2);
    font-size: var(--text-sm);
    font-weight: 650;
    color: var(--color-text-muted);
  }

  .cooccurrence-history__metrics {
    display: grid;
    grid-template-columns: repeat(3, minmax(0, 1fr));
    gap: var(--space-2);
    margin: 0 0 var(--space-2);
  }

  .cooccurrence-history__metrics div {
    display: flex;
    flex-direction: column;
    gap: 0.15rem;
  }

  .cooccurrence-history__metrics dt {
    font-size: var(--text-xs);
    color: var(--color-text-muted);
  }

  .cooccurrence-history__metrics dd {
    margin: 0;
    font-size: var(--text-xl);
    font-weight: 700;
  }

  .cooccurrence-history__tags {
    margin: 0;
    font-size: var(--text-sm);
    color: var(--color-text-muted);
  }

  .cooccurrence-history__muted {
    color: var(--color-text-muted);
  }

  .cooccurrence-history__error {
    color: var(--color-error);
  }

  @media (min-width: 768px) {
    .cooccurrence-history {
      align-items: center;
      padding: var(--space-6);
    }

    .cooccurrence-history__panel {
      border-radius: var(--radius-xl);
    }
  }
</style>
