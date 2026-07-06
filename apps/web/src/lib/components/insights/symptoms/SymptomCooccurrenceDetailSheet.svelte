<script lang="ts">
  import { createEventDispatcher } from 'svelte';
  import { _ } from 'svelte-i18n';
  import type {
    SymptomTagCooccurrenceCell,
    SymptomTagCooccurrenceConfounder,
  } from '$lib/api/insights';

  export let open = false;
  export let cell: SymptomTagCooccurrenceCell | null = null;

  const dispatch = createEventDispatcher<{ close: void; openDisclaimer: void }>();

  function confounderNoteKey(confounder: SymptomTagCooccurrenceConfounder | null): string | null {
    if (confounder === 'weekday') return 'insights.weekday_confounded_note';
    if (confounder === 'work_context') return 'insights.work_context_confounded_note';
    if (confounder === 'calendar_context') return 'insights.calendar_context_confounded_note';
    return null;
  }

  $: confounderNote = cell ? confounderNoteKey(cell.confounder) : null;
</script>

{#if open && cell}
  <div
    class="symptom-detail"
    role="dialog"
    aria-modal="true"
    aria-labelledby="symptom-detail-title"
    data-testid="symptom-cooccurrence-detail-sheet"
  >
    <button
      type="button"
      class="symptom-detail__backdrop"
      aria-label={$_('trends.history.close_aria')}
      on:click={() => dispatch('close')}
    ></button>

    <section class="symptom-detail__panel">
      <header class="symptom-detail__header">
        <div>
          <p class="symptom-detail__eyebrow">{$_('insights.symptoms.detail_eyebrow')}</p>
          <h2 id="symptom-detail-title">
            {cell.symptom.name} + {cell.tag.name}
          </h2>
        </div>
        <button
          type="button"
          class="symptom-detail__close"
          aria-label={$_('trends.history.close_aria')}
          data-testid="symptom-cooccurrence-detail-close"
          on:click={() => dispatch('close')}
        >
          ×
        </button>
      </header>

      {#if confounderNote}
        <p class="symptom-detail__confounder">{$_(confounderNote)}</p>
      {/if}

      <dl class="symptom-detail__metrics">
        <div>
          <dt>{$_('insights.symptoms.detail_lift')}</dt>
          <dd>{cell.lift.toFixed(2)}</dd>
        </div>
        <div>
          <dt>{$_('insights.symptoms.detail_phi')}</dt>
          <dd>{cell.phi.toFixed(3)}</dd>
        </div>
        <div>
          <dt>{$_('insights.symptoms.detail_jaccard')}</dt>
          <dd>{cell.jaccard.toFixed(3)}</dd>
        </div>
        <div>
          <dt>{$_('insights.symptoms.detail_co_count')}</dt>
          <dd>{cell.co_count}</dd>
        </div>
        <div>
          <dt>{$_('insights.symptoms.detail_symptom_days')}</dt>
          <dd>{cell.symptom_count}</dd>
        </div>
        <div>
          <dt>{$_('insights.symptoms.detail_tag_days')}</dt>
          <dd>{cell.tag_count}</dd>
        </div>
        <div>
          <dt>{$_('insights.symptoms.detail_total_days')}</dt>
          <dd>{cell.total_count}</dd>
        </div>
      </dl>

      <p class="symptom-detail__base-rate">
        {$_('insights.symptoms.detail_base_rate', {
          values: {
            co: cell.co_count,
            symptom: cell.symptom_count,
            tag: cell.tag_count,
          },
        })}
      </p>

      <button
        type="button"
        class="symptom-detail__methodology"
        data-testid="symptom-cooccurrence-detail-methodology"
        on:click={() => dispatch('openDisclaimer')}
      >
        {$_('insights.symptoms.detail_methodology')}
      </button>
    </section>
  </div>
{/if}

<style>
  .symptom-detail {
    position: fixed;
    inset: 0;
    z-index: 60;
    display: grid;
    place-items: end center;
    padding: var(--space-4);
  }

  .symptom-detail__backdrop {
    position: absolute;
    inset: 0;
    border: none;
    background: color-mix(in srgb, var(--color-surface-inverse, #000) 45%, transparent);
    cursor: pointer;
  }

  .symptom-detail__panel {
    position: relative;
    width: min(100%, 28rem);
    max-height: min(85vh, 32rem);
    overflow: auto;
    padding: var(--space-4);
    border-radius: var(--radius-lg);
    border: 1px solid var(--color-border);
    background: var(--color-surface);
    box-shadow: var(--shadow-lg, 0 12px 40px rgb(0 0 0 / 0.18));
  }

  .symptom-detail__header {
    display: flex;
    justify-content: space-between;
    gap: var(--space-3);
    align-items: flex-start;
  }

  .symptom-detail__eyebrow {
    margin: 0;
    color: var(--color-text-muted);
    font-size: var(--text-xs);
    text-transform: uppercase;
    letter-spacing: 0.04em;
  }

  .symptom-detail__header h2 {
    margin: var(--space-1) 0 0;
    font-size: var(--text-lg);
  }

  .symptom-detail__close {
    border: none;
    background: none;
    font-size: 1.25rem;
    line-height: 1;
    cursor: pointer;
    color: var(--color-text-muted);
  }

  .symptom-detail__confounder {
    margin: var(--space-3) 0 0;
    color: var(--color-text-muted);
    font-size: var(--text-sm);
  }

  .symptom-detail__metrics {
    display: grid;
    grid-template-columns: repeat(2, minmax(0, 1fr));
    gap: var(--space-3);
    margin: var(--space-4) 0 0;
  }

  .symptom-detail__metrics dt {
    margin: 0;
    color: var(--color-text-muted);
    font-size: var(--text-xs);
  }

  .symptom-detail__metrics dd {
    margin: var(--space-1) 0 0;
    font-size: var(--text-base);
    font-weight: 700;
  }

  .symptom-detail__base-rate,
  .symptom-detail__methodology {
    margin: var(--space-4) 0 0;
    font-size: var(--text-sm);
  }

  .symptom-detail__base-rate {
    color: var(--color-text-muted);
  }

  .symptom-detail__methodology {
    border: none;
    background: none;
    padding: 0;
    color: var(--color-primary);
    font-weight: 600;
    cursor: pointer;
    text-align: left;
  }
</style>
