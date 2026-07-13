<script lang="ts">
  import { createEventDispatcher } from 'svelte';
  import { _ } from 'svelte-i18n';
  import BottomSheet from '$lib/components/common/BottomSheet.svelte';
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

{#if selected}
  <BottomSheet
    {open}
    labelledBy="habit-sheet-title"
    testId="habit-detail-sheet"
    closeAriaLabel={$_('habits.sheet_close')}
    on:close={() => dispatch('close')}
  >
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
  </BottomSheet>
{/if}

<style>
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
    font-size: var(--text-lg);
  }

  .habit-sheet__close {
    min-width: 44px;
    min-height: 44px;
    border-radius: var(--radius-full);
    color: var(--color-text-muted);
    font-size: var(--text-xl);
  }
</style>
