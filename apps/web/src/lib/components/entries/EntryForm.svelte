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
  import { get } from 'svelte/store';
  import { _ } from 'svelte-i18n';
  import { goto } from '$app/navigation';
  import ScaleSlider from '$lib/components/entries/ScaleSlider.svelte';
  import TagPicker from '$lib/components/entries/TagPicker.svelte';
  import OnboardingTagSuggestions from '$lib/components/entries/OnboardingTagSuggestions.svelte';
  import SymptomChecker from '$lib/components/entries/SymptomChecker.svelte';
  import SaveStatusBadge from '$lib/components/entries/SaveStatusBadge.svelte';
  import DayDeltaCard from '$lib/components/entries/DayDeltaCard.svelte';
  import NoteMarkerChips from '$lib/components/entries/NoteMarkerChips.svelte';
  import Button from '$lib/components/common/Button.svelte';
  import ThemeToggle from '$lib/components/common/ThemeToggle.svelte';
  import SegmentedControl from '$lib/components/common/SegmentedControl.svelte';
  import {
    fetchEntryDelta,
    listEntries,
    updateEntry,
    type BleedingLevel,
    type EntryDeltaResponse,
    type EntryResponse,
    type EntrySlot,
    type WorkContext,
  } from '$lib/api/entries';
  import type { WorkContextTypical } from '$lib/api/profile';
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
  import { computeNoteSummaryShort } from '$lib/utils/noteSummary';
  import {
    addNoteMarker,
    deleteNoteMarker,
    listNoteMarkerSuggestions,
    type EntryNoteMarkerResponse,
    type NoteVisibility,
  } from '$lib/api/noteMarkers';
  import { createAutoSave, type AutoSaveState } from '$lib/utils/autoSave';
  import { refreshTags } from '$lib/stores/tags';
  import { defaultWorkContextForDate } from '$lib/utils/workContext';
  import { isoDate, mergeUnresolvedSymptoms, mergeUnresolvedTagIds } from '$lib/utils/entryForm';
  import { NEUTRAL_SCALE_DEFAULT, scaleDefaultsFromPrevious } from '$lib/utils/entrySmartDefaults';
  import { setEntryOpenMode, type EntryOpenMode } from '$lib/utils/entryOpenMode';
  import { canUseOfflineSync } from '$lib/offline/featureFlag';
  import { auth } from '$lib/stores/auth';
  import { connectivity } from '$lib/stores/connectivity';
  import { onLocalEntrySaved, scheduleSync, syncOrchestrator } from '$lib/offline/syncOrchestrator';
  import {
    findLocalEntryByDateSlot,
    hydrateServerEntryFromApi,
    localEntryToFormFields,
    saveEntryOffline,
    shouldPreferLocalEntry,
    type EntryFormSnapshot,
  } from '$lib/stores/entriesOffline';
  import {
    clearOnboardingSuggestionStash,
    readOnboardingSuggestionStash,
    writeOnboardingSuggestionStash,
  } from '$lib/utils/onboardingSuggestionStash';

  export let mode: 'page' | 'sheet' = 'page';
  /** Quick capture hides tags, symptoms, and optional extras (O-25). */
  export let openMode: EntryOpenMode = 'full';
  /** When true, show onboarding tag suggestions and finalize onboarding on first save. */
  export let onboardingTagsEnabled = false;
  /** ISO date `YYYY-MM-DD` for the entry being edited. */
  export let initialDate: string;
  export let workContextTypical: WorkContextTypical | null = null;
  /** Cycle-day tracking opt-out (ADR-0034). When false, hide the cycle field. */
  export let cycleTrackingEnabled = true;

  const dispatch = createEventDispatcher<{ close: void; saved: void }>();

  const today = new Date();
  const sevenDaysAgo = new Date(today.getTime() - 7 * 24 * 60 * 60 * 1000);

  let entryDate: string = initialDate;
  let selectedSlot: EntrySlot = 'day';
  let moodScore = NEUTRAL_SCALE_DEFAULT;
  let energy = NEUTRAL_SCALE_DEFAULT;
  let stress = NEUTRAL_SCALE_DEFAULT;
  let cycleDay: number | null = null;
  let cycleBleedingLevel: BleedingLevel | null = null;
  const bleedingLevelOptions: BleedingLevel[] = ['none', 'spotting', 'light', 'medium', 'heavy'];
  // M8 Sprint 1 (#172): optional manual sleep. sleepMinutes 0..1440, sleepQuality 1..5.
  let sleepMinutes: number | null = null;
  let sleepQuality: number | null = null;
  let sleepMinutesInvalid = false;
  let workContext: WorkContext = defaultWorkContextForDate(
    new Date(initialDate + 'T00:00:00'),
    workContextTypical
  );
  let note = '';
  let noteVisibility: NoteVisibility = 'full';
  let noteMarkers: EntryNoteMarkerResponse[] = [];
  let markerSuggestions: string[] = [];
  let selectedTagIds: string[] = [];
  let selectedSymptoms: SymptomEntry[] = [];
  // When the per-entry tag/symptom fetch fails during load, the on-screen
  // selection is cleared to avoid showing another entry's rows (R-05). These
  // flags mark that the cleared set is *unknown*, not empty — persisting it
  // as-is would delete the entry's real relations under the sync replace-set
  // semantics (P1a). While set, the save path must re-resolve the affected
  // relation before it may be written.
  let tagsUnresolved = false;
  let symptomsUnresolved = false;
  let errorKey: string | null = null;
  let cycleDayInvalid = false;
  let offline = typeof navigator !== 'undefined' ? !navigator.onLine : false;

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
  let dateChangeToken = 0;
  let handledEntryDate: string | null = null;
  // The date whose fields are currently hydrated in the form. While the
  // date input is moving to a new value, pending autosaves must still
  // persist against this previous date.
  let loadedEntryDate: string = initialDate;
  let slotChangeToken = 0;
  // While `true`, reactive watchers on form fields skip `markDirty()`
  // — needed during hydration so loading an existing entry doesn't
  // immediately schedule a save back to the server.
  let hydrating = false;
  let createSaveInFlight = false;
  let applyingSmartDefaults = false;
  // Guards the reactive markDirty watcher while the save path writes the
  // re-resolved relations back into the bound fields (P1a) so that internal
  // sync does not schedule a redundant autosave.
  let applyingResolvedRelations = false;
  let dayDelta: EntryDeltaResponse | null = null;
  let dayDeltaLoading = false;
  let dayDeltaToken = 0;
  let offlineSyncConflictKey: string | null = null;
  let suggestionGroups: TagSuggestionGroup[] = [];
  let selectedSuggestions = new Map<string, TagSuggestion>();
  let suggestionsLoading = false;
  let onboardingMarkedComplete = false;
  // Set when persist deferred finalize (unreachable API or failed call).
  // Reachability/`online` retries must key off this — otherwise a false→true
  // transition (offline boot then API returns, sync blip) markDirty()'s an
  // untouched form, autosaves a default first entry, and completeOnboarding([])
  // locks out later suggestion picks.
  let onboardingFinalizeDeferred = false;
  // Set when a remount restores a deferred stash while loadForDate is still
  // hydrating — markDirty is a no-op during hydrate, so retry after it ends.
  let pendingDeferredOnboardingRetry = false;
  // P1: retry a deferred onboarding finalize when API reachability recovers.
  // `window.online` only covers navigator transitions; the stale-reachable
  // case (navigator stayed online while the API blipped) never fires it, so
  // without this the deferred finalize would only retry on a manual edit.
  let lastServerReachable: boolean | null = null;
  let unsubscribeConnectivity: (() => void) | null = null;

  $: offlineSyncBadge = $syncOrchestrator.badge;
  $: offlineSyncConflictKey = $syncOrchestrator.conflictNote;
  $: selectedSuggestionSlugs = new Set(selectedSuggestions.keys());

  // Keep the work-context default in sync with the hydrated form date,
  // but only until the user manually changes it themselves.
  let workContextTouched = false;
  $: if (!workContextTouched && loadedEntryDate && !existingEntryId) {
    const d = new Date(loadedEntryDate + 'T00:00:00');
    if (!Number.isNaN(d.getTime())) {
      workContext = defaultWorkContextForDate(d, workContextTypical);
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
    cycleBleedingLevel = null;
    cycleDayInvalid = false;
    sleepMinutes = null;
    sleepQuality = null;
    sleepMinutesInvalid = false;
    note = '';
    noteVisibility = 'full';
    noteMarkers = [];
    selectedTagIds = [];
    selectedSymptoms = [];
    tagsUnresolved = false;
    symptomsUnresolved = false;
    workContextTouched = false;
    const d = new Date(forDate + 'T00:00:00');
    if (!Number.isNaN(d.getTime())) {
      workContext = defaultWorkContextForDate(d, workContextTypical);
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
    // Assume relations resolve; the fetch branches flip these on rejection.
    tagsUnresolved = false;
    symptomsUnresolved = false;
    errorKey = null;
    selectedSlot = slot;
    // Cancel any in-flight auto-save scheduling — switching dates is a
    // hard form-reset, not an edit (ADR-0013 explicitly excludes date
    // changes from auto-save triggers).
    autoSave.reset();
    try {
      if (canUseOfflineSync()) {
        const [local, matches] = await Promise.all([
          findLocalEntryByDateSlot(date, slot),
          typeof navigator !== 'undefined' && navigator.onLine
            ? listEntries({ start_date: date, end_date: date, limit: 5 }).catch(
                () => [] as EntryResponse[]
              )
            : Promise.resolve([] as EntryResponse[]),
        ]);
        if (myToken !== loadToken) return;

        const matchingEntry = matches.find(
          (entry) => entry.entry_date === date && entry.slot === slot
        );
        if (matchingEntry && shouldPreferLocalEntry(local, matchingEntry.updated_at)) {
          existingEntryId = local!.id;
          const fields = localEntryToFormFields(local!);
          selectedSlot = fields.selectedSlot;
          moodScore = fields.moodScore;
          energy = fields.energy;
          stress = fields.stress;
          cycleDay = fields.cycleDay;
          cycleBleedingLevel = fields.cycleBleedingLevel;
          cycleDayInvalid = false;
          sleepMinutes = fields.sleepMinutes;
          sleepQuality = fields.sleepQuality;
          sleepMinutesInvalid = false;
          workContext = fields.workContext;
          workContextTouched = true;
          note = fields.note;
          selectedTagIds = fields.selectedTagIds;
          selectedSymptoms = fields.selectedSymptoms;
          if (typeof navigator !== 'undefined' && navigator.onLine) {
            void refreshDayDelta(date, selectedSlot);
          }
          loadedEntryDate = date;
          return;
        }
        if (matchingEntry) {
          existingEntryId = matchingEntry.id;
          selectedSlot = matchingEntry.slot;
          moodScore = matchingEntry.mood_score;
          energy = matchingEntry.energy;
          stress = matchingEntry.stress;
          cycleDay = matchingEntry.cycle_day;
          cycleBleedingLevel = matchingEntry.cycle_bleeding_level ?? null;
          cycleDayInvalid = false;
          sleepMinutes = matchingEntry.sleep_minutes ?? null;
          sleepQuality = matchingEntry.sleep_quality ?? null;
          sleepMinutesInvalid = false;
          workContext = matchingEntry.work_context;
          workContextTouched = true;
          note = matchingEntry.note ?? '';
          noteVisibility = matchingEntry.note_visibility ?? 'full';
          noteMarkers = matchingEntry.note_markers ?? [];
          const [tagsRes, symRes] = await Promise.allSettled([
            listTagsForEntry(matchingEntry.id),
            listSymptomsForEntry(matchingEntry.id),
          ]);
          if (myToken !== loadToken) return;
          // Clear on rejection so a failed tags/symptoms fetch cannot leave
          // the previous entry's selections in the form — and never hydrate
          // IndexedDB with those stale arrays (R-05 / GUI consistency P3-S2).
          let hydratedTagIds: string[] = [];
          let hydratedSymptoms: { symptom_id: string; intensity: number }[] = [];
          if (tagsRes.status === 'fulfilled') {
            hydratedTagIds = tagsRes.value.map((t) => t.id);
            selectedTagIds = hydratedTagIds;
          } else {
            selectedTagIds = [];
            tagsUnresolved = true;
          }
          if (symRes.status === 'fulfilled') {
            hydratedSymptoms = symRes.value.map((s) => ({
              symptom_id: s.symptom_id,
              intensity: s.intensity,
            }));
            selectedSymptoms = hydratedSymptoms;
          } else {
            selectedSymptoms = [];
            symptomsUnresolved = true;
          }
          if (tagsRes.status === 'fulfilled' && symRes.status === 'fulfilled') {
            await hydrateServerEntryFromApi(matchingEntry, hydratedTagIds, hydratedSymptoms);
          }
          loadedEntryDate = date;
          void refreshDayDelta(date, selectedSlot);
          return;
        }

        if (local) {
          existingEntryId = local.id;
          const fields = localEntryToFormFields(local);
          selectedSlot = fields.selectedSlot;
          moodScore = fields.moodScore;
          energy = fields.energy;
          stress = fields.stress;
          cycleDay = fields.cycleDay;
          cycleBleedingLevel = fields.cycleBleedingLevel;
          cycleDayInvalid = false;
          sleepMinutes = fields.sleepMinutes;
          sleepQuality = fields.sleepQuality;
          sleepMinutesInvalid = false;
          workContext = fields.workContext;
          workContextTouched = true;
          note = fields.note;
          selectedTagIds = fields.selectedTagIds;
          selectedSymptoms = fields.selectedSymptoms;
          if (typeof navigator !== 'undefined' && navigator.onLine) {
            void refreshDayDelta(date, selectedSlot);
          }
          loadedEntryDate = date;
          return;
        }

        resetForm(date, slot);
        loadedEntryDate = date;
        void applySmartDefaults(date, slot, myToken);
        return;
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
        loadedEntryDate = date;
        void applySmartDefaults(date, slot, myToken);
        return;
      }
      existingEntryId = matchingEntry.id;
      selectedSlot = matchingEntry.slot;
      moodScore = matchingEntry.mood_score;
      energy = matchingEntry.energy;
      stress = matchingEntry.stress;
      cycleDay = matchingEntry.cycle_day;
      cycleBleedingLevel = matchingEntry.cycle_bleeding_level ?? null;
      cycleDayInvalid = false;
      workContext = matchingEntry.work_context;
      // Mark touched so the date-change reactive block doesn't reset it
      // back to the weekday default.
      workContextTouched = true;
      note = matchingEntry.note ?? '';
      noteVisibility = matchingEntry.note_visibility ?? 'full';
      noteMarkers = matchingEntry.note_markers ?? [];

      // Tags + symptoms load in parallel; both wrapped so one slow
      // network blip doesn't keep the other from rendering.
      const [tagsRes, symRes] = await Promise.allSettled([
        listTagsForEntry(matchingEntry.id),
        listSymptomsForEntry(matchingEntry.id),
      ]);
      if (myToken !== loadToken) return;
      let hydratedTagIds = [...selectedTagIds];
      let hydratedSymptoms = [...selectedSymptoms];
      if (tagsRes.status === 'fulfilled') {
        hydratedTagIds = tagsRes.value.map((t) => t.id);
        selectedTagIds = hydratedTagIds;
      } else {
        selectedTagIds = [];
        hydratedTagIds = [];
        tagsUnresolved = true;
      }
      if (symRes.status === 'fulfilled') {
        hydratedSymptoms = symRes.value.map((s) => ({
          symptom_id: s.symptom_id,
          intensity: s.intensity,
        }));
        selectedSymptoms = hydratedSymptoms;
      } else {
        selectedSymptoms = [];
        hydratedSymptoms = [];
        symptomsUnresolved = true;
      }
      if (canUseOfflineSync() && tagsRes.status === 'fulfilled' && symRes.status === 'fulfilled') {
        await hydrateServerEntryFromApi(matchingEntry, hydratedTagIds, hydratedSymptoms);
      }
      loadedEntryDate = date;
      void refreshDayDelta(date, selectedSlot);
    } catch (err) {
      if (myToken !== loadToken) return;
      if (canUseOfflineSync()) {
        const local = await findLocalEntryByDateSlot(date, slot);
        if (myToken !== loadToken) return;
        if (local) {
          existingEntryId = local.id;
          const fields = localEntryToFormFields(local);
          selectedSlot = fields.selectedSlot;
          moodScore = fields.moodScore;
          energy = fields.energy;
          stress = fields.stress;
          cycleDay = fields.cycleDay;
          cycleBleedingLevel = fields.cycleBleedingLevel;
          cycleDayInvalid = false;
          sleepMinutes = fields.sleepMinutes;
          sleepQuality = fields.sleepQuality;
          sleepMinutesInvalid = false;
          workContext = fields.workContext;
          workContextTouched = true;
          note = fields.note;
          selectedTagIds = fields.selectedTagIds;
          selectedSymptoms = fields.selectedSymptoms;
          loadedEntryDate = date;
          return;
        }
      }
      errorKey = mapApiError(err, ERROR_MAP) ?? 'entry.error_load';
      resetForm(date, slot);
      loadedEntryDate = date;
    } finally {
      if (myToken === loadToken) {
        loading = false;
        // Defer turning hydration off to the next microtask: Svelte
        // reactivity flushes any pending field-change reactions
        // synchronously after this assignment, and we don't want those
        // to count as user edits.
        await Promise.resolve();
        hydrating = false;
        if (pendingDeferredOnboardingRetry) {
          pendingDeferredOnboardingRetry = false;
          scheduleDeferredOnboardingRetry();
        }
      }
    }
  }

  async function handleEntryDateChange(date: string): Promise<void> {
    const myToken = ++dateChangeToken;
    if (date !== loadedEntryDate) {
      const settled = await settleAutosaveBeforeHydration();
      if (myToken !== dateChangeToken) return;
      if (!settled) {
        handledEntryDate = loadedEntryDate;
        entryDate = loadedEntryDate;
        return;
      }
    }
    await loadForDate(date);
  }

  // Reactively reload whenever the user picks a different date. The
  // initial call is also covered: once ``entryDate`` is initialised
  // above, this reactive block fires on mount.
  $: if (entryDate) {
    if (entryDate !== handledEntryDate) {
      handledEntryDate = entryDate;
      void handleEntryDateChange(entryDate);
    }
  }

  function onWorkContextChange(e: Event) {
    workContextTouched = true;
    workContext = (e.target as HTMLSelectElement).value as WorkContext;
  }

  function onCycleBleedingChange(e: Event) {
    const value = (e.currentTarget as HTMLSelectElement).value;
    cycleBleedingLevel = value === '' ? null : (value as BleedingLevel);
  }

  function onCycleDayInput(e: Event) {
    const value = (e.currentTarget as HTMLInputElement).value;
    const parsed = Number(value);
    cycleDay = value === '' || !Number.isFinite(parsed) ? null : parsed;
    cycleDayInvalid = cycleDay !== null && (cycleDay < 1 || cycleDay > 35);
  }

  function onSleepMinutesInput(e: Event) {
    const value = (e.currentTarget as HTMLInputElement).value;
    const parsed = Number(value);
    sleepMinutes = value === '' || !Number.isFinite(parsed) ? null : Math.round(parsed);
    sleepMinutesInvalid = sleepMinutes !== null && (sleepMinutes < 0 || sleepMinutes > 1440);
  }

  function onSleepQualityChange(e: Event) {
    const value = (e.currentTarget as HTMLSelectElement).value;
    sleepQuality = value === '' ? null : Number(value);
  }

  function handleOnline() {
    offline = false;
    if (canUseOfflineSync()) {
      scheduleSync();
    }
    if (onboardingFinalizeDeferred && onboardingTagsEnabled && !onboardingMarkedComplete) {
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

  function waitForAutoSaveNotSaving(): Promise<void> {
    if (autoSave.peek().status !== 'saving') return Promise.resolve();

    return new Promise((resolve) => {
      let unsubscribe = () => {};
      unsubscribe = autoSaveState.subscribe((state) => {
        if (state.status !== 'saving') {
          unsubscribe();
          resolve();
        }
      });
    });
  }

  async function settleAutosaveBeforeHydration(): Promise<boolean> {
    let flushed = false;

    while (true) {
      const status = autoSave.peek().status;
      if (status === 'dirty' || status === 'error') {
        if (flushed) return false;
        flushed = true;
        await autoSave.flushNow();
        continue;
      }
      if (status === 'saving') {
        await waitForAutoSaveNotSaving();
        continue;
      }
      return true;
    }
  }

  async function flushSlotAfterInFlightSave(): Promise<void> {
    await waitForAutoSaveNotSaving();
    const status = autoSave.peek().status;
    if (status === 'saved' || status === 'idle') {
      markDirty();
    }
    await autoSave.flushNow();
  }

  async function entryExistsForSlot(date: string, slot: EntrySlot): Promise<boolean> {
    if (canUseOfflineSync()) {
      if (typeof navigator !== 'undefined' && navigator.onLine) {
        try {
          const matches = await listEntries({
            start_date: date,
            end_date: date,
            limit: 5,
          });
          if (matches.some((entry) => entry.entry_date === date && entry.slot === slot)) {
            return true;
          }
        } catch {
          // Fall back to Dexie when the API is temporarily unavailable.
        }
      }
      const local = await findLocalEntryByDateSlot(date, slot);
      if (local) return true;
      return false;
    }
    const matches = await listEntries({
      start_date: date,
      end_date: date,
      limit: 5,
    });
    return matches.some((entry) => entry.entry_date === date && entry.slot === slot);
  }

  async function setSlot(slot: EntrySlot) {
    if (loading || entryDate !== loadedEntryDate) return;

    const myToken = ++slotChangeToken;
    const nextSlot = selectedSlot === slot ? 'day' : slot;

    async function hydrateSelectedSlot(): Promise<void> {
      if (!(await settleAutosaveBeforeHydration())) return;
      if (myToken !== slotChangeToken) return;
      await loadForDate(entryDate, nextSlot);
    }

    const occupied = await entryExistsForSlot(entryDate, nextSlot);
    if (occupied) {
      await hydrateSelectedSlot();
      return;
    }

    const status = autoSave.peek().status;
    const saving = status === 'saving';
    const dirtyOrError = status === 'dirty' || status === 'error';
    const draftCreatePath = !existingEntryId && (dirtyOrError || saving);
    const finishingCreatePipeline = Boolean(existingEntryId) && saving && createSaveInFlight;

    if (draftCreatePath || finishingCreatePipeline) {
      selectedSlot = nextSlot;
      markDirty();
      if (saving) {
        void flushSlotAfterInFlightSave();
      }
      if (draftCreatePath) {
        void refreshDayDelta(entryDate, nextSlot);
      }
      return;
    }

    await hydrateSelectedSlot();
  }

  // ---------------------------------------------------------------------
  // Auto-save controller (ADR-0013)
  // ---------------------------------------------------------------------

  interface FormSnapshot extends EntryFormSnapshot {}

  function snapshot(): FormSnapshot {
    return {
      entry_date: loadedEntryDate,
      mood_score: moodScore,
      energy,
      stress,
      slot: selectedSlot,
      cycle_day: cycleDay ?? null,
      cycle_bleeding_level: cycleBleedingLevel,
      sleep_minutes: sleepMinutes ?? null,
      sleep_quality: sleepQuality ?? null,
      work_context: workContext,
      note: note.trim(),
      selectedTagIds: [...selectedTagIds],
      selectedSymptoms: selectedSymptoms.map((s) => ({ ...s })),
    };
  }

  function applyLocalMarkerToggle(marker: string, selected: boolean): void {
    if (selected) {
      if (noteMarkers.some((item) => item.marker === marker)) return;
      noteMarkers = [
        ...noteMarkers,
        {
          id: `pending:${marker}`,
          entry_id: existingEntryId ?? '',
          marker,
          source: 'user',
          created_at: new Date().toISOString(),
        },
      ];
      return;
    }
    noteMarkers = noteMarkers.filter((item) => item.marker !== marker);
  }

  async function syncMarkerToggle(marker: string, selected: boolean): Promise<void> {
    // Keep optimistic local state even before first save / while offline sync owns persistence.
    const existingBefore = noteMarkers.find((item) => item.marker === marker);
    applyLocalMarkerToggle(marker, selected);
    markDirty();
    if (!existingEntryId || canUseOfflineSync()) return;
    if (selected) {
      const created = await addNoteMarker(existingEntryId, { marker, source: 'user' });
      noteMarkers = [...noteMarkers.filter((item) => item.marker !== created.marker), created];
      return;
    }
    if (!existingBefore || existingBefore.id.startsWith('pending:')) return;
    await deleteNoteMarker(existingEntryId, existingBefore.id);
  }

  async function flushPendingMarkers(entryId: string): Promise<void> {
    if (canUseOfflineSync()) return;
    const pending = noteMarkers.filter((item) => item.id.startsWith('pending:'));
    for (const item of pending) {
      const created = await addNoteMarker(entryId, { marker: item.marker, source: 'user' });
      noteMarkers = [...noteMarkers.filter((m) => m.marker !== created.marker), created];
    }
  }

  async function handleMarkerToggle(
    event: CustomEvent<{ marker: string; selected: boolean }>
  ): Promise<void> {
    const { marker, selected } = event.detail;
    try {
      await syncMarkerToggle(marker, selected);
    } catch (err) {
      errorKey = mapApiError(err, ERROR_MAP);
    }
  }

  async function handleCustomMarker(event: CustomEvent<{ marker: string }>): Promise<void> {
    await handleMarkerToggle(
      new CustomEvent('toggle', { detail: { marker: event.detail.marker, selected: true } })
    );
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
    if (
      snap.sleep_minutes !== null &&
      snap.sleep_minutes !== undefined &&
      (snap.sleep_minutes < 0 || snap.sleep_minutes > 1440)
    ) {
      throw new Error('invalid_sleep_minutes');
    }
    const startedAsCreate = !existingEntryId;
    if (startedAsCreate) createSaveInFlight = true;

    try {
      const resolvedSnap = await preserveUnresolvedRelations(await resolveOnboardingTags(snap));

      if (canUseOfflineSync()) {
        const result = await saveEntryOffline(existingEntryId, resolvedSnap);
        existingEntryId = result.entryId;
        onLocalEntrySaved();
        if (typeof navigator !== 'undefined' && navigator.onLine) {
          void refreshDayDelta(resolvedSnap.entry_date, resolvedSnap.slot);
        }
        clearOnboardingStashAfterSuccessfulPersist();
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
          cycle_bleeding_level: resolvedSnap.cycle_bleeding_level ?? null,
          sleep_minutes: resolvedSnap.sleep_minutes ?? null,
          sleep_quality: resolvedSnap.sleep_quality ?? null,
          work_context: resolvedSnap.work_context,
          note: resolvedSnap.note,
          note_summary_short: computeNoteSummaryShort(resolvedSnap.note) ?? undefined,
          note_visibility: noteVisibility,
        });
        entryId = updated.id;
        noteMarkers = updated.note_markers ?? noteMarkers;
      } else {
        const created = await submitEntry({
          entry_date: resolvedSnap.entry_date,
          slot: resolvedSnap.slot,
          mood_score: resolvedSnap.mood_score,
          energy: resolvedSnap.energy,
          stress: resolvedSnap.stress,
          cycle_day: resolvedSnap.cycle_day,
          cycle_bleeding_level: resolvedSnap.cycle_bleeding_level ?? null,
          sleep_minutes: resolvedSnap.sleep_minutes ?? null,
          sleep_quality: resolvedSnap.sleep_quality ?? null,
          work_context: resolvedSnap.work_context,
          note: resolvedSnap.note ? resolvedSnap.note : undefined,
          note_summary_short: computeNoteSummaryShort(resolvedSnap.note) ?? undefined,
          note_visibility: noteVisibility,
        });
        entryId = created.id;
        // POST → PATCH-Flip: store the id so subsequent saves go via
        // updateEntry. This is the same flow that defused the 409 race
        // we hit in PR #117.
        existingEntryId = entryId;
        await flushPendingMarkers(entryId);
      }

      await assignTagsToEntry(entryId, resolvedSnap.selectedTagIds);
      await assignSymptomsToEntry(entryId, resolvedSnap.selectedSymptoms);
      await refreshDayDelta(resolvedSnap.entry_date, resolvedSnap.slot);
      clearOnboardingStashAfterSuccessfulPersist();
    } finally {
      if (startedAsCreate) createSaveInFlight = false;
    }
  }

  /**
   * P1a — guard against silently deleting an entry's relations after a failed
   * relation fetch. When ``tagsUnresolved`` / ``symptomsUnresolved`` is set the
   * on-screen selection was cleared to an *unknown* (not empty) state, and the
   * sync payload / assign endpoints replace-set the whole relation. Re-resolve
   * the affected relation before saving; merge any rows the user added in the
   * meantime so nothing is lost. If the fetch still fails we rethrow — the
   * autosave stays in ``error`` (retryable) rather than persisting a
   * destructive empty replace-set.
   */
  async function preserveUnresolvedRelations(snap: FormSnapshot): Promise<FormSnapshot> {
    if (!existingEntryId || (!tagsUnresolved && !symptomsUnresolved)) return snap;

    // Capture before awaits — loadForDate can change the bound entry, and
    // TagPicker/SymptomChecker stay enabled during save so live selections
    // may advance past the dirty snapshot.
    const entryId = existingEntryId;
    const resolveTags = tagsUnresolved;
    const resolveSymptoms = symptomsUnresolved;

    let nextTagIds: string[] | null = null;
    let nextSymptoms: SymptomEntry[] | null = null;

    if (resolveTags) {
      const serverTags = await listTagsForEntry(entryId);
      // server ∪ dirty snap ∪ live picks (live wins membership for new chips).
      nextTagIds = mergeUnresolvedTagIds(
        serverTags.map((t) => t.id),
        snap.selectedTagIds,
        selectedTagIds
      );
    }
    if (resolveSymptoms) {
      const serverSymptoms = await listSymptomsForEntry(entryId);
      // Later groups win intensity; live edits after the dirty snap must stick.
      nextSymptoms = mergeUnresolvedSymptoms(
        serverSymptoms.map((s) => ({ symptom_id: s.symptom_id, intensity: s.intensity })),
        snap.selectedSymptoms,
        selectedSymptoms
      );
    }

    // If the user navigated to another entry while we re-fetched, abort —
    // returning the old entry's relations into persist() would write them
    // onto the newly bound existingEntryId.
    if (existingEntryId !== entryId) {
      throw new Error('entry_changed_during_relation_resolve');
    }

    // Reflect the resolved relations back into the bound fields so a later
    // edit keeps them instead of falling back to the cleared empty set, then
    // clear the flags. Suppress markDirty so this internal sync does not
    // schedule a redundant autosave.
    applyingResolvedRelations = true;
    try {
      if (nextTagIds) {
        selectedTagIds = nextTagIds;
        tagsUnresolved = false;
      }
      if (nextSymptoms) {
        selectedSymptoms = nextSymptoms;
        symptomsUnresolved = false;
      }
      await Promise.resolve();
    } finally {
      applyingResolvedRelations = false;
    }

    return {
      ...snap,
      selectedTagIds: nextTagIds ?? snap.selectedTagIds,
      selectedSymptoms: nextSymptoms ?? snap.selectedSymptoms,
    };
  }

  function currentUserId(): string | null {
    const state = get(auth);
    return state.status === 'authenticated' ? state.user.id : null;
  }

  function persistOnboardingSuggestionStash(finalizeDeferred: boolean) {
    const userId = currentUserId();
    if (!userId) return;
    // After finalize succeeds we keep the deferred stash until persist()
    // finishes so a failed tag/entry write can still remount-retry. Do not
    // overwrite that recovery marker with a toggle-only (non-deferred) stash.
    if (onboardingMarkedComplete && !finalizeDeferred) return;
    writeOnboardingSuggestionStash({
      userId,
      suggestions: [...selectedSuggestions.values()],
      finalizeDeferred,
    });
  }

  function clearOnboardingStashAfterSuccessfulPersist() {
    // Entry-only saves while finalize is still deferred must keep the stash
    // so a remount can retry completeOnboarding + tag writeback.
    if (!onboardingMarkedComplete) return;
    const userId = currentUserId();
    if (userId) clearOnboardingSuggestionStash(userId);
  }

  function scheduleDeferredOnboardingRetry() {
    if (hydrating || loading) {
      pendingDeferredOnboardingRetry = true;
      return;
    }
    void Promise.resolve().then(() => {
      if (onboardingFinalizeDeferred && onboardingTagsEnabled && !onboardingMarkedComplete) {
        markDirty();
      }
    });
  }

  function restoreOnboardingSuggestionStash() {
    const userId = currentUserId();
    if (!userId) return;
    const stash = readOnboardingSuggestionStash(userId);
    if (!stash) return;
    selectedSuggestions = new Map(stash.suggestions.map((tag) => [tag.slug, tag]));
    if (stash.finalizeDeferred) {
      onboardingFinalizeDeferred = true;
      scheduleDeferredOnboardingRetry();
    }
  }

  async function resolveOnboardingTags(snap: FormSnapshot): Promise<FormSnapshot> {
    if (!onboardingTagsEnabled || onboardingMarkedComplete) return snap;
    // Offline sync enabled must not skip onboarding while the API is
    // reachable — otherwise suggestion chips never become entry tags (R-04).
    // Only defer when we truly cannot reach the API. `navigator.onLine`
    // alone misses the "browser online but API unreachable" case: without
    // deferring there, `completeOnboarding` throws and aborts the save
    // before `saveEntryOffline` runs, losing the first onboarding entry
    // (P1b). Treat `serverReachable === false` as offline too.
    const cannotReachApi =
      (typeof navigator !== 'undefined' && !navigator.onLine) ||
      get(connectivity).serverReachable === false;
    if (canUseOfflineSync() && cannotReachApi) {
      onboardingFinalizeDeferred = true;
      // Survive BottomSheet unmount: picks are only in selectedSuggestions.
      persistOnboardingSuggestionStash(true);
      return snap;
    }
    const tags = [...selectedSuggestions.values()].map((tag) => ({
      slug: tag.slug,
      name: tag.name,
      category: tag.category,
      icon: tag.icon,
      color: tag.color,
    }));
    // P1b residual: `serverReachable` can be stale `true`/`null` while the
    // finalize call still fails (blip, 5xx). Swallow and defer so the Dexie
    // write still runs; the connectivity-recovery watcher (or the next dirty
    // pass) retries the finalize (P1).
    let result: Awaited<ReturnType<typeof completeOnboarding>>;
    try {
      result = await completeOnboarding(tags);
    } catch (err) {
      if (canUseOfflineSync()) {
        onboardingFinalizeDeferred = true;
        persistOnboardingSuggestionStash(true);
        return snap;
      }
      throw err;
    }
    onboardingMarkedComplete = true;
    onboardingFinalizeDeferred = false;
    // Keep a deferred stash until persist() succeeds — completeOnboarding has
    // already flipped onboarding_retro_completed server-side; clearing here
    // made a post-finalize save failure + remount permanently drop tag
    // associations (gate hid chips because prefs looked finished).
    persistOnboardingSuggestionStash(true);
    const createdIds = result.created_tags.map((tag) => tag.id);
    // Merge the live `selectedTagIds` as well, not just the snapshot: a tag the
    // user picks while completeOnboarding() is still awaiting lives only in the
    // live set, so writing back the snapshot alone would clobber that pick (P2).
    const nextTagIds = [...new Set([...selectedTagIds, ...snap.selectedTagIds, ...createdIds])];
    // Write created IDs into the live form — resolve only mutates the save
    // snapshot otherwise, so the next autosave (replace-set) would persist
    // empty selectedTagIds and wipe the onboarding associations just applied.
    // Mirror preserveUnresolvedRelations: suppress markDirty for this sync.
    applyingResolvedRelations = true;
    try {
      selectedTagIds = nextTagIds;
      await Promise.resolve();
    } finally {
      applyingResolvedRelations = false;
    }
    // The catalogue refresh is best-effort: a failure here must NOT discard
    // the just-created onboarding tag associations (P2). The finalize already
    // succeeded, so apply its result regardless of the refresh outcome.
    try {
      await refreshTags();
    } catch {
      /* non-fatal — the tags exist server-side; the catalogue re-syncs later */
    }
    return {
      ...snap,
      selectedTagIds: nextTagIds,
    };
  }

  function toggleOnboardingSuggestion(tag: TagSuggestion) {
    selectedSuggestions = new Map(selectedSuggestions);
    if (selectedSuggestions.has(tag.slug)) selectedSuggestions.delete(tag.slug);
    else selectedSuggestions.set(tag.slug, tag);
    // Persist on toggle too — close-before-autosave must not drop picks.
    persistOnboardingSuggestionStash(onboardingFinalizeDeferred);
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
    restoreOnboardingSuggestionStash();
  }

  const autoSave = createAutoSave<FormSnapshot>({
    getSnapshot: snapshot,
    save: persist,
  });
  const autoSaveState = autoSave.state;

  let autoSaveSnap: AutoSaveState = { status: 'idle', lastSavedAt: null, lastError: null };
  $: autoSaveSnap = $autoSaveState;

  function markDirty() {
    if (hydrating || loading || applyingSmartDefaults || applyingResolvedRelations) return;
    // Per-route guard: don't try to auto-save when the user has dialed
    // into a load-error — they need to retry the load first.
    autoSave.markDirty();
  }

  // Reactive watchers: any edit to a tracked field marks the form
  // dirty (includes cycleBleedingLevel). We deliberately keep `entryDate`
  // out of this list — date changes trigger a full hydration via `loadForDate` instead.
  $: {
    moodScore;
    energy;
    stress;
    selectedSlot;
    cycleDay;
    cycleBleedingLevel;
    sleepMinutes;
    sleepQuality;
    workContext;
    note;
    noteVisibility;
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
    void listNoteMarkerSuggestions()
      .then((items) => {
        markerSuggestions = items;
      })
      .catch(() => {
        markerSuggestions = [];
      });
    window.addEventListener('online', handleOnline);
    window.addEventListener('offline', handleOffline);
    window.addEventListener('beforeunload', onBeforeUnload);
    // P1: when the API becomes reachable again, retry a still-pending
    // onboarding finalize (schedule an autosave) instead of waiting for a
    // manual edit. Mirrors handleOnline but keyed on effective reachability,
    // which the `window.online` event does not cover in the stale-reachable case.
    // Only retry after an actual deferral — a bare false→true must not
    // autosave/finalize an untouched onboarding form.
    lastServerReachable = get(connectivity).serverReachable;
    unsubscribeConnectivity = connectivity.subscribe(($c) => {
      const recovered = $c.serverReachable === true && lastServerReachable !== true;
      lastServerReachable = $c.serverReachable;
      if (
        recovered &&
        onboardingFinalizeDeferred &&
        onboardingTagsEnabled &&
        !onboardingMarkedComplete
      ) {
        markDirty();
      }
    });
  });

  onDestroy(() => {
    if (typeof window !== 'undefined') {
      window.removeEventListener('beforeunload', onBeforeUnload);
      window.removeEventListener('online', handleOnline);
      window.removeEventListener('offline', handleOffline);
    }
    unsubscribeConnectivity?.();
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
            if (autoSaveSnap.status === 'error') {
              void autoSave.retry();
            } else {
              scheduleSync();
            }
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
            disabled={loading || entryDate !== loadedEntryDate}
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

    <section class="entry-section" aria-labelledby="entry-section-note">
      <h2 id="entry-section-note" class="entry-section__title">{$_('entry.section.note')}</h2>
      <label class="entry-field">
        <span class="sr-only">{$_('entry.note_placeholder')}</span>
        <textarea
          class="input"
          rows="4"
          maxlength="4000"
          bind:value={note}
          placeholder={$_('entry.note_placeholder')}></textarea>
      </label>
      <NoteMarkerChips
        markers={noteMarkers}
        suggestions={markerSuggestions}
        on:toggle={handleMarkerToggle}
        on:addCustom={handleCustomMarker}
      />
      <label class="entry-field entry-field--inline">
        <span class="entry-label">{$_('entry.note_visibility.label')}</span>
        <select bind:value={noteVisibility} data-testid="entry-note-visibility">
          <option value="full">{$_('entry.note_visibility.full')}</option>
          <option value="analysis_only">{$_('entry.note_visibility.analysis_only')}</option>
          <option value="hidden">{$_('entry.note_visibility.hidden')}</option>
        </select>
      </label>
    </section>

    {#if cycleTrackingEnabled}
      <section class="entry-section" aria-labelledby="entry-section-cycle">
        <h2 id="entry-section-cycle" class="entry-section__title">
          {$_('entry.section.cycle')}
        </h2>
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
        <label class="entry-field">
          <span class="entry-label">{$_('entry.cycle_bleeding.label')}</span>
          <select
            class="input"
            value={cycleBleedingLevel ?? ''}
            on:change={onCycleBleedingChange}
            data-testid="entry-cycle-bleeding"
          >
            <option value="">{$_('entry.cycle_bleeding.unset')}</option>
            {#each bleedingLevelOptions as level}
              <option value={level}>{$_(`entry.cycle_bleeding.${level}`)}</option>
            {/each}
          </select>
        </label>
        <p class="entry-hint">{$_('entry.cycle_bleeding.hint')}</p>
      </section>
    {/if}

    <section class="entry-section" aria-labelledby="entry-section-sleep">
      <h2 id="entry-section-sleep" class="entry-section__title">
        {$_('entry.section.sleep')}
      </h2>
      <label class="entry-field">
        <span class="entry-label">{$_('entry.sleep_minutes.label')}</span>
        <input
          type="number"
          class="input"
          min="0"
          max="1440"
          step="15"
          inputmode="numeric"
          value={sleepMinutes ?? ''}
          on:input={onSleepMinutesInput}
          aria-invalid={sleepMinutesInvalid}
          aria-describedby={sleepMinutesInvalid ? 'entry-sleep-error' : 'entry-sleep-hint'}
          placeholder={$_('entry.sleep_minutes.placeholder')}
          data-testid="entry-sleep-minutes"
        />
      </label>
      <p id="entry-sleep-hint" class="entry-hint">{$_('entry.sleep_minutes.hint')}</p>
      {#if sleepMinutesInvalid}
        <p id="entry-sleep-error" class="entry-error" role="alert">
          {$_('entry.sleep_minutes.error_range')}
        </p>
      {/if}
      <label class="entry-field">
        <span class="entry-label">{$_('entry.sleep_quality.label')}</span>
        <select
          class="input"
          value={sleepQuality ?? ''}
          on:change={onSleepQualityChange}
          data-testid="entry-sleep-quality"
        >
          <option value="">{$_('entry.sleep_quality.unset')}</option>
          {#each [1, 2, 3, 4, 5] as level}
            <option value={level}>{$_(`entry.sleep_quality.level_${level}`)}</option>
          {/each}
        </select>
      </label>
      <p class="entry-hint">{$_('entry.sleep_quality.hint')}</p>
    </section>

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

  .entry-chip-row button:disabled {
    cursor: not-allowed;
    opacity: 0.55;
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
    border-radius: var(--radius-md);
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

    .entry-form {
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
