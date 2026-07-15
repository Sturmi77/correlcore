<script lang="ts">
  import { createEventDispatcher } from 'svelte';
  import { _, locale } from 'svelte-i18n';
  import { signalConfidenceBand } from '$lib/api/noteSignals';

  export let marker: string | null = null;
  export let signal: string | null = null;
  export let sampleSize = 0;
  export let confidence: number | null = null;
  export let avgDelta: number | null = null;
  export let exampleDates: string[] = [];
  /** When true, example dates link to /entries/day/{date}. */
  export let linkExampleDates = true;

  const dispatch = createEventDispatcher<{ selectDate: { date: string } }>();

  $: hasEvidence = Boolean((marker || signal) && sampleSize > 0);
  $: confidenceBand = confidence === null ? null : signalConfidenceBand(confidence);
  $: confidenceLabel =
    confidenceBand === null ? '' : $_(`insights.note_evidence.confidence_${confidenceBand}`);

  function formatExampleDate(isoDate: string): string {
    if (!/^\d{4}-\d{2}-\d{2}$/.test(isoDate)) return isoDate;
    const parsed = new Date(`${isoDate}T12:00:00`);
    if (Number.isNaN(parsed.getTime())) return isoDate;
    return new Intl.DateTimeFormat($locale ?? undefined, {
      day: 'numeric',
      month: 'long',
    }).format(parsed);
  }

  function subjectLabel(): string {
    if (marker) {
      return $_(`entry.note_markers.${marker}`, { default: marker });
    }
    if (signal) {
      return $_(`entry.note_signals.${signal}`, { default: signal });
    }
    return '';
  }

  function handleDateClick(event: MouseEvent, isoDate: string): void {
    if (!linkExampleDates) return;
    if (event.metaKey || event.ctrlKey || event.shiftKey || event.altKey) return;
    event.preventDefault();
    dispatch('selectDate', { date: isoDate });
  }
</script>

{#if hasEvidence}
  <div class="note-evidence" data-testid="insight-note-evidence">
    <p class="note-evidence__lead">
      {#if marker}
        {$_('insights.note_evidence.lead_marker', {
          values: {
            marker: subjectLabel(),
            delta: avgDelta ?? 0,
          },
        })}
      {:else}
        {$_('insights.note_evidence.lead_signal', {
          values: {
            signal: subjectLabel(),
            delta: avgDelta ?? 0,
          },
        })}
      {/if}
    </p>
    <p class="note-evidence__meta">
      {$_('insights.note_evidence.meta', {
        values: {
          days: sampleSize,
          confidence: confidenceLabel,
        },
      })}
    </p>
    {#if exampleDates.length > 0}
      <p class="note-evidence__examples">
        <span>{$_('insights.note_evidence.examples_prefix')}</span>
        {#each exampleDates as isoDate, index (isoDate)}
          {#if index > 0}<span aria-hidden="true">, </span>{/if}
          {#if linkExampleDates && /^\d{4}-\d{2}-\d{2}$/.test(isoDate)}
            <a
              class="note-evidence__date-link"
              href={`/entries/day/${isoDate}`}
              data-testid="insight-note-evidence-date"
              on:click={(event) => handleDateClick(event, isoDate)}
            >
              {formatExampleDate(isoDate)}
            </a>
          {:else}
            <span>{formatExampleDate(isoDate)}</span>
          {/if}
        {/each}
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

  .note-evidence__date-link {
    color: inherit;
    text-decoration: underline;
    text-underline-offset: 2px;
  }

  .note-evidence__date-link:hover {
    color: var(--color-primary);
  }
</style>
