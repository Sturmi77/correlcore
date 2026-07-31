<script lang="ts">
  import { createEventDispatcher } from 'svelte';
  import { _ } from 'svelte-i18n';
  import type { HomeSectionKey, HomeSectionPreference } from '$lib/api/preferences';
  import IconButton from '$lib/components/common/IconButton.svelte';
  import {
    DEFAULT_HOME_SECTIONS,
    mergeHomeSections,
    normalizeHomeSectionsForSave,
  } from '$lib/utils/homeSections';

  export let sections: HomeSectionPreference[] = DEFAULT_HOME_SECTIONS;
  export let disabled = false;

  const dispatch = createEventDispatcher<{
    change: HomeSectionPreference[];
  }>();

  $: orderedSections = mergeHomeSections(sections);

  function emitChange(next: HomeSectionPreference[]): void {
    const normalized = normalizeHomeSectionsForSave(next);
    sections = normalized;
    dispatch('change', normalized);
  }

  function toggleSection(key: HomeSectionKey, enabled: boolean): void {
    emitChange(
      orderedSections.map((section) =>
        section.key === key ? { ...section, enabled } : section
      )
    );
  }

  function moveSection(key: HomeSectionKey, direction: -1 | 1): void {
    const index = orderedSections.findIndex((section) => section.key === key);
    const target = index + direction;
    if (index < 0 || target < 0 || target >= orderedSections.length) return;

    const next = [...orderedSections];
    const [item] = next.splice(index, 1);
    next.splice(target, 0, item);
    emitChange(next);
  }

  function resetDefaults(): void {
    emitChange(DEFAULT_HOME_SECTIONS.map((section) => ({ ...section })));
  }
</script>

<div class="home-sections-editor" data-testid="home-sections-editor">
  <ul class="home-sections-editor__list" aria-label={$_('settings.home.list_aria')}>
    {#each orderedSections as section, index (section.key)}
      <li class="home-sections-editor__row" data-testid={`home-section-row-${section.key}`}>
        <label class="home-sections-editor__toggle">
          <input
            type="checkbox"
            checked={section.enabled}
            disabled={disabled}
            data-testid={`home-section-toggle-${section.key}`}
            on:change={(event) =>
              toggleSection(section.key, (event.currentTarget as HTMLInputElement).checked)}
          />
          <span class="home-sections-editor__copy">
            <strong>{$_(`settings.home.sections.${section.key}.label`)}</strong>
            <span>{$_(`settings.home.sections.${section.key}.description`)}</span>
          </span>
        </label>
        <div class="home-sections-editor__actions">
          <IconButton
            type="button"
            size="sm"
            ariaLabel={$_('settings.home.move_up')}
            disabled={disabled || index === 0}
            data-testid={`home-section-up-${section.key}`}
            on:click={() => moveSection(section.key, -1)}
          >
            ↑
          </IconButton>
          <IconButton
            type="button"
            size="sm"
            ariaLabel={$_('settings.home.move_down')}
            disabled={disabled || index === orderedSections.length - 1}
            data-testid={`home-section-down-${section.key}`}
            on:click={() => moveSection(section.key, 1)}
          >
            ↓
          </IconButton>
        </div>
      </li>
    {/each}
  </ul>
  <button
    type="button"
    class="home-sections-editor__reset"
    disabled={disabled}
    data-testid="home-sections-reset"
    on:click={resetDefaults}
  >
    {$_('settings.home.reset_defaults')}
  </button>
</div>

<style>
  .home-sections-editor {
    display: grid;
    gap: var(--space-4);
  }

  .home-sections-editor__list {
    display: grid;
    gap: var(--space-3);
    margin: 0;
    padding: 0;
    list-style: none;
  }

  .home-sections-editor__row {
    display: flex;
    align-items: center;
    justify-content: space-between;
    gap: var(--space-3);
    padding: var(--space-3);
    border: 1px solid var(--color-border);
    border-radius: var(--radius-md);
    background: var(--color-surface);
  }

  .home-sections-editor__toggle {
    display: flex;
    align-items: flex-start;
    gap: var(--space-3);
    flex: 1;
    min-width: 0;
    cursor: pointer;
  }

  .home-sections-editor__copy {
    display: grid;
    gap: var(--space-1);
    min-width: 0;
  }

  .home-sections-editor__copy strong {
    font-size: var(--text-sm);
  }

  .home-sections-editor__copy span {
    color: var(--color-text-muted);
    font-size: var(--text-xs);
    line-height: 1.45;
  }

  .home-sections-editor__actions {
    display: flex;
    gap: var(--space-1);
    flex: 0 0 auto;
  }

  .home-sections-editor__reset {
    justify-self: start;
    padding: 0;
    border: 0;
    background: none;
    color: var(--color-primary);
    font: inherit;
    font-size: var(--text-sm);
    font-weight: 650;
    cursor: pointer;
  }

  .home-sections-editor__reset:disabled {
    opacity: 0.55;
    cursor: not-allowed;
  }

  @media (max-width: 480px) {
    .home-sections-editor__row {
      align-items: stretch;
      flex-direction: column;
    }

    .home-sections-editor__actions {
      justify-content: flex-end;
    }
  }
</style>
