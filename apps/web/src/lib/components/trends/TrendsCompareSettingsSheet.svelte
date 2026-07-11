<script lang="ts">
  import { createEventDispatcher } from 'svelte';
  import { _ } from 'svelte-i18n';
  import type { TagCategory } from '$lib/api/tags';
  import type { MetricKey } from '$lib/utils/charts';
  import type { CompareMode, CompareSortMode } from '$lib/utils/comparePanelSettings';
  import TrendsCompareFilters from './TrendsCompareFilters.svelte';

  export let open = false;
  export let smoothing = false;
  export let smoothingAvailable = false;
  export let metrics: Record<MetricKey, boolean>;
  export let selectedCategory: TagCategory | 'all' = 'all';
  export let showTags = true;
  export let showSymptoms = false;
  export let showWorkContexts = true;
  export let mode: CompareMode = 'lines';
  export let sortMode: CompareSortMode = 'frequency';

  const dispatch = createEventDispatcher<{
    close: void;
    smoothingChange: { value: boolean };
    metricToggle: { metric: MetricKey };
    categoryChange: { category: TagCategory | 'all' };
    layerChange: { showTags: boolean; showSymptoms: boolean; showWorkContexts: boolean };
    modeChange: { value: CompareMode };
    sortChange: { value: CompareSortMode };
  }>();
</script>

