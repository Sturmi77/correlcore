<script lang="ts">
  /**
   * EntryForm — daily entry (Issue #7) + auto-save (ADR-0013).
   * Used on `/entries/new` (page) and inside `EntrySheet` from Home (M3.5 Sprint 3).
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

  import { createEventDispatcher, onDestroy, onMount } from 'svelte';
  import { _ } from 'svelte-i18n';
  import { goto } from '$app/navigation';
  import ScaleSlider from '$lib/components/entries/ScaleSlider.svelte';
  import TagPicker from '$lib/components/entries/TagPicker.svelte';
  import OnboardingTagSuggestions from '$lib/components/entries/OnboardingTagSuggestions.svelte';
  import SymptomChecker from '$lib/components/entries/SymptomChecker.svelte';
  import SaveStatusBadge from '$lib/components/entries/SaveStatusBadge.svelte';
  import DayDeltaCard from '$lib/components/entries/DayDeltaCard.svelte';
  import Button from '$lib/components/common/Button.svelte';
  import ThemeToggle from '$lib/components/common/ThemeToggle.svelte';
  import SegmentedControl from '$lib/components/common/SegmentedControl.svelte';
  import {
    fetchEntryDelta,
    listEntries,
    updateEntry,
    type EntryDeltaResponse,
    type EntryResponse,
    type EntrySlot,
    type WorkContext,
  } from '$lib/api/entries';
  import { submitEntry } from '$lib/stores/entries';
  import { assignTagsToEntry, listTagsForEntry } from '$lib/api/tags';
  import {
    completeOnboarding,
    fetchTagSuggestions,
    type TagSuggestion,
    type TagSuggestionGroup,
  } from '$lib/api/onboarding';
  import {
    assignSymptomsToEntry,
    listSymptomsForEntry,
    type SymptomEntry,
  } from '$lib/api/symptoms';
  import { mapApiError, type ApiErrorMap } from '$lib/utils/error';
  import { createAutoSave, type AutoSaveState } from '$lib/utils/autoSave';
  import { refreshTags } from '$lib/stores/tags';
  import { defaultWorkContextForDate } from '$lib/utils/workContext';
  import { isoDate } from '$lib/utils/entryForm';
  import { NEUTRAL_SCALE_DEFAULT, scaleDefaultsFromPrevious } from '$lib/utils/entrySmartDefaults';
  import { setEntryOpenMode, type EntryOpenMode } from '$lib/utils/entryOpenMode';
  import { canUseOfflineSync } from '$lib/offline/featureFlag';
  import { onLocalEntrySaved, scheduleSync, syncOrchestrator } from '$lib/offline/syncOrchestrator';
  import {
    findLocalEntryByDateSlot,
    localEntryToFormFields,
    saveEntryOffline,
    type EntryFormSnapshot,
  } from '$lib/stores/entriesOffline';

  export let mode: 'page' | 'sheet' = 'page';
  /** Quick capture hides tags, symptoms, and optional extras (O-25). */
  export let openMode: EntryOpenMode = 'full';
  /** When true, show onboarding tag suggestions and finalize onboarding on first save. */
  export let onboardingTagsEnabled = false;
  /** ISO date `YYYY-MM-DD` for the entry being edited. */
  export let initialDate: string;

  const dispatch = createEventDispatcher<{ close: void; saved: void }>();

  const today = new Date();
  const sevenDaysAgo = new Date(today.getTime() - 7 * 24 * 60 * 60 * 1000);

  let entryDate: string = initialDate;
  // Keep SSR and the first client render identical; viewport adaptation happens on mount.
  let compactEntry = false;
  /** Note + cycle day only; tags/symptoms/time slots stay visible (O-21). */
  let showOptionalExtras = !compactEntry;
  let optionalTouched = false;
  let selectedSlot: EntrySlot = 'day';
  let moodScore = NEUTRAL_SCALE_DEFAULT;
  let energy = NEUTRAL_SCALE_DEFAULT;
  let stress = NEUTRAL_SCALE_DEFAULT;
  let cycleDay: number | null = null;
  let workContext: WorkContext = defaultWorkContextForDate(new Date(initialDate + 'T00:00:00'));
  let note = '';
  let selectedTagIds: string[] = [];
  let selectedSymptoms: SymptomEntry[] = [];
  let errorKey: string | null = null;
  let cycleDayInvalid = false;
  let offline = typeof navigator !== 'undefined' ? !navigator.onLine : false;
  let mobileMedia: MediaQueryList | null = null;

  // Edit-mode: when the user navigates to a date/slot that already has an
  // entry, we hydrate the form with the existing values so
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
  let applyingSmartDefaults = false;
  let dayDelta: EntryDeltaResponse | null = null;
  let dayDeltaLoading = false;
  let dayDeltaToken = 0;
  let offlineSyncConflictKey: string | null = null;
  let suggestionGroups: TagSuggestionGroup[] = [];
  let selectedSuggestions = new Map<string, TagSuggestion>();
  let suggestionsLoading = false;
  let onboardingMarkedComplete = false;

  $: offlineSyncBadge = $syncOrchestrator.badge;
  $: offlineSyncConflictKey = $syncOrchestrator.conflictNote;
  $: selectedSuggestionSlugs = new Set(selectedSuggestions.keys());

  // Keep the work-context default in sync if the user picks a different
  // day, but only until they manually change it themselves.
  let workContextTouched = false;
  $: if (!workContextTouched && entryDate && !existingEntryId) {
    const d = new Date(entryDate + 'T00:00:00');
    if (!Number.isNaN(d.getTime())) {
      workContext = defaultWorkContextForDate(d);
    }
  }

  /**
   * Reset the form to the neutral default for a date with no entry yet.
   * Called when the user picks a date and the API returns no match.
   */
  function resetForm(forDate: string, slot: EntrySlot = 'day') {
    existingEntryId = null;
    dayDelta = null;
    moodScore = NEUTRAL_SCALE_DEFAULT;
    energy = NEUTRAL_SCALE_DEFAULT;
    stress = NEUTRAL_SCALE_DEFAULT;
    selectedSlot = slot;
    cycleDay = null;
    cycleDayInvalid = false;
    note = '';
    selectedTagIds = [];
    selectedSymptoms = [];
    workContextTouched = false;
    const d = new Date(forDate + 'T00:00:00');
    if (!Number.isNaN(d.getTime())) {
      workContext = defaultWorkContextForDate(d);
    }
  }

  async function applySmartDefaults(date: string, slot: EntrySlot, token: number): Promise<void> {
    let appliedDefaults = false;
    try {
      const result = await fetchEntryDelta({ entry_date: date, slot });
      if (token !== loadToken || existingEntryId || autoSave.peek().status !== 'idle') return;
      const defaults = scaleDefaultsFromPrevious(result.previous);
      if (!defaults) return;
      applyingSmartDefaults = true;
      appliedDefaults = true;
      moodScore = defaults.mood_score;
      energy = defaults.energy;
      stress = defaults.stress;
      await Promise.resolve();
    } catch {
      // Keep neutral defaults when the comparison endpoint is unavailable.
    } finally {
      if (appliedDefaults) {
        applyingSmartDefaults = false;
      }
    }
  }

  async function refreshDayDelta(date: string, slot: EntrySlot = selectedSlot) {
    const token = ++dayDeltaToken;
    dayDeltaLoading = true;
    try {
      const result = await fetchEntryDelta({ entry_date: date, slot });
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
  async function loadForDate(date: string, slot: EntrySlot = 'day') {
    const myToken = ++loadToken;
    dayDeltaToken += 1;
    dayDelta = null;
    dayDeltaLoading = false;
    loading = true;
    hydrating = true;
    errorKey = null;
    selectedSlot = slot;
    // Cancel any in-flight auto-save scheduling — switching dates is a
    // hard form-reset, not an edit (ADR-0013 explicitly excludes date
    // changes from auto-save triggers).
    autoSave.reset();
    try {
      if (canUseOfflineSync()) {
        const local = await findLocalEntryByDateSlot(date, slot);
        if (local) {
          existingEntryId = local.id;
          const fields = localEntryToFormFields(local);
          selectedSlot = fields.selectedSlot;
          moodScore = fields.moodScore;
          energy = fields.energy;
          stress = fields.stress;
          cycleDay = fields.cycleDay;
          cycleDayInvalid = false;
          workContext = fields.workContext;
          workContextTouched = true;
          note = fields.note;
          selectedTagIds = fields.selectedTagIds;
          selectedSymptoms = fields.selectedSymptoms;
          if (typeof navigator !== 'undefined' && navigator.onLine) {
            void refreshDayDelta(date, selectedSlot);
          }
          return;
        }
      }

      const matches = await listEntries({
        start_date: date,
        end_date: date,
        limit: 5,
      });
      if (myToken !== loadToken) return;
      const matchingEntry = matches.find(
        (e: EntryResponse) => e.entry_date === date && e.slot === slot
      );
      if (!matchingEntry) {
        resetForm(date, slot);
        void applySmartDefaults(date, slot, myToken);
        return;
      }
      existingEntryId = matchingEntry.id;
      selectedSlot = matchingEntry.slot;
      moodScore = matchingEntry.mood_score;
      energy = matchingEntry.energy;
      stress = matchingEntry.stress;
      cycleDay = matchingEntry.cycle_day;
      cycleDayInvalid = false;
      workContext = matchingEntry.work_context;
      // Mark touched so the date-change reactive block doesn't reset it
      // back to the weekday default.
      workContextTouched = true;
      note = matchingEntry.note ?? '';

      // Tags + symptoms load in parallel; both wrapped so one slow
      // network blip doesn't keep the other from rendering.
      const [tagsRes, symRes] = await Promise.allSettled([
        listTagsForEntry(matchingEntry.id),
        listSymptomsForEntry(matchingEntry.id),
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
      void refreshDayDelta(date, selectedSlot);
    } catch (err) {
      if (myToken !== loadToken) return;
      errorKey = mapApiError(err, ERROR_MAP) ?? 'entry.error_load';
      resetForm(date, slot);
    } finally {
      if (myToken === loadToken) {
        loading = false;
        // Defer turning hydration off to the next microtask: Svelte
        // reactivity flushes any pending field-change reactions
        // synchronously after this assignment, and we don't want those
        // to count as user edits.
        await Promise.resolve();
        hydrating = false;
        syncOptionalExtrasVisibility();
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

  function onCycleDayInput(e: Event) {
    const value = (e.currentTarget as HTMLInputElement).value;
    const parsed = Number(value);
    cycleDay = value === '' || !Number.isFinite(parsed) ? null : parsed;
    cycleDayInvalid = cycleDay !== null && (cycleDay < 1 || cycleDay > 35);
  }

  function hasOptionalExtrasContent(): boolean {
    return note.trim().length > 0 || cycleDay !== null;
  }

  function toggleOptionalExtras() {
    optionalTouched = true;
    showOptionalExtras = !showOptionalExtras;
  }

  function syncOptionalExtrasVisibility() {
    if (!compactEntry) {
      showOptionalExtras = true;
      return;
    }
    if (!optionalTouched) {
      showOptionalExtras = hasOptionalExtrasContent();
    }
  }

  function syncCompactEntry() {
    compactEntry = Boolean(mobileMedia?.matches);
    syncOptionalExtrasVisibility();
  }

  function handleOnline() {
    offline = false;
    if (canUseOfflineSync()) {
      scheduleSync();
    }
    if (onboardingTagsEnabled && !onboardingMarkedComplete) {
      markDirty();
    }
  }

  function handleOffline() {
    offline = true;
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
  const ENTRY_SLOTS: Exclude<EntrySlot, 'day'>[] = ['morning', 'noon', 'evening'];

  $: quickEntry = openMode === 'quick';
  $: openModeOptions = [
    { id: 'quick' as const, label: $_('entry.open_mode.quick'), testId: 'entry-open-mode-quick' },
    { id: 'full' as const, label: $_('entry.open_mode.full'), testId: 'entry-open-mode-full' },
  ];

  function setOpenMode(next: EntryOpenMode): void {
    openMode = next;
    setEntryOpenMode(next);
  }

  function setSlot(slot: EntrySlot) {
    const nextSlot = selectedSlot === slot ? 'day' : slot;
    void loadForDate(entryDate, nextSlot);
  }

  // ---------------------------------------------------------------------
  // Auto-save controller (ADR-0013)
  // ---------------------------------------------------------------------

  interface FormSnapshot extends EntryFormSnapshot {}

  function snapshot(): FormSnapshot {
    return {
      entry_date: entryDate,
      mood_score: moodScore,
      energy,
      stress,
      slot: selectedSlot,
      cycle_day: cycleDay ?? null,
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
    if (snap.cycle_day !== null && (snap.cycle_day < 1 || snap.cycle_day > 35)) {
      throw new Error('invalid_cycle_day');
    }
    const resolvedSnap = await resolveOnboardingTags(snap);

    if (canUseOfflineSync()) {
      const result = await saveEntryOffline(existingEntryId, resolvedSnap);
      existingEntryId = result.entryId;
      onLocalEntrySaved();
      if (typeof navigator !== 'undefined' && navigator.onLine) {
        void refreshDayDelta(resolvedSnap.entry_date, resolvedSnap.slot);
      }
      return;
    }

    let entryId: string;
    if (existingEntryId) {
      const updated = await updateEntry(existingEntryId, {
        mood_score: resolvedSnap.mood_score,
        energy: resolvedSnap.energy,
        stress: resolvedSnap.stress,
        slot: resolvedSnap.slot,
        cycle_day: resolvedSnap.cycle_day,
        work_context: resolvedSnap.work_context,
        note: resolvedSnap.note,
      });
      entryId = updated.id;
    } else {
      const created = await submitEntry({
        entry_date: resolvedSnap.entry_date,
        slot: resolvedSnap.slot,
        mood_score: resolvedSnap.mood_score,
        energy: resolvedSnap.energy,
        stress: resolvedSnap.stress,
        cycle_day: resolvedSnap.cycle_day,
        work_context: resolvedSnap.work_context,
        note: resolvedSnap.note ? resolvedSnap.note : undefined,
      });
      entryId = created.id;
      // POST → PATCH-Flip: store the id so subsequent saves go via
      // updateEntry. This is the same flow that defused the 409 race
      // we hit in PR #117.
      existingEntryId = entryId;
    }

    await assignTagsToEntry(entryId, resolvedSnap.selectedTagIds);
    await assignSymptomsToEntry(entryId, resolvedSnap.selectedSymptoms);
    await refreshDayDelta(resolvedSnap.entry_date, resolvedSnap.slot);
  }

  async function resolveOnboardingTags(snap: FormSnapshot): Promise<FormSnapshot> {
    if (!onboardingTagsEnabled || onboardingMarkedComplete) return snap;
    if (canUseOfflineSync() && typeof navigator !== 'undefined' && !navigator.onLine) {
      return snap;
    }
    const tags = [...selectedSuggestions.values()].map((tag) => ({
      slug: tag.slug,
      name: tag.name,
      category: tag.category,
      icon: tag.icon,
      color: tag.color,
    }));
    const result = await completeOnboarding(tags);
    onboardingMarkedComplete = true;
    await refreshTags();
    const createdIds = result.created_tags.map((tag) => tag.id);
    return {
      ...snap,
      selectedTagIds: [...new Set([...snap.selectedTagIds, ...createdIds])],
    };
  }

  function toggleOnboardingSuggestion(tag: TagSuggestion) {
    selectedSuggestions = new Map(selectedSuggestions);
    if (selectedSuggestions.has(tag.slug)) selectedSuggestions.delete(tag.slug);
    else selectedSuggestions.set(tag.slug, tag);
    markDirty();
  }

  async function loadOnboardingSuggestions() {
    if (!onboardingTagsEnabled) return;
    suggestionsLoading = true;
    try {
      const response = await fetchTagSuggestions();
      suggestionGroups = response.groups;
    } catch {
      suggestionGroups = [];
    } finally {
      suggestionsLoading = false;
    }
  }

  const autoSave = createAutoSave<FormSnapshot>({
    getSnapshot: snapshot,
    save: persist,
  });
  const autoSaveState = autoSave.state;

  let autoSaveSnap: AutoSaveState = { status: 'idle', lastSavedAt: null, lastError: null };
  $: autoSaveSnap = $autoSaveState;

  function markDirty() {
    if (hydrating || loading || applyingSmartDefaults) return;
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
    selectedSlot;
    cycleDay;
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

  export async function requestClose(): Promise<boolean> {
    const status = autoSave.peek().status;
    if (status === 'dirty' || status === 'saving') {
      const leave =
        typeof window !== 'undefined' && window.confirm($_('entry.autosave.leave_warning'));
      if (!leave) return false;
      await autoSave.flushNow();
    }
    if (mode === 'sheet') {
      dispatch('close');
    } else {
      void goto('/');
    }
    return true;
  }

  function onCancel() {
    void requestClose();
  }

  onMount(() => {
    // Focus the mood slider so a typical "log my day" flow needs zero
    // clicks (still relevant under auto-save).
    const el = document.getElementById('entry-mood');
    el?.focus();
    void loadOnboardingSuggestions();
    mobileMedia = window.matchMedia('(max-width: 767px)');
    syncCompactEntry();
    mobileMedia.addEventListener('change', syncCompactEntry);
    window.addEventListener('online', handleOnline);
    window.addEventListener('offline', handleOffline);
    window.addEventListener('beforeunload', onBeforeUnload);
  });

  onDestroy(() => {
    if (typeof window !== 'undefined') {
      window.removeEventListener('beforeunload', onBeforeUnload);
      window.removeEventListener('online', handleOnline);
      window.removeEventListener('offline', handleOffline);
    }
    mobileMedia?.removeEventListener('change', syncCompactEntry);
    autoSave.destroy();
  });

  // Surface auto-save errors via the existing error-key channel for the
  // error banner; mapping unknown errors to the generic key keeps the
  // user from seeing raw stack traces.
  $: if (autoSaveSnap.status === 'error' && autoSaveSnap.lastError) {
    if (!canUseOfflineSync() && autoSaveSnap.lastError.startsWith('Network error on ')) {
      offline = true;
    }
    errorKey = 'entry.error_generic';
  } else if (autoSaveSnap.status === 'saving' || autoSaveSnap.status === 'saved') {
    if (typeof navigator === 'undefined' || navigator.onLine) offline = false;
    errorKey = null;
  }

  let lastAutoSaveStatus: AutoSaveState['status'] = 'idle';
  $: if (lastAutoSaveStatus === 'saving' && autoSaveSnap.status === 'saved') {
    dispatch('saved');
  }
  $: lastAutoSaveStatus = autoSaveSnap.status;
</script>

<header class="entry-header" class:entry-header--sheet={mode === 'sheet'}>
  <div class="entry-header-row">
    <div class="entry-header-text">
      {#if mode === 'sheet'}
        <h2 id="entry-sheet-title" class="entry-title">{$_('entry.sheet.title')}</h2>
      {:else}
        <h1 class="entry-title">{$_('entry.title')}</h1>
        <p class="entry-subtitle">{$_('entry.subtitle')}</p>
      {/if}
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
        {offline}
        offlineSyncBadge={canUseOfflineSync() ? offlineSyncBadge : null}
        onRetry={() => {
          if (canUseOfflineSync()) {
            scheduleSync();
            return;
          }
          void autoSave.retry();
        }}
      />
      {#if mode === 'page'}
        <ThemeToggle testId="entry-theme-toggle" />
      {/if}
    </div>
  </div>
  {#if mode === 'sheet'}
    <SegmentedControl
      value={openMode}
      options={openModeOptions}
      ariaLabel={$_('entry.open_mode.label')}
      testId="entry-open-mode-control"
      on:change={(event) => setOpenMode(event.detail.value as EntryOpenMode)}
    />
  {/if}
</header>

<form
  class="entry-form"
  class:entry-form--sheet={mode === 'sheet'}
  novalidate
  aria-busy={loading || autoSaveSnap.status === 'saving'}
  data-loading={loading ? 'true' : 'false'}
  data-autosave-status={autoSaveSnap.status}
>
  <section class="entry-section" aria-labelledby="entry-section-date">
    <h2 id="entry-section-date" class="entry-section__title">{$_('entry.section.date')}</h2>
    <div class="entry-date-row">
      <label class="entry-field entry-field--date">
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
      <div class="entry-chip-row" role="group" aria-label={$_('entry.time_slot.label')}>
        {#each ENTRY_SLOTS as slot}
          <button
            type="button"
            class:active={selectedSlot === slot}
            aria-pressed={selectedSlot === slot}
            on:click={() => setSlot(slot)}
          >
            {$_(`entry.time_slot.${slot}`)}
          </button>
        {/each}
      </div>
    </div>
    <p class="entry-hint">{$_('entry.time_slot.hint')}</p>
  </section>

  {#if onboardingTagsEnabled}
    <section class="entry-section" aria-labelledby="entry-section-onboarding-tags">
      <OnboardingTagSuggestions
        groups={suggestionGroups}
        loading={suggestionsLoading}
        selectedSlugs={selectedSuggestionSlugs}
        disabled={loading || autoSaveSnap.status === 'saving'}
        on:toggle={(event) => toggleOnboardingSuggestion(event.detail)}
      />
    </section>
  {/if}

  <section class="entry-section" aria-labelledby="entry-section-metrics">
    <h2 id="entry-section-metrics" class="entry-section__title">{$_('entry.section.metrics')}</h2>
    <div class="entry-section__stack">
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
    </div>
  </section>

  <section class="entry-section" aria-labelledby="entry-section-work">
    <h2 id="entry-section-work" class="entry-section__title">{$_('entry.section.work_context')}</h2>
    {#if !workContextTouched}
      <p class="entry-hint" id="entry-work-context-hint">
        {$_('entry.work_context_required_hint')}
      </p>
    {/if}
    <label class="entry-field">
      <span class="entry-label">{$_('entry.work_context_label')}</span>
      <select
        class="input"
        value={workContext}
        on:change={onWorkContextChange}
        aria-describedby={workContextTouched ? undefined : 'entry-work-context-hint'}
      >
        {#each WORK_CONTEXTS as wc}
          <option value={wc}>{$_(`entry.work_context.${wc}`)}</option>
        {/each}
      </select>
    </label>
  </section>

  {#if !quickEntry}
    <section class="entry-section" aria-labelledby="entry-section-tags">
      <h2 id="entry-section-tags" class="entry-section__title">{$_('entry.section.tags')}</h2>
      <TagPicker bind:selected={selectedTagIds} />
    </section>

    <section class="entry-section" aria-labelledby="entry-section-symptoms">
      <h2 id="entry-section-symptoms" class="entry-section__title">
        {$_('entry.section.symptoms')}
      </h2>
      <SymptomChecker bind:selected={selectedSymptoms} />
    </section>

    {#if compactEntry}
      <Button
        type="button"
        variant="ghost"
        fullWidth
        className="entry-optional-extras-toggle"
        data-testid="entry-optional-extras-toggle"
        aria-expanded={showOptionalExtras}
        aria-controls="entry-optional-extras"
        on:click={toggleOptionalExtras}
      >
        {showOptionalExtras ? $_('entry.optional_extras_hide') : $_('entry.optional_extras_toggle')}
      </Button>
    {/if}

    {#if showOptionalExtras}
      <div id="entry-optional-extras" class="entry-optional-extras">
        <section class="entry-section" aria-labelledby="entry-section-note">
          <h2 id="entry-section-note" class="entry-section__title">{$_('entry.section.note')}</h2>
          <label class="entry-field">
            <span class="sr-only">{$_('entry.note_placeholder')}</span>
            <textarea
              class="input"
              rows="4"
              maxlength="4000"
              bind:value={note}
              placeholder={$_('entry.note_placeholder')}
            ></textarea>
          </label>
        </section>

        <section class="entry-section" aria-labelledby="entry-section-cycle">
          <h2 id="entry-section-cycle" class="entry-section__title">{$_('entry.section.cycle')}</h2>
          <label class="entry-field">
            <span class="entry-label">{$_('entry.cycle_day.label')}</span>
            <input
              type="number"
              class="input"
              min="1"
              max="35"
              value={cycleDay ?? ''}
              on:input={onCycleDayInput}
              aria-invalid={cycleDayInvalid}
              aria-describedby={cycleDayInvalid ? 'entry-cycle-error' : 'entry-cycle-hint'}
              placeholder={$_('entry.cycle_day.placeholder')}
            />
          </label>
          <p id="entry-cycle-hint" class="entry-hint">{$_('entry.cycle_day.hint')}</p>
          {#if cycleDayInvalid}
            <p id="entry-cycle-error" class="entry-error" role="alert">
              {$_('entry.cycle_day.error_range')}
            </p>
          {/if}
        </section>
      </div>
    {/if}

    <section class="entry-section" aria-labelledby="entry-section-delta">
      <h2 id="entry-section-delta" class="entry-section__title">{$_('entry.section.delta')}</h2>
      <DayDeltaCard delta={dayDelta} loading={dayDeltaLoading} />
    </section>
  {/if}

  {#if offlineSyncConflictKey}
    <p class="entry-hint" role="status" data-testid="entry-sync-conflict-note">
      {$_(offlineSyncConflictKey)}
    </p>
  {/if}

  {#if errorKey}
    <p class="entry-error" role="alert">{$_(errorKey)}</p>
  {/if}

  <div class="entry-actions">
    <Button type="button" variant="secondary" on:click={onCancel} data-testid="entry-cancel">
      {mode === 'sheet' ? $_('entry.sheet.done') : $_('entry.cancel')}
    </Button>
  </div>
</form>

<style>
  .entry-header {
    margin-bottom: var(--space-6);
  }

  .entry-header--sheet {
    margin-bottom: var(--space-4);
  }

  .entry-form--sheet {
    gap: var(--space-4);
    max-width: none;
    margin: 0;
  }

  .entry-optional-extras {
    display: flex;
    flex-direction: column;
    gap: var(--space-6);
  }

  :global(.entry-optional-extras-toggle) {
    width: 100%;
    justify-content: center;
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
    color: var(--color-primary);
    font-weight: 600;
  }

  .entry-form[data-loading='true'] {
    opacity: 0.65;
    pointer-events: none;
  }

  .entry-form {
    display: flex;
    flex-direction: column;
    gap: var(--space-6);
    max-width: 32rem;
    margin: 0 auto;
  }

  .entry-section {
    display: flex;
    flex-direction: column;
    gap: var(--space-4);
    padding: var(--space-4);
    border: 1px solid var(--color-border);
    border-radius: var(--radius-md);
    background: var(--color-surface);
  }

  .entry-section__title {
    margin: 0;
    font-size: var(--text-sm);
    font-weight: 600;
    color: var(--color-fg);
    letter-spacing: 0.02em;
    text-transform: uppercase;
  }

  .entry-section__stack {
    display: flex;
    flex-direction: column;
    gap: var(--space-5);
  }

  .entry-hint {
    margin: 0;
    font-size: var(--text-sm);
    line-height: 1.45;
    color: var(--color-text);
    padding: var(--space-2) var(--space-3);
    border-radius: var(--radius-sm);
    background: var(--color-surface-2);
    border-left: 3px solid var(--color-primary);
  }

  .entry-field {
    display: flex;
    flex-direction: column;
    gap: var(--space-2);
  }

  .entry-date-row {
    display: grid;
    gap: var(--space-3);
  }

  .entry-field--date {
    min-width: 0;
  }

  @media (min-width: 480px) {
    .entry-date-row {
      grid-template-columns: minmax(10rem, 14rem) 1fr;
      align-items: end;
    }
  }

  .entry-chip-row {
    display: flex;
    gap: var(--space-2);
    overflow-x: auto;
    padding-bottom: var(--space-1);
  }

  .entry-chip-row button {
    min-height: 44px;
    border: 1px solid var(--color-border);
    border-radius: var(--radius-sm);
    background: var(--color-surface-2);
    color: var(--color-text);
    padding: var(--space-2) var(--space-3);
    white-space: nowrap;
    cursor: pointer;
  }

  .entry-chip-row button.active {
    border-color: var(--color-primary);
    background: var(--color-primary-soft);
    color: var(--color-primary);
    font-weight: 650;
  }

  .entry-label {
    font-size: var(--text-sm);
    font-weight: 500;
  }

  .entry-error {
    font-size: var(--text-sm);
    color: var(--color-error);
    background: var(--color-error-highlight);
    border-left: 3px solid var(--color-error);
    padding: var(--space-2) var(--space-3);
    border-radius: 6px;
  }

  .entry-actions {
    display: flex;
    gap: var(--space-3);
    justify-content: flex-end;
    margin-top: var(--space-2);
  }

  @media (max-width: 767px) {
    .entry-header-row {
      flex-direction: column;
    }

    .entry-header-tools {
      width: 100%;
      justify-content: space-between;
      flex-wrap: wrap;
    }

    .entry-form,
    .entry-optional-extras {
      gap: var(--screen-gap);
    }

    .entry-section {
      padding: 0 0 var(--screen-gap);
      border: 0;
      border-bottom: 1px solid var(--color-border);
      border-radius: 0;
      background: transparent;
    }

    .entry-actions :global(.ui-button) {
      width: 100%;
    }
  }
</style>
