<script lang="ts">
  /**
   * SymptomChecker — visual 4-step intensity picker per symptom (Issue #9).
   *
   * Used in the daily-entry form (/entries/new) to attach symptoms to a
   * new entry. The component is "dumb" w.r.t. persistence:
   *   - the parent passes a bound `selected` array of {symptom_key, intensity}
   *   - this component only emits state via two-way binding
   *
   * UX
   * --
   * Each symptom row renders 4 dots representing intensity 0..3. Clicking a
   * dot sets that intensity; clicking the currently-selected dot toggles
   * the symptom off (i.e. removes it from the bound list) — a
   * "no-symptom" state shows no dot filled.
   *
   * Accessibility
   * -------------
   * Each dot is a `<button type="button" aria-pressed>` so screen readers
   * announce the chosen intensity. Each row is a fieldset with a legend
   * carrying the localised symptom name.
   *
   * Privacy
   * -------
   * Symptoms are health data under DSGVO Art. 9. The component never logs
   * the user's selections, even on error. We render a permanent medical
   * disclaimer (`disclaimer.medical`) at the top of the section so users
   * know MoodSync is not a diagnostic tool.
   */

  import { onMount } from 'svelte';
  import { _ } from 'svelte-i18n';
  import { refreshSymptomCatalogue, symptomCatalogue, symptomKeysList } from '$lib/stores/symptoms';
  import {
    INTENSITY_MAX,
    INTENSITY_MIN,
    MAX_SYMPTOMS_PER_ENTRY,
    type SymptomEntry,
  } from '$lib/api/symptoms';

  /** Two-way bound: list of selected (symptom_key, intensity) pairs. */
  export let selected: SymptomEntry[] = [];
  /** Disable interaction (e.g. while the parent form submits). */
  export let disabled = false;

  let loadError: string | null = null;

  onMount(async () => {
    if ($symptomCatalogue.status === 'ready' || $symptomCatalogue.status === 'loading') return;
    try {
      await refreshSymptomCatalogue();
    } catch (err) {
      // The store falls back to the local constant on error so the
      // picker is still usable; we only surface a side-channel warning.
      loadError = err instanceof Error ? err.message : 'load_failed';
    }
  });

  const INTENSITY_VALUES = (() => {
    const out: number[] = [];
    for (let i = INTENSITY_MIN; i <= INTENSITY_MAX; i += 1) out.push(i);
    return out;
  })();

  function getIntensity(key: string, list: SymptomEntry[]): number | null {
    const hit = list.find((s) => s.symptom_key === key);
    return hit ? hit.intensity : null;
  }

  function setIntensity(key: string, value: number) {
    if (disabled) return;
    const current = getIntensity(key, selected);

    // Clicking the already-selected dot clears the symptom row.
    if (current === value) {
      selected = selected.filter((s) => s.symptom_key !== key);
      return;
    }

    if (current === null) {
      // Adding a new symptom — respect the cap.
      if (selected.length >= MAX_SYMPTOMS_PER_ENTRY) return;
      selected = [...selected, { symptom_key: key, intensity: value }];
      return;
    }

    selected = selected.map((s) =>
      s.symptom_key === key ? { symptom_key: key, intensity: value } : s
    );
  }

  $: keys = $symptomKeysList;
  $: atLimit = selected.length >= MAX_SYMPTOMS_PER_ENTRY;
</script>

