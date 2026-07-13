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
  import { tags, tagsByCategory, refreshTags, submitTag } from '$lib/stores/tags';
  import { TAG_CATEGORIES, MAX_TAGS_PER_ENTRY, type TagCategory } from '$lib/api/tags';
  import IconRender from '$lib/components/common/IconRender.svelte';

  /** Two-way bound: list of selected tag IDs. */
  export let selected: string[] = [];
  /** Disable interaction (e.g. while the parent form submits). */
  export let disabled = false;

  let loadError: string | null = null;
  let showCustomForm = false;
  let customName = '';
  let customSlug = '';
  let customCategory: TagCategory = 'other';
  let customIcon = '';
  let customColor = '';
  let customError: string | null = null;
  let customBusy = false;
  let slugTouched = false;

  async function loadTags() {
    loadError = null;
    try {
      await refreshTags();
    } catch (err) {
      loadError = err instanceof Error ? err.message : 'load_failed';
    }
  }

  onMount(async () => {
    if ($tags.status === 'ready' || $tags.status === 'loading') return;
    await loadTags();
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
    customIcon = '';
    customColor = '';
    customError = null;
    slugTouched = false;
    showCustomForm = true;
  }

  function closeCustomForm() {
    showCustomForm = false;
    customError = null;
  }

  async function onSubmitCustom() {
    if (customBusy) return;
    customError = null;
    const name = customName.trim();
    const slug = customSlug.trim().toLowerCase();
    const icon = customIcon.trim();
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
        icon: icon || null,
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
    <div class="tag-status-row">
      <p class="tag-status tag-status-error" role="alert">{$_('tag.error_load')}</p>
      <button type="button" class="tag-retry" on:click={loadTags}>{$_('tag.retry')}</button>
    </div>
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
                <span class="tag-icon" aria-hidden="true">
                  <IconRender icon={tag.icon} size={16} />
                </span>
              {/if}
              <span class="tag-name">{tag.name}</span>
            </button>
          {/each}
        </div>
      </div>
    {/each}
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
          <select class="input" bind:value={customCategory} disabled={customBusy || disabled}>
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
        <div class="tag-custom-grid">
          <label class="tag-custom-field">
            <span class="tag-custom-label">{$_('tag.custom.icon_label')}</span>
            <input
              class="input"
              type="text"
              bind:value={customIcon}
              maxlength="32"
              disabled={customBusy || disabled}
              placeholder={$_('tag.custom.icon_placeholder')}
            />
          </label>
          <label class="tag-custom-field">
            <span class="tag-custom-label">{$_('tag.custom.color_label')}</span>
            <input
              class="input"
              type="text"
              bind:value={customColor}
              maxlength="7"
              pattern="#[0-9a-fA-F]{6}"
              disabled={customBusy || disabled}
              placeholder={$_('tag.custom.color_placeholder')}
            />
          </label>
        </div>
        {#if customIcon.trim() || customColor.trim()}
          <span
            class="tag-custom-preview"
            style={customColor.trim() ? `--tag-color: ${customColor.trim()}` : ''}
            aria-live="polite"
          >
            {#if customIcon.trim()}
              <IconRender icon={customIcon} size={16} />
            {/if}
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
          <button
            type="submit"
            class="btn btn--primary"
            disabled={customBusy || disabled}
          >
            {customBusy ? $_('tag.custom.save_busy') : $_('tag.custom.save')}
          </button>
        </div>
      </form>
    {/if}
  </div>
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
    border: 1px solid var(--color-border);
    background: transparent;
    color: inherit;
    font-size: var(--text-sm);
    line-height: 1.2;
    cursor: pointer;
    min-height: 44px;
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
    background: var(--tag-color, var(--color-primary));
    border-color: var(--tag-color, var(--color-primary));
    color: var(--color-text-inverse);
  }

  .tag-icon {
    font-size: 1rem;
    line-height: 1;
  }

  .tag-custom {
    margin-top: var(--space-2);
  }

  .tag-custom-toggle {
    background: transparent;
    border: 1px dashed var(--color-border);
    border-radius: 8px;
    padding: var(--space-2) var(--space-3);
    font-size: var(--text-sm);
    cursor: pointer;
    color: inherit;
    width: 100%;
    text-align: left;
    transition: border-color 120ms ease;
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
    border-radius: 8px;
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

  .tag-custom-grid {
    display: grid;
    grid-template-columns: repeat(2, minmax(0, 1fr));
    gap: var(--space-3);
  }

  .tag-custom-preview {
    align-self: flex-start;
    display: inline-flex;
    align-items: center;
    gap: 0.4rem;
    padding: 0.35rem 0.75rem;
    border-radius: 999px;
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

  @media (max-width: 520px) {
    .tag-custom-grid {
      grid-template-columns: 1fr;
    }
  }
</style>
