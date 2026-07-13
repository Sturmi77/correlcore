<script lang="ts">
  import { createEventDispatcher } from 'svelte';
  import { _ } from 'svelte-i18n';
  import type { HabitStatsResponse, HabitWindow } from '$lib/api/habits';
  import type { TagHeatmapResponse } from '$lib/api/stats';
  import type { TagResponse } from '$lib/api/tags';
  import HabitDetailBody from '$lib/components/trends/HabitDetailBody.svelte';

  export let open = false;
  export let selected: { habit: HabitStatsResponse; tag: TagResponse } | null = null;
  export let detailHeatmap: TagHeatmapResponse | null = null;
  export let window: HabitWindow = 28;
  export let loading = false;

  const dispatch = createEventDispatcher<{
    close: void;
    selectDate: { date: string; tagId: string };
  }>();
</script>

{#if open && selected}
  <div
    class="habit-sheet"
    role="dialog"
    aria-modal="true"
    aria-labelledby="habit-sheet-title"
    data-testid="habit-detail-sheet"
  >
    <button
      type="button"
      class="habit-sheet__backdrop"
      aria-label={$_('habits.sheet_close')}
      on:click={() => dispatch('close')}
    ></button>

    <section class="habit-sheet__panel">
      <header class="habit-sheet__header">
        <div>
          <p class="habit-sheet__eyebrow">
            {$_('habits.window_last', { values: { n: window } })}
          </p>
          <h2 id="habit-sheet-title">{selected.tag.name}</h2>
        </div>
        <button
          type="button"
          class="habit-sheet__close"
          aria-label={$_('habits.sheet_close')}
          data-testid="habit-detail-sheet-close"
          on:click={() => dispatch('close')}
        >
          ×
        </button>
      </header>

      <HabitDetailBody
        {selected}
        {detailHeatmap}
        {loading}
        on:selectDate={(event) => dispatch('selectDate', event.detail)}
      />
    </section>
  </div>
{/if}

<style>
  .habit-sheet {
    position: fixed;
    inset: 0;
    z-index: 60;
    display: flex;
    align-items: flex-end;
    justify-content: center;
  }

  .habit-sheet__backdrop {
    position: absolute;
    inset: 0;
    background: var(--color-scrim);
  }

  .habit-sheet__panel {
    position: relative;
    z-index: 1;
    width: min(100%, 42rem);
    max-height: min(88vh, 44rem);
    overflow: auto;
    padding: var(--space-4);
    border-radius: var(--radius-xl) var(--radius-xl) 0 0;
    background: var(--color-surface);
    border: 1px solid var(--color-border);
    box-shadow: var(--shadow-lg);
  }

  .habit-sheet__header {
    display: flex;
    align-items: flex-start;
    justify-content: space-between;
    gap: var(--space-3);
    margin-bottom: var(--space-4);
  }

  .habit-sheet__eyebrow {
    margin: 0 0 var(--space-1);
    font-size: var(--text-xs);
    color: var(--color-text-muted);
    text-transform: uppercase;
    letter-spacing: 0.04em;
  }

  .habit-sheet__header h2 {
    margin: 0;
    font-size: var(--text-xl);
  }

  .habit-sheet__close {
    min-width: 44px;
    min-height: 44px;
    border-radius: var(--radius-full);
    color: var(--color-text-muted);
    font-size: 1.5rem;
  }
</style>
