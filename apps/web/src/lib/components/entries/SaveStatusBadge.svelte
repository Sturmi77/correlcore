<script lang="ts">
  /**
   * SaveStatusBadge — visualises the auto-save state machine
   * from ADR-0013 next to the page headline.
   *
   * Status mapping (per ADR-0013):
   *   idle    → invisible (nothing to report yet)
   *   dirty   → "Wird in Kürze gespeichert…"
   *   saving  → "Wird gespeichert…"
   *   saved   → "Gespeichert um HH:MM"
   *   error   → "Fehler beim Speichern. Erneut versuchen?" + retry button
   *
   * The badge wires `aria-live="polite"` so screen readers narrate
   * the transitions without interrupting the user mid-input.
   */

  import { _ } from 'svelte-i18n';
  import type { AutoSaveStatus } from '$lib/utils/autoSave';

  export let status: AutoSaveStatus = 'idle';
  export let lastSavedAt: number | null = null;
  export let lastError: string | null = null;
  export let onRetry: (() => void) | null = null;
  export let testId = 'save-status';

  function formatTime(ts: number | null): string {
    if (ts === null) return '';
    const d = new Date(ts);
    const hh = String(d.getHours()).padStart(2, '0');
    const mm = String(d.getMinutes()).padStart(2, '0');
    return `${hh}:${mm}`;
  }

  $: tone = status; // map status to CSS class
</script>

{#if status !== 'idle'}
  <div
    class="save-status save-status--{tone}"
    role="status"
    aria-live="polite"
    data-testid={testId}
    data-status={status}
  >
    {#if status === 'dirty'}
      <span class="save-status__dot" aria-hidden="true"></span>
      <span class="save-status__text">{$_('entry.autosave.dirty')}</span>
    {:else if status === 'saving'}
      <span class="save-status__spinner" aria-hidden="true"></span>
      <span class="save-status__text">{$_('entry.autosave.saving')}</span>
    {:else if status === 'saved'}
      <span class="save-status__check" aria-hidden="true">✓</span>
      <span class="save-status__text">
        {$_('entry.autosave.saved_at', { values: { time: formatTime(lastSavedAt) } })}
      </span>
    {:else if status === 'error'}
      <span class="save-status__warn" aria-hidden="true">!</span>
      <span class="save-status__text">{$_('entry.autosave.error')}</span>
      {#if lastError}
        <span class="save-status__detail">{lastError}</span>
      {/if}
      {#if onRetry}
        <button
          type="button"
          class="save-status__retry"
          on:click={onRetry}
          data-testid="{testId}-retry"
        >
          {$_('entry.autosave.retry')}
        </button>
      {/if}
    {/if}
  </div>
{/if}

<style>
  .save-status {
    display: inline-flex;
    align-items: center;
    gap: 0.4rem;
    font-size: var(--text-xs, 0.78rem);
    line-height: 1.2;
    padding: 0.2rem 0.55rem;
    border-radius: 999px;
    border: 1px solid transparent;
    background: rgb(var(--color-surface-200, 230 230 235) / 0.6);
    color: rgb(var(--color-surface-900, 17 24 39));
    white-space: nowrap;
  }

  .save-status--dirty {
    color: rgb(var(--color-warning-600, 217 119 6));
    background: rgb(var(--color-warning-500, 245 158 11) / 0.1);
    border-color: rgb(var(--color-warning-500, 245 158 11) / 0.25);
  }

  .save-status--saving {
    color: rgb(var(--color-primary-600, 37 99 235));
    background: color-mix(in srgb, var(--color-primary) 10%, transparent);
    border-color: color-mix(in srgb, var(--color-primary) 25%, transparent);
  }

  .save-status--saved {
    color: rgb(var(--color-success-600, 22 163 74));
    background: rgb(var(--color-success-500, 34 197 94) / 0.1);
    border-color: rgb(var(--color-success-500, 34 197 94) / 0.25);
  }

  .save-status--error {
    color: rgb(var(--color-error-600, 220 38 38));
    background: rgb(var(--color-error-500, 239 68 68) / 0.1);
    border-color: rgb(var(--color-error-500, 239 68 68) / 0.3);
    flex-wrap: wrap;
  }

  .save-status__dot {
    width: 0.5rem;
    height: 0.5rem;
    border-radius: 50%;
    background: currentColor;
    opacity: 0.7;
  }

  .save-status__check,
  .save-status__warn {
    font-weight: 700;
  }

  .save-status__spinner {
    width: 0.7rem;
    height: 0.7rem;
    border-radius: 50%;
    border: 2px solid currentColor;
    border-right-color: transparent;
    animation: save-status-spin 0.7s linear infinite;
  }

  @keyframes save-status-spin {
    to {
      transform: rotate(360deg);
    }
  }

  .save-status__detail {
    font-size: 0.7rem;
    opacity: 0.75;
    max-width: 16ch;
    overflow: hidden;
    text-overflow: ellipsis;
  }

  .save-status__retry {
    font: inherit;
    color: inherit;
    background: transparent;
    border: 1px solid currentColor;
    border-radius: 999px;
    padding: 0.05rem 0.5rem;
    cursor: pointer;
  }

  .save-status__retry:hover {
    background: currentColor;
    color: white;
  }

  @media (prefers-reduced-motion: reduce) {
    .save-status__spinner {
      animation: none;
    }
  }
</style>
