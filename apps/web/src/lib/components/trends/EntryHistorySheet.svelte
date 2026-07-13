<script lang="ts" context="module">
  import type { EntryResponse } from '$lib/api/entries';

  export interface EntryHistoryDetail {
    entry: EntryResponse;
    tags: string[];
    symptoms: { name: string; intensity: number }[];
  }
</script>

<script lang="ts">
  import { createEventDispatcher } from 'svelte';
  import { _ } from 'svelte-i18n';

  export let open = false;
  export let date = '';
  export let loading = false;
  export let error = '';
  export let details: EntryHistoryDetail[] = [];

  const dispatch = createEventDispatcher<{ close: void }>();
</script>

{#if open}
  <div
    class="entry-history"
    role="dialog"
    aria-modal="true"
    aria-labelledby="entry-history-title"
    data-testid="entry-history-sheet"
  >
    <button
      type="button"
      class="entry-history__backdrop"
      aria-label={$_('trends.history.close_aria')}
      on:click={() => dispatch('close')}
    ></button>

    <section class="entry-history__panel">
      <header class="entry-history__header">
        <div>
          <p class="entry-history__eyebrow">{$_('trends.history.eyebrow')}</p>
          <h2 id="entry-history-title">{date}</h2>
        </div>
        <button
          type="button"
          class="entry-history__close"
          aria-label={$_('trends.history.close_aria')}
          data-testid="entry-history-close"
          on:click={() => dispatch('close')}
        >
          x
        </button>
      </header>

      {#if loading}
        <p class="entry-history__muted" role="status">{$_('trends.history.loading')}</p>
      {:else if error}
        <p class="entry-history__error" role="alert">{error}</p>
      {:else if details.length === 0}
        <p class="entry-history__muted">{$_('trends.history.empty')}</p>
      {:else}
        <div class="entry-history__list">
          {#each details as detail (detail.entry.id)}
            <article class="entry-history__card">
              <dl class="entry-history__metrics">
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

              <dl class="entry-history__meta">
                <div>
                  <dt>{$_('entry.work_context_label')}</dt>
                  <dd>{$_(`entry.work_context.${detail.entry.work_context}`)}</dd>
                </div>
                <div>
                  <dt>{$_('trends.history.tags')}</dt>
                  <dd>
                    {detail.tags.length > 0 ? detail.tags.join(', ') : $_('trends.history.none')}
                  </dd>
                </div>
                <div>
                  <dt>{$_('trends.history.symptoms')}</dt>
                  <dd>
                    {#if detail.symptoms.length > 0}
                      {detail.symptoms.map((s) => `${s.name} (${s.intensity})`).join(', ')}
                    {:else}
                      {$_('trends.history.none')}
                    {/if}
                  </dd>
                </div>
                <div>
                  <dt>{$_('entry.section.note')}</dt>
                  <dd>{detail.entry.note || $_('trends.history.none')}</dd>
                </div>
              </dl>
            </article>
          {/each}
        </div>
      {/if}
    </section>
  </div>
{/if}

<style>
  .entry-history {
    position: fixed;
    inset: 0;
    z-index: 60;
    display: flex;
    align-items: flex-end;
    justify-content: center;
  }

  .entry-history__backdrop {
    position: absolute;
    inset: 0;
    background: var(--color-scrim);
  }

  .entry-history__panel {
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

  .entry-history__header {
    display: flex;
    align-items: flex-start;
    justify-content: space-between;
    gap: var(--space-3);
    margin-bottom: var(--space-4);
  }

  .entry-history__eyebrow {
    margin: 0 0 var(--space-1);
    font-size: var(--text-xs);
    color: var(--color-text-muted);
    text-transform: uppercase;
    letter-spacing: 0.04em;
  }

  .entry-history__header h2 {
    margin: 0;
    font-size: var(--text-xl);
  }

  .entry-history__close {
    min-width: 44px;
    min-height: 44px;
    border-radius: var(--radius-full);
    color: var(--color-text-muted);
    font-size: 1.5rem;
  }

  .entry-history__list {
    display: flex;
    flex-direction: column;
    gap: var(--space-3);
  }

  .entry-history__card {
    padding: var(--space-3);
    border-radius: var(--radius-lg);
    border: 1px solid oklch(from var(--color-text) l c h / 0.08);
    background: var(--color-surface-offset);
  }

  .entry-history__metrics {
    display: grid;
    grid-template-columns: repeat(3, minmax(0, 1fr));
    gap: var(--space-2);
    margin: 0 0 var(--space-3);
  }

  .entry-history__metrics div,
  .entry-history__meta div {
    display: flex;
    flex-direction: column;
    gap: 0.15rem;
  }

  .entry-history__metrics dt,
  .entry-history__meta dt {
    font-size: var(--text-xs);
    color: var(--color-text-muted);
  }

  .entry-history__metrics dd,
  .entry-history__meta dd {
    margin: 0;
  }

  .entry-history__metrics dd {
    font-size: var(--text-xl);
    font-weight: 700;
  }

  .entry-history__meta {
    display: grid;
    gap: var(--space-2);
    margin: 0;
    font-size: var(--text-sm);
  }

  .entry-history__muted {
    color: var(--color-text-muted);
  }

  .entry-history__error {
    color: var(--color-error);
  }

  @media (min-width: 768px) {
    .entry-history {
      align-items: center;
      padding: var(--space-6);
    }

    .entry-history__panel {
      border-radius: var(--radius-xl);
    }
  }
</style>
