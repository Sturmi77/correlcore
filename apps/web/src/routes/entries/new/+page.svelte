<script lang="ts">
  /**
   * /entries/new — daily-entry form (Issue #7).
   *
   * Design constraints (DESIGN_DOCUMENT.md §6 + Issue #7):
   *   - 60-second rule: a default entry should be submittable in ≤ 60 s.
   *     We pre-fill mood/energy/stress to a neutral 3 and pick the date
   *     based on weekday → a typical homeoffice/office/weekend default.
   *   - A11y: each scale has +/- buttons in addition to the slider
   *     (see ScaleSlider).
   *   - Backdating is allowed up to 7 days; the date input is bounded
   *     accordingly.
   *   - On success the user is redirected back to "/" (the timeline /
   *     home page that will land in a sibling issue).
   */

  import { onMount } from 'svelte';
  import { _ } from 'svelte-i18n';
  import { goto } from '$app/navigation';
  import ScaleSlider from '$lib/components/entries/ScaleSlider.svelte';
  import TagPicker from '$lib/components/entries/TagPicker.svelte';
  import SymptomChecker from '$lib/components/entries/SymptomChecker.svelte';
  import ThemeToggle from '$lib/components/common/ThemeToggle.svelte';
  import { listEntries, updateEntry, type EntryResponse, type WorkContext } from '$lib/api/entries';
  import { submitEntry } from '$lib/stores/entries';
  import { assignTagsToEntry, listTagsForEntry } from '$lib/api/tags';
  import {
    assignSymptomsToEntry,
    listSymptomsForEntry,
    type SymptomEntry,
  } from '$lib/api/symptoms';
  import { mapApiError, type ApiErrorMap } from '$lib/utils/error';

  // ---------------------------------------------------------------------
  // Form state
  // ---------------------------------------------------------------------

  function isoDate(d: Date): string {
    return d.toISOString().slice(0, 10);
  }

  function defaultWorkContext(d: Date): WorkContext {
    const dow = d.getDay(); // 0 = Sun
    if (dow === 0 || dow === 6) return 'weekend';
    return 'homeoffice';
  }

  const today = new Date();
  const sevenDaysAgo = new Date(today.getTime() - 7 * 24 * 60 * 60 * 1000);

  let entryDate: string = isoDate(today);
  let moodScore = 3;
  let energy = 3;
  let stress = 3;
  let workContext: WorkContext = defaultWorkContext(today);
  let note = '';
  let selectedTagIds: string[] = [];
  let selectedSymptoms: SymptomEntry[] = [];
  let busy = false;
  let errorKey: string | null = null;

  // Edit-mode: when the user navigates to a date that already has a
  // ``slot=day`` entry, we hydrate the form with the existing values so
  // the picker doubles as both "new" and "edit" view. The presence of
  // ``existingEntryId`` flips the submit handler from POST to PATCH and
  // re-uses the same replace-set tag/symptom assignment endpoints.
  let existingEntryId: string | null = null;
  let loading = false;
  // Debounce token: each load invocation increments this; stale
  // responses (user changed date again before fetch returned) are
  // discarded so the form doesn't snap back to outdated data.
  let loadToken = 0;

  // Keep the work-context default in sync if the user picks a different
  // day, but only until they manually change it themselves.
  let workContextTouched = false;
  $: if (!workContextTouched && entryDate && !existingEntryId) {
    const d = new Date(entryDate + 'T00:00:00');
    if (!Number.isNaN(d.getTime())) {
      workContext = defaultWorkContext(d);
    }
  }

  /**
   * Reset the form to the neutral default for a date with no entry yet.
   * Called when the user picks a date and the API returns no match.
   */
  function resetForm(forDate: string) {
    existingEntryId = null;
    moodScore = 3;
    energy = 3;
    stress = 3;
    note = '';
    selectedTagIds = [];
    selectedSymptoms = [];
    workContextTouched = false;
    const d = new Date(forDate + 'T00:00:00');
    if (!Number.isNaN(d.getTime())) {
      workContext = defaultWorkContext(d);
    }
  }

  /**
   * Hydrate the form from an existing entry. Tags and symptoms are
   * fetched in parallel; failures there are non-fatal (form still
   * usable, just without the related rows pre-selected). Errors on the
   * entry fetch itself are surfaced via ``errorKey``.
   */
  async function loadForDate(date: string) {
    const myToken = ++loadToken;
    loading = true;
    errorKey = null;
    try {
      const matches = await listEntries({
        start_date: date,
        end_date: date,
        limit: 5,
      });
      if (myToken !== loadToken) return;
      const dayEntry = matches.find(
        (e: EntryResponse) => e.entry_date === date && e.slot === 'day'
      );
      if (!dayEntry) {
        resetForm(date);
        return;
      }
      existingEntryId = dayEntry.id;
      moodScore = dayEntry.mood_score;
      energy = dayEntry.energy;
      stress = dayEntry.stress;
      workContext = dayEntry.work_context;
      // Mark touched so the date-change reactive block doesn't reset it
      // back to the weekday default.
      workContextTouched = true;
      note = dayEntry.note ?? '';

      // Tags + symptoms load in parallel; both wrapped so one slow
      // network blip doesn't keep the other from rendering.
      const [tagsRes, symRes] = await Promise.allSettled([
        listTagsForEntry(dayEntry.id),
        listSymptomsForEntry(dayEntry.id),
      ]);
      if (myToken !== loadToken) return;
      if (tagsRes.status === 'fulfilled') {
        selectedTagIds = tagsRes.value.map((t) => t.id);
      }
      if (symRes.status === 'fulfilled') {
        selectedSymptoms = symRes.value.map((s) => ({
          symptom_id: s.symptom_id,
          intensity: s.intensity,
        }));
      }
    } catch (err) {
      if (myToken !== loadToken) return;
      errorKey = mapApiError(err, ERROR_MAP) ?? 'entry.error_load';
      resetForm(date);
    } finally {
      if (myToken === loadToken) loading = false;
    }
  }

  // Reactively reload whenever the user picks a different date. The
  // initial call is also covered: once ``entryDate`` is initialised
  // above, this reactive block fires on mount.
  $: if (entryDate) {
    void loadForDate(entryDate);
  }

  function onWorkContextChange(e: Event) {
    workContextTouched = true;
    workContext = (e.target as HTMLSelectElement).value as WorkContext;
  }

  const ERROR_MAP: ApiErrorMap = {
    401: 'entry.error_unauthenticated',
    409: 'entry.error_conflict',
    422: 'entry.error_too_old',
  };

  const WORK_CONTEXTS: WorkContext[] = [
    'homeoffice',
    'office',
    'vacation',
    'sick',
    'weekend',
    'travel',
  ];

  async function onSubmit() {
    if (busy) return;
    busy = true;
    errorKey = null;
    try {
      // Two flows from one form: when ``existingEntryId`` is set the
      // user is editing an entry that the loader pulled in earlier, so
      // we PATCH instead of POST. Replace-set tag/symptom assignment
      // remains the same in both cases (PUT is idempotent).
      let entryId: string;
      if (existingEntryId) {
        const updated = await updateEntry(existingEntryId, {
          mood_score: moodScore,
          energy,
          stress,
          work_context: workContext,
          note: note.trim() ? note.trim() : '',
        });
        entryId = updated.id;
      } else {
        const created = await submitEntry({
          entry_date: entryDate,
          slot: 'day',
          mood_score: moodScore,
          energy,
          stress,
          work_context: workContext,
          note: note.trim() ? note.trim() : undefined,
        });
        entryId = created.id;
      }

      // Tag/Symptom-Assignment: replace-set semantics make this safe
      // even when re-submitting an unchanged form. Sending the
      // (possibly empty) lists guarantees "unchecked" rows actually
      // disappear server-side.
      try {
        await assignTagsToEntry(entryId, selectedTagIds);
      } catch (tagErr) {
        errorKey = mapApiError(tagErr, ERROR_MAP) ?? 'tag.error_assign';
        return;
      }
      try {
        await assignSymptomsToEntry(entryId, selectedSymptoms);
      } catch (symptomErr) {
        errorKey = mapApiError(symptomErr, ERROR_MAP) ?? 'symptom.error_assign';
        return;
      }
      await goto('/', { replaceState: true });
    } catch (err) {
      errorKey = mapApiError(err, ERROR_MAP) ?? 'entry.error_generic';
    } finally {
      busy = false;
    }
  }

  onMount(() => {
    // Focus the mood slider so a typical "log my day" flow needs zero clicks.
    const el = document.getElementById('entry-mood');
    el?.focus();
  });
