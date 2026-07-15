<script lang="ts">
  import { _ } from 'svelte-i18n';
  import type { EntryNoteSignalResponse } from '$lib/api/noteSignals';
  import { signalConfidenceBand } from '$lib/api/noteSignals';

  export let signals: EntryNoteSignalResponse[] = [];
  export let limit = 5;
</script>

{#if signals.length > 0}
  <div class="note-signals" data-testid="entry-note-signals">
    <p class="note-signals__heading">{$_('entry.note_signals.heading')}</p>
    <ul class="note-signals__list">
      {#each signals.slice(0, limit) as item (item.id)}
        <li class="note-signals__item">
          <span class="note-signals__label">
            {$_(`entry.note_signals.${item.signal}`, { default: item.signal })}
          </span>
          <span
            class="note-signals__confidence"
            data-band={signalConfidenceBand(item.confidence)}
            title={item.source_span ?? ''}
          >
            {$_(`insights.note_evidence.confidence_${signalConfidenceBand(item.confidence)}`)}
          </span>
        </li>
      {/each}
    </ul>
  </div>
{/if}

<style>
  .note-signals {
    margin-top: var(--space-2);
  }

  .note-signals__heading {
    margin: 0 0 var(--space-1);
    font-size: var(--text-xs);
    font-weight: 600;
    color: var(--color-text-muted);
    text-transform: uppercase;
    letter-spacing: 0.04em;
  }

  .note-signals__list {
    margin: 0;
    padding: 0;
    list-style: none;
    display: flex;
    flex-direction: column;
    gap: var(--space-1);
  }

  .note-signals__item {
    display: flex;
    align-items: center;
    justify-content: space-between;
    gap: var(--space-2);
    font-size: var(--text-sm);
  }

  .note-signals__confidence {
    font-size: var(--text-xs);
    color: var(--color-text-muted);
  }

  .note-signals__confidence[data-band='high'] {
    color: var(--color-success, var(--color-primary));
  }
</style>
