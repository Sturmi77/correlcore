<script lang="ts">
  import { createEventDispatcher } from 'svelte';
  import { _ } from 'svelte-i18n';
  import IconButton from '$lib/components/common/IconButton.svelte';
  import type { SectionPreference } from '$lib/utils/sectionPreferences';

  /**
   * Generic order/visibility editor shared by the Home (#584) and Insights
   * (#821) section settings. Callers pass their merge/normalize helpers plus a
   * test-id and i18n key prefix. Locked keys stay always enabled (toggle
   * disabled) but remain reorderable.
   */
  export let sections: SectionPreference[] = [];
  export let disabled = false;
  export let defaults: SectionPreference[];
  export let merge: (stored: SectionPreference[] | null | undefined) => SectionPreference[];
  export let normalize: (sections: SectionPreference[]) => SectionPreference[];
  export let lockedKeys: string[] = [];
  /** Test-id + CSS prefix, e.g. "home" or "insights". */
  export let testIdPrefix: string;
  /** i18n key prefix, e.g. "settings.home" or "settings.insights". */
  export let i18nPrefix: string;

  const dispatch = createEventDispatcher<{
    change: SectionPreference[];
  }>();

  $: lockedSet = new Set(lockedKeys);
  $: orderedSections = merge(sections);

  function emitChange(next: SectionPreference[]): void {
    const normalized = normalize(next);
    sections = normalized;
    dispatch('change', normalized);
  }

  function toggleSection(key: string, enabled: boolean): void {
    if (lockedSet.has(key)) return;
    emitChange(
      orderedSections.map((section) => (section.key === key ? { ...section, enabled } : section))
    );
  }

  function moveSection(key: string, direction: -1 | 1): void {
    const index = orderedSections.findIndex((section) => section.key === key);
    const target = index + direction;
    if (index < 0 || target < 0 || target >= orderedSections.length) return;

    const next = [...orderedSections];
    const [item] = next.splice(index, 1);
    next.splice(target, 0, item);
    emitChange(next);
  }

  function resetDefaults(): void {
    emitChange(defaults.map((section) => ({ ...section })));
  }
</script>

<div class="sections-editor" data-testid={`${testIdPrefix}-sections-editor`}>
  <ul class="sections-editor__list" aria-label={$_(`${i18nPrefix}.list_aria`)}>
    {#each orderedSections as section, index (section.key)}
      <li class="sections-editor__row" data-testid={`${testIdPrefix}-section-row-${section.key}`}>
        <label class="sections-editor__toggle">
          <input
            type="checkbox"
            checked={section.enabled}
            disabled={disabled || lockedSet.has(section.key)}
            data-testid={`${testIdPrefix}-section-toggle-${section.key}`}
            on:change={(event) =>
              toggleSection(section.key, (event.currentTarget as HTMLInputElement).checked)}
          />
          <span class="sections-editor__copy">
            <strong>{$_(`${i18nPrefix}.sections.${section.key}.label`)}</strong>
            <span>{$_(`${i18nPrefix}.sections.${section.key}.description`)}</span>
            {#if lockedSet.has(section.key)}
              <span class="sections-editor__locked" data-testid={`${testIdPrefix}-section-locked-${section.key}`}>
                {$_(`${i18nPrefix}.locked_note`)}
              </span>
            {/if}
          </span>
        </label>
        <div class="sections-editor__actions">
          <IconButton
            type="button"
            size="sm"
            ariaLabel={`${$_(`${i18nPrefix}.sections.${section.key}.label`)} — ${$_(`${i18nPrefix}.move_up`)}`}
            disabled={disabled || index === 0}
            data-testid={`${testIdPrefix}-section-up-${section.key}`}
            on:click={() => moveSection(section.key, -1)}
          >
            ↑
          </IconButton>
          <IconButton
            type="button"
            size="sm"
            ariaLabel={`${$_(`${i18nPrefix}.sections.${section.key}.label`)} — ${$_(`${i18nPrefix}.move_down`)}`}
            disabled={disabled || index === orderedSections.length - 1}
            data-testid={`${testIdPrefix}-section-down-${section.key}`}
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
    class="sections-editor__reset"
    {disabled}
    data-testid={`${testIdPrefix}-sections-reset`}
    on:click={resetDefaults}
  >
    {$_(`${i18nPrefix}.reset_defaults`)}
  </button>
</div>

<style>
  .sections-editor {
    display: grid;
    gap: var(--space-4);
  }

  .sections-editor__list {
    display: grid;
    gap: var(--space-3);
    margin: 0;
    padding: 0;
    list-style: none;
  }

  .sections-editor__row {
    display: flex;
    align-items: center;
    justify-content: space-between;
    gap: var(--space-3);
    padding: var(--space-3);
    border: 1px solid var(--color-border);
    border-radius: var(--radius-md);
    background: var(--color-surface);
  }

  .sections-editor__toggle {
    display: flex;
    align-items: flex-start;
    gap: var(--space-3);
    flex: 1;
    min-width: 0;
    cursor: pointer;
  }

  .sections-editor__copy {
    display: grid;
    gap: var(--space-1);
    min-width: 0;
  }

  .sections-editor__copy strong {
    font-size: var(--text-sm);
  }

  .sections-editor__copy span {
    color: var(--color-text-muted);
    font-size: var(--text-xs);
    line-height: 1.45;
  }

  .sections-editor__locked {
    color: var(--color-text-muted);
    font-size: var(--text-xs);
    font-weight: 650;
    font-style: italic;
  }

  .sections-editor__actions {
    display: flex;
    gap: var(--space-1);
    flex: 0 0 auto;
  }

  .sections-editor__reset {
    justify-self: start;
    min-width: 44px;
    min-height: 44px;
    padding: 0.35rem 0.75rem;
    border: 0;
    background: none;
    color: var(--color-primary);
    font: inherit;
    font-size: var(--text-sm);
    font-weight: 650;
    cursor: pointer;
  }

  .sections-editor__reset:disabled {
    opacity: 0.55;
    cursor: not-allowed;
  }

  @media (max-width: 480px) {
    .sections-editor__row {
      align-items: stretch;
      flex-direction: column;
    }

    .sections-editor__actions {
      justify-content: flex-end;
    }
  }
</style>
