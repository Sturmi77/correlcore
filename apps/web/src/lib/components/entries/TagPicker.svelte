<script lang="ts">
  /**
   * TagPicker — multi-select tag chooser grouped by category (Issue #8).
   *
   * Used in the daily-entry form (/entries/new) to attach tags to a new
   * entry. The component is "dumb" with respect to persistence:
   *   - the parent passes a bound `selected` array of tag IDs
   *   - this component only emits state via two-way binding
   *
   * Loading + error handling
   * ------------------------
   * On mount we trigger a one-shot refresh of the tags store. If the
   * store is already populated (status === 'ready') we skip the fetch
   * so navigation between pages stays cheap.
   *
   * A11y
   * ----
   * Each tag chip is a `<button type="button" aria-pressed>` so screen
   * readers announce the toggle state. The category headings use h3
   * inside a labelled section for consistent structure.
   */

  import { onMount } from 'svelte';
  import { _ } from 'svelte-i18n';
  import { tags, tagsByCategory, refreshTags } from '$lib/stores/tags';
  import { TAG_CATEGORIES, MAX_TAGS_PER_ENTRY, type TagCategory } from '$lib/api/tags';

  /** Two-way bound: list of selected tag IDs. */
  export let selected: string[] = [];
  /** Disable interaction (e.g. while the parent form submits). */
  export let disabled = false;

  let loadError: string | null = null;

  onMount(async () => {
    if ($tags.status === 'ready' || $tags.status === 'loading') return;
    try {
      await refreshTags();
    } catch (err) {
      loadError = err instanceof Error ? err.message : 'load_failed';
    }
  });

  function toggle(tagId: string) {
    if (disabled) return;
    if (selected.includes(tagId)) {
      selected = selected.filter((id) => id !== tagId);
    } else {
      if (selected.length >= MAX_TAGS_PER_ENTRY) return;
      selected = [...selected, tagId];
    }
  }

  function isSelected(tagId: string, list: string[]): boolean {
    return list.includes(tagId);
  }

  // Only show categories that contain at least one tag — keeps the
  // picker compact when the user hasn't added custom tags yet in some
  // categories.
  $: visibleCategories = (TAG_CATEGORIES as readonly TagCategory[]).filter(
    (cat) => $tagsByCategory[cat].length > 0
  );

  $: atLimit = selected.length >= MAX_TAGS_PER_ENTRY;
</script>

<section class="tag-picker" aria-labelledby="tag-picker-heading">
  <div class="tag-picker-header">
    <h2 id="tag-picker-heading" class="entry-label">{$_('tag.picker_label')}</h2>
    <span class="tag-counter" aria-live="polite">
      {$_('tag.picker_counter', { values: { count: selected.length, max: MAX_TAGS_PER_ENTRY } })}
    </span>
  </div>

  {#if $tags.status === 'loading'}
    <p class="tag-status">{$_('tag.loading')}</p>
  {:else if $tags.status === 'error' || loadError}
    <p class="tag-status tag-status-error" role="alert">{$_('tag.error_load')}</p>
  {:else if $tags.status === 'ready' && visibleCategories.length === 0}
    <p class="tag-status">{$_('tag.empty')}</p>
  {:else if $tags.status === 'ready'}
    {#each visibleCategories as cat (cat)}
      <div class="tag-category">
        <h3 class="tag-category-label">{$_(`tag.category.${cat}`)}</h3>
        <div class="tag-chips">
          {#each $tagsByCategory[cat] as tag (tag.id)}
            {@const active = isSelected(tag.id, selected)}
            <button
              type="button"
              class="tag-chip"
              class:tag-chip-active={active}
              aria-pressed={active}
              disabled={disabled || (!active && atLimit)}
              on:click={() => toggle(tag.id)}
              style={tag.color ? `--tag-color: ${tag.color}` : ''}
            >
              {#if tag.icon}
                <span class="tag-icon" aria-hidden="true">{tag.icon}</span>
              {/if}
              <span class="tag-name">{tag.name}</span>
            </button>
          {/each}
        </div>
      </div>
    {/each}
  {/if}
</section>

<style>
  .tag-picker {
    display: flex;
    flex-direction: column;
    gap: var(--space-3);
  }

  .tag-picker-header {
    display: flex;
    justify-content: space-between;
    align-items: baseline;
    gap: var(--space-3);
  }

  .tag-counter {
    font-size: var(--text-xs);
    opacity: 0.7;
    font-variant-numeric: tabular-nums;
  }

  .tag-status {
    font-size: var(--text-sm);
    opacity: 0.75;
  }

  .tag-status-error {
    color: rgb(var(--color-error-500));
    opacity: 1;
  }

  .tag-category {
    display: flex;
    flex-direction: column;
    gap: var(--space-2);
  }

  .tag-category-label {
    font-size: var(--text-xs);
    font-weight: 600;
    text-transform: uppercase;
    letter-spacing: 0.05em;
    opacity: 0.7;
    margin: 0;
  }

  .tag-chips {
    display: flex;
    flex-wrap: wrap;
    gap: var(--space-2);
  }

  .tag-chip {
    display: inline-flex;
    align-items: center;
    gap: 0.4rem;
    padding: 0.35rem 0.75rem;
    border-radius: 999px;
    border: 1px solid var(--color-border, #d4d4d4);
    background: transparent;
    color: inherit;
    font-size: var(--text-sm);
    line-height: 1.2;
    cursor: pointer;
    transition:
      background 120ms ease,
      border-color 120ms ease,
      color 120ms ease;
  }

  .tag-chip:hover:not(:disabled) {
    border-color: var(--tag-color, currentColor);
  }

  .tag-chip:disabled {
    opacity: 0.45;
    cursor: not-allowed;
  }

  .tag-chip-active {
    background: var(--tag-color, rgb(var(--color-primary-500)));
    border-color: var(--tag-color, rgb(var(--color-primary-500)));
    color: #ffffff;
  }

  .tag-icon {
    font-size: 1rem;
    line-height: 1;
  }
</style>
