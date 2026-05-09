<script lang="ts">
  /**
   * SymptomChecker — visual 4-step intensity picker per symptom
   * (Issue #9 + Issue #57 Custom-Symptome).
   *
   * Used in the daily-entry form (/entries/new) to attach symptoms to a
   * new entry. The component is "dumb" w.r.t. persistence:
   *   - the parent passes a bound `selected` array of {symptom_id, intensity}
   *   - this component only emits state via two-way binding
   *
   * Custom symptoms (Issue #57)
   * ---------------------------
   * Defaults render with their localised name (`symptom.key.<slug>`) so
   * the canonical 5 stay consistent across UI languages. Custom symptoms
   * render with the user-provided name verbatim plus optional icon — they
   * can be added inline via the "Custom hinzufügen" form below the list.
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
   * carrying the symptom name.
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
  import IconRender from '$lib/components/common/IconRender.svelte';
  import { refreshSymptoms, submitSymptom, symptoms, symptomsList } from '$lib/stores/symptoms';
  import {
    INTENSITY_MAX,
    INTENSITY_MIN,
    MAX_SYMPTOMS_PER_ENTRY,
    type SymptomEntry,
    type SymptomResponse,
  } from '$lib/api/symptoms';

  /** Two-way bound: list of selected (symptom_id, intensity) pairs. */
  export let selected: SymptomEntry[] = [];
  /** Disable interaction (e.g. while the parent form submits). */
  export let disabled = false;

  let loadError: string | null = null;
  let showCustomForm = false;
  let customName = '';
  let customSlug = '';
  let customIcon = '';
  let customError: string | null = null;
  let customBusy = false;

  onMount(async () => {
    if ($symptoms.status === 'ready' || $symptoms.status === 'loading') return;
    try {
      await refreshSymptoms();
    } catch (err) {
      loadError = err instanceof Error ? err.message : 'load_failed';
    }
  });

  const INTENSITY_VALUES = (() => {
    const out: number[] = [];
    for (let i = INTENSITY_MIN; i <= INTENSITY_MAX; i += 1) out.push(i);
    return out;
  })();

  /**
   * Display name for a symptom: defaults are localised via i18n key,
   * custom symptoms render their user-provided name verbatim.
   */
  function displayName(
    s: SymptomResponse,
    // eslint-disable-next-line no-unused-vars
    translator: (k: string) => string
  ): string {
    if (s.is_default) {
      const i18nKey = `symptom.key.${s.slug}`;
      const translated = translator(i18nKey);
      // svelte-i18n returns the key itself when missing → fall back to backend name.
      return translated === i18nKey ? s.name : translated;
    }
    return s.name;
  }

  function getIntensity(symptomId: string, list: SymptomEntry[]): number | null {
    const hit = list.find((s) => s.symptom_id === symptomId);
    return hit ? hit.intensity : null;
  }

  function setIntensity(symptomId: string, value: number) {
    if (disabled) return;
    const current = getIntensity(symptomId, selected);

    // Clicking the already-selected dot clears the symptom row.
    if (current === value) {
      selected = selected.filter((s) => s.symptom_id !== symptomId);
      return;
    }

    if (current === null) {
      // Adding a new symptom — respect the cap.
      if (selected.length >= MAX_SYMPTOMS_PER_ENTRY) return;
      selected = [...selected, { symptom_id: symptomId, intensity: value }];
      return;
    }

    selected = selected.map((s) =>
      s.symptom_id === symptomId ? { symptom_id: symptomId, intensity: value } : s
    );
  }

  /**
   * Auto-derive a slug from the user-typed name when the slug field is
   * still untouched. We strip diacritics, lowercase, replace runs of
   * non-[a-z0-9] with `_`, and trim the result.
   */
  let slugTouched = false;
  function autoSlugFromName(name: string): string {
    return name
      .normalize('NFKD')
      .replace(/[\u0300-\u036f]/g, '')
      .toLowerCase()
      .replace(/ß/g, 'ss')
      .replace(/[^a-z0-9]+/g, '_')
      .replace(/^_+|_+$/g, '')
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
    customIcon = '';
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
    const slug = customSlug.trim();
    const icon = customIcon.trim();
    if (!name || !slug) {
      customError = 'symptom.custom.error_required';
      return;
    }
    if (!/^[a-z0-9_]+$/.test(slug) || slug.length > 64) {
      customError = 'symptom.custom.error_slug_invalid';
      return;
    }
    customBusy = true;
    try {
      await submitSymptom({ slug, name, icon: icon || null });
      closeCustomForm();
    } catch (err) {
      // Map common API error shapes into i18n keys without leaking the
      // raw payload (DSGVO Art. 9 — keep symptom names off console).
      const status = (err as { status?: number } | null)?.status;
      if (status === 409) {
        customError = 'symptom.custom.error_conflict';
      } else if (status === 422) {
        customError = 'symptom.custom.error_validation';
      } else {
        customError = 'symptom.custom.error_generic';
      }
    } finally {
      customBusy = false;
    }
  }

  $: list = $symptomsList;
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

  {#if $symptoms.status === 'loading'}
    <p class="symptom-status">{$_('symptom.loading')}</p>
  {:else if $symptoms.status === 'error' || loadError}
    <p class="symptom-status symptom-status-warn" role="status">
      {$_('symptom.error_load')}
    </p>
  {/if}

  {#if list.length > 0}
    <ul class="symptom-list">
      {#each list as symptom (symptom.id)}
        {@const current = getIntensity(symptom.id, selected)}
        {@const name = displayName(symptom, $_)}
        <li class="symptom-row">
          <fieldset class="symptom-fieldset" {disabled}>
            <legend class="symptom-name">
              {#if symptom.icon}
                <span class="symptom-icon" aria-hidden="true">
                  <IconRender icon={symptom.icon} />
                </span>
              {/if}
              <span>{name}</span>
            </legend>
            <div
              class="symptom-scale"
              role="group"
              aria-label={$_('symptom.scale_label', { values: { name } })}
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
                  on:click={() => setIntensity(symptom.id, value)}
                >
                  <span class="symptom-dot-marker" aria-hidden="true">{value}</span>
                </button>
              {/each}
            </div>
          </fieldset>
        </li>
      {/each}
    </ul>
  {:else if $symptoms.status === 'ready'}
    <p class="symptom-status">{$_('symptom.empty')}</p>
  {/if}

  <div class="symptom-custom">
    {#if !showCustomForm}
      <button type="button" class="symptom-custom-toggle" on:click={openCustomForm} {disabled}>
        + {$_('symptom.custom.add_button')}
      </button>
    {:else}
      <form
        class="symptom-custom-form"
        on:submit|preventDefault={onSubmitCustom}
        aria-labelledby="symptom-custom-heading"
      >
        <h3 id="symptom-custom-heading" class="symptom-custom-heading">
          {$_('symptom.custom.heading')}
        </h3>
        <label class="symptom-custom-field">
          <span class="symptom-custom-label">{$_('symptom.custom.name_label')}</span>
          <input
            class="input"
            type="text"
            bind:value={customName}
            maxlength="80"
            required
            disabled={customBusy || disabled}
            placeholder={$_('symptom.custom.name_placeholder')}
          />
        </label>
        <label class="symptom-custom-field">
          <span class="symptom-custom-label">{$_('symptom.custom.slug_label')}</span>
          <input
            class="input"
            type="text"
            value={customSlug}
            on:input={onSlugInput}
            maxlength="64"
            pattern="[a-z0-9_]+"
            required
            disabled={customBusy || disabled}
            placeholder={$_('symptom.custom.slug_placeholder')}
          />
        </label>
        <label class="symptom-custom-field">
          <span class="symptom-custom-label">{$_('symptom.custom.icon_label')}</span>
          <input
            class="input"
            type="text"
            bind:value={customIcon}
            maxlength="32"
            disabled={customBusy || disabled}
            placeholder={$_('symptom.custom.icon_placeholder')}
          />
          <small class="symptom-custom-hint">{$_('symptom.custom.icon_hint')}</small>
          {#if customIcon.trim()}
            <span class="symptom-custom-preview" aria-live="polite">
              <IconRender icon={customIcon} size={20} />
            </span>
          {/if}
        </label>
        {#if customError}
          <p class="symptom-custom-error" role="alert">{$_(customError)}</p>
        {/if}
        <div class="symptom-custom-actions">
          <button type="button" class="btn" on:click={closeCustomForm} disabled={customBusy}>
            {$_('symptom.custom.cancel')}
          </button>
          <button
            type="submit"
            class="btn variant-filled-primary"
            disabled={customBusy || disabled}
          >
            {customBusy ? $_('symptom.custom.save_busy') : $_('symptom.custom.save')}
          </button>
        </div>
      </form>
    {/if}
  </div>
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
    display: inline-flex;
    align-items: center;
    gap: 0.4rem;
  }

  .symptom-icon {
    font-size: 1rem;
    line-height: 1;
    display: inline-flex;
    align-items: center;
  }

  .symptom-custom-hint {
    display: block;
    margin-top: 0.25rem;
    font-size: var(--text-xs, 0.78rem);
    color: var(--color-muted, #6b7280);
    line-height: 1.4;
  }

  .symptom-custom-preview {
    display: inline-flex;
    align-items: center;
    margin-top: 0.35rem;
    padding: 0.2rem 0.45rem;
    border-radius: 6px;
    background: var(--color-surface-2, rgba(0, 0, 0, 0.04));
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

  .symptom-custom {
    margin-top: var(--space-2);
  }

  .symptom-custom-toggle {
    background: transparent;
    border: 1px dashed var(--color-border, #d4d4d4);
    border-radius: 8px;
    padding: var(--space-2) var(--space-3);
    font-size: var(--text-sm);
    cursor: pointer;
    color: inherit;
    width: 100%;
    text-align: left;
    transition: border-color 120ms ease;
  }

  .symptom-custom-toggle:hover:not(:disabled) {
    border-color: rgb(var(--color-primary-500));
  }

  .symptom-custom-toggle:disabled {
    opacity: 0.45;
    cursor: not-allowed;
  }

  .symptom-custom-form {
    display: flex;
    flex-direction: column;
    gap: var(--space-3);
    border: 1px solid var(--color-border, #d4d4d4);
    border-radius: 8px;
    padding: var(--space-3);
  }

  .symptom-custom-heading {
    font-size: var(--text-sm);
    font-weight: 600;
    margin: 0;
  }

  .symptom-custom-field {
    display: flex;
    flex-direction: column;
    gap: var(--space-1);
  }

  .symptom-custom-label {
    font-size: var(--text-xs);
    font-weight: 500;
    opacity: 0.8;
  }

  .symptom-custom-error {
    font-size: var(--text-sm);
    color: rgb(var(--color-error-500));
    margin: 0;
  }

  .symptom-custom-actions {
    display: flex;
    gap: var(--space-2);
    justify-content: flex-end;
  }
</style>
