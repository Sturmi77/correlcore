<script lang="ts">
  /**
   * /entries/new — daily-entry form (Issue #7) + auto-save (ADR-0013).
   *
   * Design constraints (DESIGN_DOCUMENT.md §6 + Issue #7 + ADR-0013):
   *   - 60-second rule: a default entry should be submittable in ≤ 60 s.
   *     We pre-fill mood/energy/stress to a neutral 3 and pick the date
   *     based on weekday → a typical homeoffice/office/weekend default.
   *   - A11y: each scale has +/- buttons in addition to the slider
   *     (see ScaleSlider).
   *   - Backdating is allowed up to 7 days; the date input is bounded
   *     accordingly.
   *   - **Auto-save (ADR-0013):** there is no explicit submit button.
   *     Every semantic change marks the form `dirty`; a debounced
   *     800 ms timer triggers a POST (first save) or PATCH (subsequent
   *     saves on the same `existingEntryId`). A status badge next to
   *     the headline reports the current save state.
   */

  import { onMount, onDestroy } from 'svelte';
  import { _ } from 'svelte-i18n';
  import { goto } from '$app/navigation';
  import { page } from '$app/stores';
  import { get } from 'svelte/store';
  import ScaleSlider from '$lib/components/entries/ScaleSlider.svelte';
  import TagPicker from '$lib/components/entries/TagPicker.svelte';
  import SymptomChecker from '$lib/components/entries/SymptomChecker.svelte';
  import SaveStatusBadge from '$lib/components/entries/SaveStatusBadge.svelte';
  import DayDeltaCard from '$lib/components/entries/DayDeltaCard.svelte';
  import ThemeToggle from '$lib/components/common/ThemeToggle.svelte';
  import {
    fetchEntryDelta,
    listEntries,
    updateEntry,
    type EntryDeltaResponse,
    type EntryResponse,
    type WorkContext,
  } from '$lib/api/entries';
  import { submitEntry } from '$lib/stores/entries';
  import { assignTagsToEntry, listTagsForEntry } from '$lib/api/tags';
  import {
    assignSymptomsToEntry,
    listSymptomsForEntry,
    type SymptomEntry,
  } from '$lib/api/symptoms';
  import { mapApiError, type ApiErrorMap } from '$lib/utils/error';
  import { createAutoSave, type AutoSaveState } from '$lib/utils/autoSave';

  // ---------------------------------------------------------------------
  // Form state
  // ---------------------------------------------------------------------

  function isoDate(d: Date): string {
    return d.toISOString().slice(0, 10);
  }

  /**
   * Validate a `?date=YYYY-MM-DD` query param and clamp to the
   * 7-day-back window. Invalid or out-of-range values fall back to
   * today silently — backdating > 7 days is blocked by the date input
   * anyway, so we don't need a user-facing error.
   */
  function resolveInitialDate(today: Date, queryDate: string | null): string {
    if (!queryDate) return isoDate(today);
    if (!/^\d{4}-\d{2}-\d{2}$/.test(queryDate)) return isoDate(today);
    const parsed = new Date(queryDate + 'T00:00:00');
    if (Number.isNaN(parsed.getTime())) return isoDate(today);
    const min = new Date(today.getTime() - 7 * 24 * 60 * 60 * 1000);
    if (parsed > today) return isoDate(today);
    if (parsed < min) return isoDate(today);
    return queryDate;
  }

  function defaultWorkContext(d: Date): WorkContext {
    const dow = d.getDay(); // 0 = Sun
    if (dow === 0 || dow === 6) return 'weekend';
    return 'homeoffice';
  }

  const today = new Date();
  const sevenDaysAgo = new Date(today.getTime() - 7 * 24 * 60 * 60 * 1000);

  // Initial date may come from `?date=YYYY-MM-DD` (ADR-0014: clicking
  // a recent-entries card pre-fills the picker). Reading the page
  // store via `get()` keeps the initial value synchronous; later
  // navigations land on this route with a fresh component instance.
  const initialDate = resolveInitialDate(today, get(page).url.searchParams.get('date'));
  let entryDate: string = initialDate;
  let moodScore = 3;
  let energy = 3;
  let stress = 3;
  let workContext: WorkContext = defaultWorkContext(new Date(initialDate + 'T00:00:00'));
  let note = '';
  let selectedTagIds: string[] = [];
  let selectedSymptoms: SymptomEntry[] = [];
  let errorKey: string | null = null;

  // Edit-mode: when the user navigates to a date that already has a
  // ``slot=day`` entry, we hydrate the form with the existing values so
  // the picker doubles as both "new" and "edit" view. The presence of
  // ``existingEntryId`` flips the auto-save handler from POST to PATCH
  // and re-uses the same replace-set tag/symptom assignment endpoints.
  let existingEntryId: string | null = null;
  let loading = false;
  // Debounce token for date-change loads: each load invocation
  // increments this; stale responses (user changed date again before
  // fetch returned) are discarded so the form doesn't snap back to
  // outdated data.
  let loadToken = 0;
  // While `true`, reactive watchers on form fields skip `markDirty()`
  // — needed during hydration so loading an existing entry doesn't
  // immediately schedule a save back to the server.
  let hydrating = false;
  let dayDelta: EntryDeltaResponse | null = null;
  let dayDeltaLoading = false;
  let dayDeltaToken = 0;

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
    dayDelta = null;
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

  async function refreshDayDelta(date: string) {
    const token = ++dayDeltaToken;
    dayDeltaLoading = true;
    try {
      const result = await fetchEntryDelta({ entry_date: date, slot: 'day' });
      if (token !== dayDeltaToken) return;
      dayDelta = result.today && result.previous ? result : null;
    } catch {
      if (token !== dayDeltaToken) return;
      dayDelta = null;
    } finally {
      if (token === dayDeltaToken) {
        dayDeltaLoading = false;
      }
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
    dayDeltaToken += 1;
    dayDelta = null;
    dayDeltaLoading = false;
    loading = true;
    hydrating = true;
    errorKey = null;
    // Cancel any in-flight auto-save scheduling — switching dates is a
    // hard form-reset, not an edit (ADR-0013 explicitly excludes date
    // changes from auto-save triggers).
    autoSave.reset();
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
      void refreshDayDelta(date);
    } catch (err) {
      if (myToken !== loadToken) return;
      errorKey = mapApiError(err, ERROR_MAP) ?? 'entry.error_load';
      resetForm(date);
    } finally {
      if (myToken === loadToken) {
        loading = false;
        // Defer turning hydration off to the next microtask: Svelte
        // reactivity flushes any pending field-change reactions
        // synchronously after this assignment, and we don't want those
        // to count as user edits.
        await Promise.resolve();
        hydrating = false;
      }
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

  // ---------------------------------------------------------------------
  // Auto-save controller (ADR-0013)
  // ---------------------------------------------------------------------

  interface FormSnapshot {
    entry_date: string;
    mood_score: number;
    energy: number;
    stress: number;
    work_context: WorkContext;
    note: string;
    selectedTagIds: string[];
    selectedSymptoms: SymptomEntry[];
  }

  function snapshot(): FormSnapshot {
    return {
      entry_date: entryDate,
      mood_score: moodScore,
      energy,
      stress,
      work_context: workContext,
      note: note.trim(),
      selectedTagIds: [...selectedTagIds],
      selectedSymptoms: selectedSymptoms.map((s) => ({ ...s })),
    };
  }

  /**
   * The actual persistence path. Mirrors the previous manual
   * ``onSubmit``: POST on first save (no ``existingEntryId``), PATCH
   * thereafter. Tag and symptom replace-sets always run after the
   * entry write so unchecked rows actually disappear server-side.
   */
  async function persist(snap: FormSnapshot): Promise<void> {
    let entryId: string;
    if (existingEntryId) {
      const updated = await updateEntry(existingEntryId, {
        mood_score: snap.mood_score,
        energy: snap.energy,
        stress: snap.stress,
        work_context: snap.work_context,
        note: snap.note,
      });
      entryId = updated.id;
    } else {
      const created = await submitEntry({
        entry_date: snap.entry_date,
        slot: 'day',
        mood_score: snap.mood_score,
        energy: snap.energy,
        stress: snap.stress,
        work_context: snap.work_context,
        note: snap.note ? snap.note : undefined,
      });
      entryId = created.id;
      // POST → PATCH-Flip: store the id so subsequent saves go via
      // updateEntry. This is the same flow that defused the 409 race
      // we hit in PR #117.
      existingEntryId = entryId;
    }

    await assignTagsToEntry(entryId, snap.selectedTagIds);
    await assignSymptomsToEntry(entryId, snap.selectedSymptoms);
    await refreshDayDelta(snap.entry_date);
  }

  const autoSave = createAutoSave<FormSnapshot>({
    getSnapshot: snapshot,
    save: persist,
  });
  const autoSaveState = autoSave.state;

  let autoSaveSnap: AutoSaveState = { status: 'idle', lastSavedAt: null, lastError: null };
  $: autoSaveSnap = $autoSaveState;

  function markDirty() {
    if (hydrating || loading) return;
    // Per-route guard: don't try to auto-save when the user has dialed
    // into a load-error — they need to retry the load first.
    autoSave.markDirty();
  }

  // Reactive watchers: any edit to a tracked field marks the form
  // dirty. We deliberately keep `entryDate` out of this list — date
  // changes trigger a full hydration via `loadForDate` instead.
  $: {
    moodScore;
    energy;
    stress;
    workContext;
    note;
    selectedTagIds;
    selectedSymptoms;
    markDirty();
  }

  // ---------------------------------------------------------------------
  // beforeunload: warn on dirty / saving
  // ---------------------------------------------------------------------

  function onBeforeUnload(ev: BeforeUnloadEvent) {
    const s = autoSave.peek().status;
    if (s === 'dirty' || s === 'saving') {
      // Try to flush synchronously so the browser at least kicks off
      // the request before tearing down the page (best-effort: most
      // browsers will still close the tab without awaiting).
      void autoSave.flushNow();
      ev.preventDefault();
      ev.returnValue = '';
    }
  }

  function onCancel() {
    // Cancel button leaves the page; auto-save has already persisted
    // any committed dirty state, so we just navigate.
    void goto('/');
  }

  onMount(() => {
    // Focus the mood slider so a typical "log my day" flow needs zero
    // clicks (still relevant under auto-save).
    const el = document.getElementById('entry-mood');
    el?.focus();
    window.addEventListener('beforeunload', onBeforeUnload);
  });

  onDestroy(() => {
    if (typeof window !== 'undefined') {
      window.removeEventListener('beforeunload', onBeforeUnload);
    }
    autoSave.destroy();
  });

  // Surface auto-save errors via the existing error-key channel for the
  // error banner; mapping unknown errors to the generic key keeps the
  // user from seeing raw stack traces.
  $: if (autoSaveSnap.status === 'error' && autoSaveSnap.lastError) {
    errorKey = 'entry.error_generic';
  } else if (autoSaveSnap.status === 'saving' || autoSaveSnap.status === 'saved') {
    errorKey = null;
  }
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
    <div class="entry-header-tools">
      <SaveStatusBadge
        status={autoSaveSnap.status}
        lastSavedAt={autoSaveSnap.lastSavedAt}
        lastError={autoSaveSnap.lastError}
        onRetry={() => void autoSave.retry()}
      />
      <ThemeToggle testId="entry-theme-toggle" />
    </div>
  </div>
</header>

<form
  class="entry-form"
  novalidate
  aria-busy={loading || autoSaveSnap.status === 'saving'}
  data-loading={loading ? 'true' : 'false'}
  data-autosave-status={autoSaveSnap.status}
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
    />
  </label>

  <DayDeltaCard delta={dayDelta} loading={dayDeltaLoading} />

  <ScaleSlider
    id="entry-mood"
    label={$_('entry.mood_label')}
    decrementLabel={$_('entry.mood_decrement')}
    incrementLabel={$_('entry.mood_increment')}
    scaleType="mood"
    bind:value={moodScore}
  />

  <ScaleSlider
    id="entry-energy"
    label={$_('entry.energy_label')}
    decrementLabel={$_('entry.energy_decrement')}
    incrementLabel={$_('entry.energy_increment')}
    scaleType="energy"
    bind:value={energy}
  />

  <ScaleSlider
    id="entry-stress"
    label={$_('entry.stress_label')}
    decrementLabel={$_('entry.stress_decrement')}
    incrementLabel={$_('entry.stress_increment')}
    scaleType="stress"
    bind:value={stress}
  />

  <label class="entry-field">
    <span class="entry-label">{$_('entry.work_context_label')}</span>
    <select class="input" value={workContext} on:change={onWorkContextChange}>
      {#each WORK_CONTEXTS as wc}
        <option value={wc}>{$_(`entry.work_context.${wc}`)}</option>
      {/each}
    </select>
  </label>

  <TagPicker bind:selected={selectedTagIds} />

  <SymptomChecker bind:selected={selectedSymptoms} />

  <label class="entry-field">
    <span class="entry-label">{$_('entry.note_placeholder')}</span>
    <textarea
      class="input"
      rows="4"
      maxlength="4000"
      bind:value={note}
      placeholder={$_('entry.note_placeholder')}
    ></textarea>
  </label>

  {#if errorKey}
    <p class="entry-error" role="alert">{$_(errorKey)}</p>
  {/if}

  <div class="entry-actions">
    <button type="button" class="btn" on:click={onCancel} data-testid="entry-cancel">
      {$_('entry.cancel')}
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

  .entry-header-tools {
    display: flex;
    align-items: center;
    gap: var(--space-3);
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