</script>

<svelte:head>
  <title>{$_('entry.title')} — {$_('app.name')}</title>
</svelte:head>

<header class="entry-header">
  <div class="entry-header-row">
    <div class="entry-header-text">
      <h1 class="entry-title">{$_('entry.title')}</h1>
      <p class="entry-subtitle">{$_('entry.subtitle')}</p>
      {#if existingEntryId}
        <p class="entry-edit-hint" role="status" data-testid="entry-edit-hint">
          {$_('entry.edit_hint')}
        </p>
      {/if}
    </div>
    <ThemeToggle testId="entry-theme-toggle" />
  </div>
</header>

<form
  class="entry-form"
  on:submit|preventDefault={onSubmit}
  novalidate
  aria-busy={loading}
  data-loading={loading ? 'true' : 'false'}
>
  <label class="entry-field">
    <span class="entry-label">{$_('entry.date_label')}</span>
    <input
      type="date"
      class="input"
      bind:value={entryDate}
      min={isoDate(sevenDaysAgo)}
      max={isoDate(today)}
      required
      disabled={busy}
    />
  </label>

  <ScaleSlider
    id="entry-mood"
    label={$_('entry.mood_label')}
    decrementLabel={$_('entry.mood_decrement')}
    incrementLabel={$_('entry.mood_increment')}
    bind:value={moodScore}
  />

  <ScaleSlider
    id="entry-energy"
    label={$_('entry.energy_label')}
    decrementLabel={$_('entry.energy_decrement')}
    incrementLabel={$_('entry.energy_increment')}
    bind:value={energy}
  />

  <ScaleSlider
    id="entry-stress"
    label={$_('entry.stress_label')}
    decrementLabel={$_('entry.stress_decrement')}
    incrementLabel={$_('entry.stress_increment')}
    bind:value={stress}
  />

  <label class="entry-field">
    <span class="entry-label">{$_('entry.work_context_label')}</span>
    <select class="input" value={workContext} on:change={onWorkContextChange} disabled={busy}>
      {#each WORK_CONTEXTS as wc}
        <option value={wc}>{$_(`entry.work_context.${wc}`)}</option>
      {/each}
    </select>
  </label>

  <TagPicker bind:selected={selectedTagIds} disabled={busy} />

  <SymptomChecker bind:selected={selectedSymptoms} disabled={busy} />

  <label class="entry-field">
    <span class="entry-label">{$_('entry.note_placeholder')}</span>
    <textarea
      class="input"
      rows="4"
      maxlength="4000"
      bind:value={note}
      placeholder={$_('entry.note_placeholder')}
      disabled={busy}
    ></textarea>
  </label>

  {#if errorKey}
    <p class="entry-error" role="alert">{$_(errorKey)}</p>
  {/if}

  <div class="entry-actions">
    <button type="button" class="btn" on:click={() => goto('/')} disabled={busy}>
      {$_('entry.cancel')}
    </button>
    <button type="submit" class="btn variant-filled-primary" disabled={busy || loading}>
      {busy ? $_('entry.save_busy') : existingEntryId ? $_('entry.update') : $_('entry.save')}
    </button>
  </div>
</form>

<style>
  .entry-header {
    margin-bottom: var(--space-6);
  }

  .entry-header-row {
    display: flex;
    align-items: flex-start;
    justify-content: space-between;
    gap: var(--space-4);
  }

  .entry-header-text {
    display: flex;
    flex-direction: column;
    gap: var(--space-2);
  }

  .entry-title {
    font-size: var(--text-lg);
    font-weight: 600;
  }

  .entry-subtitle {
    font-size: var(--text-sm);
    opacity: 0.75;
  }

  .entry-edit-hint {
    margin-top: 0.25rem;
    font-size: var(--text-xs, 0.78rem);
    color: rgb(var(--color-primary-600, 37 99 235));
    font-weight: 600;
  }

  .entry-form[data-loading='true'] {
    opacity: 0.65;
    pointer-events: none;
  }

  .entry-form {
    display: flex;
    flex-direction: column;
    gap: var(--space-5);
    max-width: 32rem;
    margin: 0 auto;
  }

  .entry-field {
    display: flex;
    flex-direction: column;
    gap: var(--space-2);
  }

  .entry-label {
    font-size: var(--text-sm);
    font-weight: 500;
  }

  .entry-error {
    font-size: var(--text-sm);
    color: rgb(var(--color-error-500));
    background: rgb(var(--color-error-500) / 0.1);
    border-left: 3px solid rgb(var(--color-error-500));
    padding: var(--space-2) var(--space-3);
    border-radius: 6px;
  }

  .entry-actions {
    display: flex;
    gap: var(--space-3);
    justify-content: flex-end;
    margin-top: var(--space-2);
  }
</style>