<section class="symptom-checker" aria-labelledby="symptom-checker-heading">
  <div class="symptom-checker-header">
    <h2 id="symptom-checker-heading" class="entry-label">
      {$_('symptom.picker_label')}
    </h2>
    <span class="symptom-counter" aria-live="polite">
      {$_('symptom.picker_counter', {
        values: { count: selected.length, max: MAX_SYMPTOMS_PER_ENTRY },
      })}
    </span>
  </div>

  <p class="symptom-disclaimer" role="note">{$_('disclaimer.medical')}</p>

  {#if $symptomCatalogue.status === 'loading'}
    <p class="symptom-status">{$_('symptom.loading')}</p>
  {:else if loadError}
    <p class="symptom-status symptom-status-warn" role="status">
      {$_('symptom.error_load')}
    </p>
  {/if}

  {#if keys.length > 0}
    <ul class="symptom-list">
      {#each keys as key (key)}
        {@const current = getIntensity(key, selected)}
        <li class="symptom-row">
          <fieldset class="symptom-fieldset" {disabled}>
            <legend class="symptom-name">{$_(`symptom.key.${key}`)}</legend>
            <div
              class="symptom-scale"
              role="group"
              aria-label={$_('symptom.scale_label', {
                values: { name: $_(`symptom.key.${key}`) },
              })}
            >
              {#each INTENSITY_VALUES as value (value)}
                {@const active = current === value}
                <button
                  type="button"
                  class="symptom-dot"
                  class:symptom-dot-active={active}
                  class:symptom-dot-zero={value === 0}
                  aria-pressed={active}
                  aria-label={$_(`symptom.intensity.${value}`)}
                  title={$_(`symptom.intensity.${value}`)}
                  disabled={disabled || (current === null && atLimit && value !== 0)}
                  on:click={() => setIntensity(key, value)}
                >
                  <span class="symptom-dot-marker" aria-hidden="true">{value}</span>
                </button>
              {/each}
            </div>
          </fieldset>
        </li>
      {/each}
    </ul>
  {/if}
</section>

<style>
  .symptom-checker {
    display: flex;
    flex-direction: column;
    gap: var(--space-3);
  }

  .symptom-checker-header {
    display: flex;
    justify-content: space-between;
    align-items: baseline;
    gap: var(--space-3);
  }

  .symptom-counter {
    font-size: var(--text-xs);
    opacity: 0.7;
    font-variant-numeric: tabular-nums;
  }

  .symptom-disclaimer {
    font-size: var(--text-xs);
    line-height: 1.4;
    opacity: 0.75;
    border-left: 3px solid rgb(var(--color-primary-500) / 0.4);
    padding: var(--space-1) var(--space-3);
    margin: 0;
  }

  .symptom-status {
    font-size: var(--text-sm);
    opacity: 0.75;
  }

  .symptom-status-warn {
    color: rgb(var(--color-warning-500, 245 158 11));
    opacity: 1;
  }

  .symptom-list {
    list-style: none;
    margin: 0;
    padding: 0;
    display: flex;
    flex-direction: column;
    gap: var(--space-3);
  }

  .symptom-row {
    margin: 0;
  }

  .symptom-fieldset {
    border: none;
    margin: 0;
    padding: 0;
    display: grid;
    grid-template-columns: minmax(8rem, 1fr) auto;
    align-items: center;
    gap: var(--space-3);
  }

  .symptom-name {
    font-size: var(--text-sm);
    font-weight: 500;
    padding: 0;
  }

  .symptom-scale {
    display: inline-flex;
    gap: 0.4rem;
  }

  .symptom-dot {
    width: 2rem;
    height: 2rem;
    border-radius: 999px;
    border: 1px solid var(--color-border, #d4d4d4);
    background: transparent;
    color: inherit;
    font-size: var(--text-xs);
    font-weight: 600;
    cursor: pointer;
    display: inline-flex;
    align-items: center;
    justify-content: center;
    line-height: 1;
    transition:
      background 120ms ease,
      border-color 120ms ease,
      color 120ms ease,
      transform 80ms ease;
  }

  .symptom-dot:hover:not(:disabled) {
    border-color: rgb(var(--color-primary-500));
  }

  .symptom-dot:active:not(:disabled) {
    transform: scale(0.94);
  }

  .symptom-dot:disabled {
    opacity: 0.45;
    cursor: not-allowed;
  }

  .symptom-dot-active {
    background: rgb(var(--color-primary-500));
    border-color: rgb(var(--color-primary-500));
    color: #ffffff;
  }

  /* Visual cue: 0 means "no symptom" — keep it neutral even when active. */
  .symptom-dot-zero.symptom-dot-active {
    background: var(--color-surface-2, rgb(var(--color-primary-500) / 0.15));
    color: inherit;
  }

  .symptom-dot-marker {
    pointer-events: none;
  }
</style>
