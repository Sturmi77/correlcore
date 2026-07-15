<script lang="ts">
  import { _ } from 'svelte-i18n';

  export let marker: string | null = null;
  export let sampleSize = 0;
  export let confidence: number | null = null;
  export let avgDelta: number | null = null;
  export let exampleDates: string[] = [];
</script>

{#if marker && sampleSize > 0}
  <div class="note-evidence" data-testid="insight-note-evidence">
    <p class="note-evidence__lead">
      {$_('insights.note_evidence.lead', {
        values: {
          marker: $_(`entry.note_markers.${marker}`, { default: marker }),
          delta: avgDelta ?? 0,
        },
      })}
    </p>
    <p class="note-evidence__meta">
      {$_('insights.note_evidence.meta', {
        values: {
          days: sampleSize,
          confidence: confidence ?? 0,
        },
      })}
    </p>
    {#if exampleDates.length > 0}
      <p class="note-evidence__examples">
        {$_('insights.note_evidence.examples', { values: { dates: exampleDates.join(', ') } })}
      </p>
    {/if}
  </div>
{/if}

<style>
  .note-evidence {
    margin-top: var(--space-2);
    padding: var(--space-2) var(--space-3);
    border-radius: var(--radius-sm);
    border: 1px solid color-mix(in srgb, var(--color-primary) 20%, var(--color-border));
    background: color-mix(in srgb, var(--color-primary) 6%, var(--color-surface));
    font-size: var(--text-sm);
    line-height: 1.45;
  }

  .note-evidence__lead {
    margin: 0;
    font-weight: 600;
  }

  .note-evidence__meta,
  .note-evidence__examples {
    margin: var(--space-1) 0 0;
    color: var(--color-text-muted);
    font-size: var(--text-xs);
  }
</style>
