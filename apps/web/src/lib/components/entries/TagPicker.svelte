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
  import { tags, tagsList, tagsByCategory, refreshTags, submitTag } from '$lib/stores/tags';
  import {
    TAG_CATEGORIES,
    MAX_TAGS_PER_ENTRY,
    type TagCategory,
    type TagResponse,
  } from '$lib/api/tags';
  import { fetchTagHeatmap } from '$lib/api/stats';
  import { rankRecentTagIds } from '$lib/utils/recentTags';
  import CategoryIcon from '$lib/components/common/CategoryIcon.svelte';
  import { categoryColorForCurrentTheme } from '$lib/constants/tagDefaults';
  import { localizedCatalogName } from '$lib/utils/localizedCatalogName';

  /** Two-way bound: list of selected tag IDs. */
  export let selected: string[] = [];
  /** Disable interaction (e.g. while the parent form submits). */
  export let disabled = false;

  /**
   * "Recently used" cloud (#890 Folge 4/4, #898). A short window keeps the row
   * anchored to the person's current life phase (incl. weekly cadence) without
   * over-weighting old habits; 7 days was too sparse for infrequent loggers,
   * all-time over-weights the past — 14 days is the justified middle default.
   * Source is the existing tag-frequency heatmap; no second tag UI, no markers.
   */
  const RECENCY_WINDOW_DAYS = 14;
  const RECENCY_LIMIT = 8;

  let recentTagIds: string[] = [];
  let showAllTags = false;

  let loadError: string | null = null;
  let showCustomForm = false;
  let customName = '';
  let customSlug = '';
  let customCategory: TagCategory = 'other';
  let customColor = '';
  let customError: string | null = null;
  let customBusy = false;
  let slugTouched = false;
  // Tracks whether the colour was set manually, so switching category
  // re-suggests the group colour only while it is still untouched.
  let colorTouched = false;

  async function loadTags() {
    loadError = null;
    try {
      await refreshTags();
    } catch (err) {
      loadError = err instanceof Error ? err.message : 'load_failed';
    }
  }

  function toISODate(value: Date): string {
    const year = value.getFullYear();
    const month = String(value.getMonth() + 1).padStart(2, '0');
    const day = String(value.getDate()).padStart(2, '0');
    return `${year}-${month}-${day}`;
  }

  // Non-blocking: the recency row is a shortcut on top of the full catalogue.
  // A failure or empty window must never stop tagging or block save/autosave —
  // we simply fall back to the categorised catalogue (60-second rule).
  async function loadRecentTags() {
    try {
      const end = new Date();
      const start = new Date();
      start.setDate(start.getDate() - (RECENCY_WINDOW_DAYS - 1));
      const heatmap = await fetchTagHeatmap({
        start_date: toISODate(start),
        end_date: toISODate(end),
      });
      recentTagIds = rankRecentTagIds(heatmap, RECENCY_LIMIT);
    } catch {
      recentTagIds = [];
    }
  }

  onMount(() => {
    if ($tags.status !== 'ready' && $tags.status !== 'loading') {
      void loadTags();
    }
    void loadRecentTags();
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

  function autoSlugFromName(name: string): string {
    return name
      .normalize('NFKD')
      .replace(/[\u0300-\u036f]/g, '')
      .toLowerCase()
      .replace(/ß/g, 'ss')
      .replace(/[^a-z0-9]+/g, '-')
      .replace(/^-+|-+$/g, '')
      .slice(0, 64);
  }

  $: if (!slugTouched) customSlug = autoSlugFromName(customName);

  function onSlugInput(e: Event) {
    slugTouched = true;
    customSlug = (e.target as HTMLInputElement).value;
  }

  function openCustomForm() {
    customName = '';
    customSlug = '';
    customCategory = 'other';
    customColor = categoryColorForCurrentTheme('other');
    customError = null;
    slugTouched = false;
    colorTouched = false;
    showCustomForm = true;
  }

  function closeCustomForm() {
    showCustomForm = false;
    customError = null;
  }

  function onCategoryChange(e: Event) {
    customCategory = (e.target as HTMLSelectElement).value as TagCategory;
    // Re-suggest the group colour until the user picks one manually.
    if (!colorTouched) customColor = categoryColorForCurrentTheme(customCategory);
  }

  function onColorInput(e: Event) {
    colorTouched = true;
    customColor = (e.target as HTMLInputElement).value;
  }

  async function onSubmitCustom() {
    if (customBusy) return;
    customError = null;
    const name = customName.trim();
    const slug = customSlug.trim().toLowerCase();
    const color = customColor.trim();
    if (!name || !slug || !customCategory) {
      customError = 'tag.custom.error_required';
      return;
    }
    if (!/^[a-z0-9](?:[a-z0-9_-]{0,62}[a-z0-9])$/.test(slug) || slug.length < 2) {
      customError = 'tag.custom.error_slug_invalid';
      return;
    }
    if (color && !/^#[0-9a-fA-F]{6}$/.test(color)) {
      customError = 'tag.custom.error_color_invalid';
      return;
    }
    customBusy = true;
    try {
      const created = await submitTag({
        slug,
        name,
        category: customCategory,
        color: color || null,
      });
      if (!selected.includes(created.id) && selected.length < MAX_TAGS_PER_ENTRY) {
        selected = [...selected, created.id];
      }
      closeCustomForm();
    } catch (err) {
      const status = (err as { status?: number } | null)?.status;
      if (status === 409) {
        customError = 'tag.custom.error_conflict';
      } else if (status === 422) {
        customError = 'tag.custom.error_validation';
      } else {
        customError = 'tag.custom.error_generic';
      }
    } finally {
      customBusy = false;
    }
  }

  // Only show categories that contain at least one tag — keeps the
  // picker compact when the user hasn't added custom tags yet in some
  // categories.
  $: visibleCategories = (TAG_CATEGORIES as readonly TagCategory[]).filter(
    (cat) => $tagsByCategory[cat].length > 0
  );

  $: atLimit = selected.length >= MAX_TAGS_PER_ENTRY;

  $: tagById = new Map($tagsList.map((tag) => [tag.id, tag]));

  // Recency drives the disclosure — NOT the current selection. Only real recency
  // data (mapped to still-existing tags) may collapse the catalogue behind
  // "All tags"; otherwise the first chip click on a new/sparse account, or a
  // heatmap failure with tags already selected, would hide the whole catalogue.
  $: recentTags = recentTagIds
    .map((id) => tagById.get(id))
    .filter((tag): tag is TagResponse => Boolean(tag));
  $: hasRecency = recentTags.length > 0;

  // When a recency row is shown, also surface currently-selected tags in it so a
  // selection is never hidden behind the collapsed catalogue. With no recency the
  // full catalogue is shown directly (selected tags are visible there already).
  $: quickTags = (() => {
    if (!hasRecency) return [];
    const result: TagResponse[] = [];
    const seen = new Set<string>();
    for (const tag of recentTags) {
      if (seen.has(tag.id)) continue;
      seen.add(tag.id);
      result.push(tag);
    }
    for (const id of selected) {
      if (seen.has(id)) continue;
      const tag = tagById.get(id);
      if (!tag) continue;
      seen.add(id);
      result.push(tag);
    }
    return result;
  })();
</script>

<div class="tag-picker">
  <div class="tag-picker-header">
    <span class="tag-counter" aria-live="polite">
      {$_('tag.picker_counter', { values: { count: selected.length, max: MAX_TAGS_PER_ENTRY } })}
    </span>
  </div>

  {#if $tags.status === 'loading'}
    <p class="tag-status">{$_('tag.loading')}</p>
  {:else if $tags.status === 'error' || loadError}
    <div class="tag-status-row">
      <p class="tag-status tag-status-error" role="alert">{$_('tag.error_load')}</p>
      <button type="button" class="tag-retry" on:click={loadTags}>{$_('tag.retry')}</button>
    </div>
  {:else if $tags.status === 'ready' && visibleCategories.length === 0}
    <p class="tag-status">{$_('tag.empty')}</p>
  {:else if $tags.status === 'ready'}
    {#snippet chip(tag: TagResponse)}
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
        <span class="tag-name">{localizedCatalogName(tag.slug, tag.is_default, tag.name, $_)}</span>
      </button>
    {/snippet}

    {#if hasRecency}
      <div class="tag-category" data-testid="tag-recent">
        <h3 class="tag-category-label">
          <span>{$_('tag.recent_heading')}</span>
        </h3>
        <div class="tag-chips">
          {#each quickTags as tag (tag.id)}
            {@render chip(tag)}
          {/each}
        </div>
      </div>
      <button
        type="button"
        class="tag-all-toggle"
        aria-expanded={showAllTags}
        data-testid="tag-all-toggle"
        on:click={() => (showAllTags = !showAllTags)}
      >
        {$_('tag.all_toggle')}
      </button>
    {/if}

    {#if !hasRecency || showAllTags}
      <div class="tag-all" data-testid="tag-all">
        {#each visibleCategories as cat (cat)}
          <div class="tag-category">
            <h3 class="tag-category-label">
              <CategoryIcon category={cat} />
              <span>{$_(`tag.category.${cat}`)}</span>
            </h3>
            <div class="tag-chips">
              {#each $tagsByCategory[cat] as tag (tag.id)}
                {@render chip(tag)}
              {/each}
            </div>
          </div>
        {/each}
      </div>
    {/if}
  {/if}

  {#if atLimit}
    <p class="tag-limit" role="status" data-testid="tag-limit-message">
      {$_('tag.limit_reached')}
    </p>
  {/if}

  <div class="tag-custom">
    {#if !showCustomForm}
      <button
        type="button"
        class="tag-custom-toggle"
        on:click={openCustomForm}
        disabled={disabled || atLimit}
      >
        + {$_('tag.custom.add_button')}
      </button>
    {:else}
      <form
        class="tag-custom-form"
        on:submit|preventDefault={onSubmitCustom}
        aria-labelledby="tag-custom-heading"
      >
        <h3 id="tag-custom-heading" class="tag-custom-heading">{$_('tag.custom.heading')}</h3>
        <label class="tag-custom-field">
          <span class="tag-custom-label">{$_('tag.custom.name_label')}</span>
          <input
            class="input"
            type="text"
            bind:value={customName}
            maxlength="64"
            required
            disabled={customBusy || disabled}
            placeholder={$_('tag.custom.name_placeholder')}
          />
        </label>
        <label class="tag-custom-field">
          <span class="tag-custom-label">{$_('tag.custom.category_label')}</span>
          <select
            class="input"
            value={customCategory}
            on:change={onCategoryChange}
            disabled={customBusy || disabled}
          >
            {#each TAG_CATEGORIES as category}
              <option value={category}>{$_(`tag.category.${category}`)}</option>
            {/each}
          </select>
        </label>
        <label class="tag-custom-field">
          <span class="tag-custom-label">{$_('tag.custom.slug_label')}</span>
          <input
            class="input"
            type="text"
            value={customSlug}
            on:input={onSlugInput}
            minlength="2"
            maxlength="64"
            pattern="[a-z0-9]([a-z0-9_-]*[a-z0-9])?"
            required
            disabled={customBusy || disabled}
            placeholder={$_('tag.custom.slug_placeholder')}
          />
        </label>
        <label class="tag-custom-field">
          <span class="tag-custom-label">{$_('tag.custom.color_label')}</span>
          <input
            class="tag-custom-color"
            type="color"
            value={customColor}
            on:input={onColorInput}
            disabled={customBusy || disabled}
          />
        </label>
        {#if customColor.trim()}
          <span
            class="tag-custom-preview"
            style={`--tag-color: ${customColor.trim()}`}
            aria-live="polite"
          >
            {customName || $_('tag.custom.preview')}
          </span>
        {/if}
        {#if customError}
          <p class="tag-custom-error" role="alert">{$_(customError)}</p>
        {/if}
        <div class="tag-custom-actions">
          <button type="button" class="btn" on:click={closeCustomForm} disabled={customBusy}>
            {$_('tag.custom.cancel')}
          </button>
          <button type="submit" class="btn btn--primary" disabled={customBusy || disabled}>
            {customBusy ? $_('tag.custom.save_busy') : $_('tag.custom.save')}
          </button>
        </div>
      </form>
    {/if}
  </div>
</div>

<style>
  .tag-picker {
    display: flex;
    flex-direction: column;
    gap: var(--space-3);
  }

  .tag-picker-header {
    display: flex;
    justify-content: flex-end;
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
    color: var(--color-error);
    opacity: 1;
  }

  .tag-status-row {
    display: flex;
    align-items: center;
    justify-content: space-between;
    gap: var(--space-3);
  }

  .tag-retry {
    min-height: 44px;
    padding: var(--space-2) var(--space-3);
    border: 1px solid currentColor;
    border-radius: var(--radius-sm);
    background: transparent;
    color: var(--color-error);
    cursor: pointer;
  }

  .tag-limit {
    margin: 0;
    padding: var(--space-2) var(--space-3);
    border-left: 3px solid var(--color-warning);
    border-radius: var(--radius-sm);
    background: color-mix(in srgb, var(--color-warning) 10%, transparent);
    color: var(--color-text);
    font-size: var(--text-sm);
  }

  .tag-all-toggle {
    align-self: flex-start;
    background: transparent;
    border: none;
    padding: var(--space-1) 0;
    font-size: var(--text-sm);
    font-weight: 600;
    color: var(--color-primary);
    cursor: pointer;
    min-height: 44px;
  }

  .tag-all-toggle::after {
    content: ' ▾';
  }

  .tag-all-toggle[aria-expanded='true']::after {
    content: ' ▴';
  }

  .tag-all-toggle:disabled {
    opacity: 0.45;
    cursor: not-allowed;
  }

  .tag-all {
    display: flex;
    flex-direction: column;
    gap: var(--space-3);
  }

  .tag-category {
    display: flex;
    flex-direction: column;
    gap: var(--space-2);
  }

  .tag-category-label {
    display: inline-flex;
    align-items: center;
    gap: var(--space-2);
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
    border-radius: var(--radius-full);
    border: 1px solid var(--color-border);
    background: transparent;
    color: inherit;
    font-size: var(--text-sm);
    line-height: 1.2;
    cursor: pointer;
    min-height: 44px;
    transition:
      background var(--transition-fast),
      border-color var(--transition-fast),
      color var(--transition-fast);
  }

  .tag-chip:hover:not(:disabled) {
    border-color: var(--tag-color, currentColor);
  }

  .tag-chip:disabled {
    opacity: 0.45;
    cursor: not-allowed;
  }

  .tag-chip-active {
    background: var(--tag-color, var(--color-primary));
    border-color: var(--tag-color, var(--color-primary));
    color: var(--color-text-inverse);
  }

  .tag-custom {
    margin-top: var(--space-2);
  }

  .tag-custom-toggle {
    background: transparent;
    border: 1px dashed var(--color-border);
    border-radius: var(--radius-md);
    padding: var(--space-2) var(--space-3);
    font-size: var(--text-sm);
    cursor: pointer;
    color: inherit;
    width: 100%;
    text-align: left;
    transition: border-color var(--transition-fast);
    min-height: 44px;
  }

  .tag-custom-toggle:hover:not(:disabled) {
    border-color: var(--color-primary);
  }

  .tag-custom-toggle:disabled {
    opacity: 0.45;
    cursor: not-allowed;
  }

  .tag-custom-form {
    display: flex;
    flex-direction: column;
    gap: var(--space-3);
    border: 1px solid var(--color-border);
    border-radius: var(--radius-md);
    padding: var(--space-3);
  }

  .tag-custom-heading {
    font-size: var(--text-sm);
    font-weight: 600;
    margin: 0;
  }

  .tag-custom-field {
    display: flex;
    flex-direction: column;
    gap: var(--space-1);
  }

  .tag-custom-label {
    font-size: var(--text-xs);
    font-weight: 500;
    opacity: 0.8;
  }

  .tag-custom-color {
    width: 3rem;
    min-height: 44px;
    border: 1px solid var(--color-border);
    border-radius: var(--radius-sm);
    background: var(--color-surface);
    padding: 0.15rem;
    cursor: pointer;
  }

  .tag-custom-color:disabled {
    opacity: 0.45;
    cursor: not-allowed;
  }

  .tag-custom-preview {
    align-self: flex-start;
    display: inline-flex;
    align-items: center;
    gap: 0.4rem;
    padding: 0.35rem 0.75rem;
    border-radius: var(--radius-full);
    background: var(--tag-color, var(--color-primary-highlight));
    color: var(--color-text);
    font-size: var(--text-sm);
  }

  .tag-custom-error {
    font-size: var(--text-sm);
    color: var(--color-error);
    margin: 0;
  }

  .tag-custom-actions {
    display: flex;
    gap: var(--space-2);
    justify-content: flex-end;
  }
</style>