{#if open}
  <div
    class="compare-settings"
    role="dialog"
    aria-modal="true"
    aria-labelledby="compare-settings-title"
    data-testid="trends-compare-settings-sheet"
  >
    <button
      type="button"
      class="compare-settings__backdrop"
      aria-label={$_('trends.settings.close_aria')}
      on:click={() => dispatch('close')}
    ></button>

    <section class="compare-settings__panel">
      <header class="compare-settings__header">
        <div>
          <p class="compare-settings__eyebrow">{$_('trends.tabs.compare')}</p>
          <h2 id="compare-settings-title">{$_('trends.settings.title')}</h2>
        </div>
        <button
          type="button"
          class="compare-settings__close"
          aria-label={$_('trends.settings.close_aria')}
          data-testid="trends-compare-settings-close"
          on:click={() => dispatch('close')}
        >
          ×
        </button>
      </header>

      <div class="compare-settings__body">
        <TrendsCompareFilters
          {smoothing}
          {smoothingAvailable}
          {metrics}
          {selectedCategory}
          on:smoothingChange={(event) => dispatch('smoothingChange', event.detail)}
          on:metricToggle={(event) => dispatch('metricToggle', event.detail)}
          on:categoryChange={(event) => dispatch('categoryChange', event.detail)}
        />

        <fieldset class="compare-settings__layers">
          <legend>{$_('trends.compare.layers')}</legend>
          <label>
            <input
              type="checkbox"
              checked={showTags}
              on:change={(event) =>
                dispatch('layerChange', {
                  showTags: event.currentTarget.checked,
                  showSymptoms,
                  showWorkContexts,
                })}
            />
            {$_('trends.compare.tags')}
          </label>
          <label>
            <input
              type="checkbox"
              checked={showSymptoms}
              on:change={(event) =>
                dispatch('layerChange', {
                  showTags,
                  showSymptoms: event.currentTarget.checked,
                  showWorkContexts,
                })}
            />
            {$_('trends.compare.symptoms')}
          </label>
          <label>
            <input
              type="checkbox"
              checked={showWorkContexts}
              on:change={(event) =>
                dispatch('layerChange', {
                  showTags,
                  showSymptoms,
                  showWorkContexts: event.currentTarget.checked,
                })}
            />
            {$_('trends.compare.work_contexts')}
          </label>
        </fieldset>

        <div class="compare-settings__mode" role="group" aria-label={$_('trends.compare.mode_label')}>
          <span class="compare-settings__label">{$_('trends.compare.mode_label')}</span>
          <button
            type="button"
            class="compare-settings__chip"
            class:compare-settings__chip--active={mode === 'lines'}
            aria-pressed={mode === 'lines'}
            on:click={() => dispatch('modeChange', { value: 'lines' })}
          >
            {$_('trends.compare.mode_lines')}
          </button>
          <button
            type="button"
            class="compare-settings__chip"
            class:compare-settings__chip--active={mode === 'strips'}
            aria-pressed={mode === 'strips'}
            on:click={() => dispatch('modeChange', { value: 'strips' })}
          >
            {$_('trends.compare.mode_strips')}
          </button>
        </div>

        <label class="compare-settings__sort">
          <span class="compare-settings__label">{$_('trends.compare.sort_label')}</span>
          <select
            value={sortMode}
            on:change={(event) =>
              dispatch('sortChange', { value: event.currentTarget.value as CompareSortMode })}
          >
            <option value="frequency">{$_('trends.compare.sort_frequency')}</option>
            <option value="recent">{$_('trends.compare.sort_recent')}</option>
            <option value="correlation">{$_('trends.compare.sort_correlation')}</option>
            <option value="pinned">{$_('trends.compare.sort_pinned')}</option>
          </select>
        </label>
      </div>
    </section>
  </div>
{/if}

<style>
  .compare-settings {
    position: fixed;
    inset: 0;
    z-index: 60;
    display: flex;
    align-items: flex-end;
    justify-content: center;
  }

  .compare-settings__backdrop {
    position: absolute;
    inset: 0;
    background: oklch(0 0 0 / 0.48);
  }

  .compare-settings__panel {
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

  .compare-settings__header {
    display: flex;
    align-items: flex-start;
    justify-content: space-between;
    gap: var(--space-3);
    margin-bottom: var(--space-4);
  }

  .compare-settings__eyebrow {
    margin: 0 0 var(--space-1);
    font-size: var(--text-xs);
    color: var(--color-text-muted);
    text-transform: uppercase;
    letter-spacing: 0.04em;
  }

  .compare-settings__header h2 {
    margin: 0;
    font-size: var(--text-xl);
  }

  .compare-settings__close {
    min-width: 44px;
    min-height: 44px;
    border-radius: var(--radius-full);
    color: var(--color-text-muted);
    font-size: 1.5rem;
  }

  .compare-settings__body {
    display: grid;
    gap: var(--space-4);
  }

  .compare-settings__layers {
    display: flex;
    flex-wrap: wrap;
    gap: var(--space-2);
    margin: 0;
    padding: 0;
    border: 0;
  }

  .compare-settings__layers legend {
    width: 100%;
    color: var(--color-text-muted);
    font-size: var(--text-xs);
    font-weight: 700;
  }

  .compare-settings__layers label {
    min-height: 44px;
    display: inline-flex;
    align-items: center;
    gap: var(--space-1);
    font-size: var(--text-sm);
    font-weight: 700;
  }

  .compare-settings__mode {
    display: inline-flex;
    flex-wrap: wrap;
    align-items: center;
    gap: var(--space-1);
    background: var(--color-surface-muted, var(--color-strip-track-bg));
    border-radius: var(--radius-md, 8px);
    padding: 2px;
  }

  .compare-settings__label {
    color: var(--color-text-muted);
    font-size: var(--text-xs);
    padding: 0 var(--space-1);
  }

  .compare-settings__chip {
    background: transparent;
    border: 0;
    padding: var(--space-1) var(--space-2);
    border-radius: var(--radius-md, 8px);
    color: var(--color-text);
    cursor: pointer;
    font-size: var(--text-sm);
    font-weight: 600;
    min-height: 32px;
  }

  .compare-settings__chip--active {
    background: var(--color-surface);
    color: var(--color-fg);
    box-shadow: 0 0 0 1px var(--color-border-chart, var(--color-cursor-halo));
  }

  .compare-settings__sort {
    display: inline-flex;
    align-items: center;
    gap: var(--space-2);
    font-size: var(--text-sm);
  }

  .compare-settings__sort select {
    min-height: 44px;
    padding: var(--space-1) var(--space-2);
    border-radius: var(--radius-md, 8px);
    border: 1px solid var(--color-border, var(--color-border-chart));
    background: var(--color-surface);
    color: var(--color-text);
    font: inherit;
  }
</style>
