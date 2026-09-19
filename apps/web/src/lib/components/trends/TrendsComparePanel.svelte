<script lang="ts">
  import { browser } from '$app/environment';
  import { createEventDispatcher, onDestroy, onMount } from 'svelte';
  import { tick } from 'svelte';
  import { get } from 'svelte/store';
  import { _ } from 'svelte-i18n';
  import { fetchTagClusters, type TagClustersResponse } from '$lib/api/insights';
  import { getDevPhaseFixture } from '$lib/dev/phaseFixtures';
  import { devForceVisualizations, devPhase } from '$lib/stores/devMode';
  import { auth } from '$lib/stores/auth';
  import type {
    SymptomHeatmapResponse,
    TagHeatmapResponse,
    TimeseriesPoint,
    TimeseriesRange,
  } from '$lib/api/stats';
  import { buildIsoDateRange, compareDailyAxisLayout, type MetricKey } from '$lib/utils/charts';
  import {
    buildAxisBuckets,
    clampZoomStageForWindow,
    findBucketForDate,
    formatBucketRangeLabel,
    maxZoomStageForWindow,
    stageDays,
    type AxisBucket,
    type CompareZoomStageIndex,
  } from '$lib/utils/compareAxisZoom';
  import { TREND_WINDOW_DAYS_DEFAULT, type TrendWindowDays } from '$lib/utils/trendWindowDays';
  import { clampAxisRangeToData, compareDailyAxisLayoutFromRoot } from '$lib/utils/trendsDateAxis';
  import type { WorkContextHeatmapResponse } from '$lib/utils/workContextHeatmap';
  import {
    readCompareMode,
    readCompareSortMode,
    readCompareZoomStage,
    readCompareCoincidenceHighlight,
    readCompareLag1Highlight,
    readCompareOverlayHintDismissed,
    writeCompareMode,
    writeCompareSortMode,
    writeCompareZoomStage,
    writeCompareCoincidenceHighlight,
    writeCompareLag1Highlight,
    writeCompareOverlayHintDismissed,
    type CompareMode,
    type CompareSortMode,
  } from '$lib/utils/comparePanelSettings';
  import {
    MAX_COMPARE_PINS,
    canPinMore,
    clampPinnedIds,
    coincidenceDaysToMarkers,
    deriveCoincidence,
    isRowActiveOnDay,
    summarizeCoincidence,
    type CoincidenceRow,
  } from '$lib/utils/coincidenceMarkers';
  import { datesToEventWindows } from '$lib/utils/exploreEventWindows';
  import type { EventWindow } from './EventAlignedSmallMultiplesSheet.svelte';
  import Button from '$lib/components/common/Button.svelte';
  import {
    deriveLag1,
    hasReportableLag1,
    lag1DaysToMarkers,
    summarizeLag1,
  } from '$lib/utils/lag1Markers';
  import { timelineCursor, timelineCursorDate } from '$lib/stores/timelineCursor';
  import { buildTagClusterMeta } from '$lib/utils/tagCooccurrenceMatrix';
  import MetricTimeseries from './MetricTimeseries.svelte';
  import ComparisonHeatmap from './ComparisonHeatmap.svelte';
  import UnifiedStripChart from './UnifiedStripChart.svelte';
  import CompareOverlayControls from './CompareOverlayControls.svelte';
  import type { CompareOverlayAvailability } from '$lib/utils/compareOverlayAvailability';
  import { dedupeEventMarkers, type EventMarker } from './EventMarkerLayer.svelte';

  export let points: TimeseriesPoint[] = [];
  export let range: TimeseriesRange = 'week';
  /** Analysis window in days — clamps zoom so a cell never exceeds the window (#928 O5). */
  export let windowDays: TrendWindowDays = TREND_WINDOW_DAYS_DEFAULT;
  export let enabled: Record<MetricKey, boolean>;
  export let tagHeatmap: TagHeatmapResponse | null = null;
  export let symptomHeatmap: SymptomHeatmapResponse | null = null;
  export let workContextHeatmap: WorkContextHeatmapResponse | null = null;
  export let showTags = true;
  export let showSymptoms = false;
  export let showWorkContexts = true;
  export let loading = false;
  export let pruneSparseAxes = true;
  export let compactChrome = false;
  /** Increment to reload tag clusters after a parent data refresh (#597 P2). */
  export let clusterRefreshToken = 0;
  /** Bound by parent for compact settings sheet cluster-sort availability (#597). */
  export let clustersAvailableBinding = false;
  /** Bound by parent so the mobile settings sheet can drive focus chips (#928 O7). */
  export let focusedClusterId: number | null = null;
  /** Bound by parent so zoom is shared with the mobile settings sheet (#928 O7). */
  export let zoomStage: CompareZoomStageIndex = readCompareZoomStage();
  /** Tag group labels for the mobile settings sheet focus chips. */
  export let tagClusterLabelsBinding: { cluster_id: number; label: string }[] = [];
  /** When true, show the compare → ESM affordance (#928 Phase 2). */
  export let esmUnlocked = false;
  export let mode: CompareMode = readCompareMode();
  export let sortMode: CompareSortMode = readCompareSortMode();
  /** #919: bindable so the mobile settings sheet can drive the same overlays. */
  export let coincidenceHighlight = readCompareCoincidenceHighlight();
  export let lag1Highlight = readCompareLag1Highlight();
  export let overlayHintDismissed = readCompareOverlayHintDismissed();
  /** Gate state published for surfaces that cannot derive it (settings sheet). */
  export let overlayAvailabilityBinding: CompareOverlayAvailability = {
    pinnedCount: 0,
    coincidence: false,
    lag1: false,
  };
  /**
   * Sprint 1 (ADR-0035): event markers shared across metric chart and
   * heatmap rows. Computed by the parent page from insight maturity,
   * symptom onsets, and habit goal changes; passed unfiltered.
   */
  export let markers: readonly EventMarker[] = [];
  export let noteDates: readonly string[] = [];
  /**
   * Sprint 2 (ADR-0035): optional correlation map handed down to the
   * heatmap when sortMode === 'correlation'. Values are |r| in [0, 1].
   */
  export let correlationScores: Record<string, number> = {};

  const dispatch = createEventDispatcher<{
    selectDate: { date: string };
    layerChange: { showTags: boolean; showSymptoms: boolean; showWorkContexts: boolean };
    modeChange: { value: CompareMode };
    sortChange: { value: CompareSortMode };
    coincidenceChange: { value: boolean };
    lag1Change: { value: boolean };
    overlayHintDismiss: void;
    checkQuestion: { windows: EventWindow[]; label: string };
  }>();

  // Sprint 1 (ADR-0035): the Compare panel owns the cursor lifecycle.
  // #214 finding 4: scale day columns from root rem for accessible touch targets.
  let axisLayout = compareDailyAxisLayout;

  onMount(() => {
    const rootPx = parseFloat(getComputedStyle(document.documentElement).fontSize) || 16;
    axisLayout = compareDailyAxisLayoutFromRoot(rootPx);
    timelineCursor.reset();
    void loadTagClusters();
  });
  $: if (clusterRefreshToken) {
    void loadTagClusters();
  }
  onDestroy(() => {
    timelineCursor.reset();
  });

  const PINS_KEY = 'cc_trend_compare_pins';

  function readLocal<T>(key: string, fallback: T, isValid: (value: unknown) => boolean): T {
    if (!browser) return fallback;
    try {
      const raw = window.localStorage.getItem(key);
      if (raw === null) return fallback;
      const parsed = JSON.parse(raw);
      return isValid(parsed) ? (parsed as T) : fallback;
    } catch {
      return fallback;
    }
  }

  function writeLocal(key: string, value: unknown): void {
    if (!browser) return;
    try {
      // storage-exempt: generic helper, callers pass compare-panel UI keys only
      window.localStorage.setItem(key, JSON.stringify(value));
    } catch {
      // Quota or private-mode — silently ignore. Preference falls back to default next session.
    }
  }

  let pinned: string[] = clampPinnedIds(
    readLocal<string[]>(
      PINS_KEY,
      [],
      (value) => Array.isArray(value) && value.every((item) => typeof item === 'string')
    )
  );

  let axisScroller: HTMLDivElement;
  let lastAxisKey = '';
  let pendingFocusDate: string | null = null;
  let tagClusters: TagClustersResponse | null = null;

  $: tagClusterMeta = buildTagClusterMeta(tagClusters);
  $: tagClusterLabelsBinding = tagClusterMeta.labels;
  $: tagRowsWithClusters =
    showTags && tagHeatmap
      ? tagHeatmap.tags.filter((tag) => tagClusterMeta.byTagId.has(tag.tag_id))
      : [];
  $: clustersAvailable = tagClusterMeta.labels.length > 0 && tagRowsWithClusters.length > 0;
  $: clustersAvailableBinding = clustersAvailable;
  $: if (
    focusedClusterId !== null &&
    !tagClusterMeta.labels.some((cluster) => cluster.cluster_id === focusedClusterId)
  ) {
    focusedClusterId = null;
  }

  async function loadTagClusters(): Promise<void> {
    if (get(auth).status !== 'authenticated') return;
    try {
      if (get(devForceVisualizations)) {
        tagClusters = getDevPhaseFixture(get(devPhase)).tagClusters;
        return;
      }
      tagClusters = await fetchTagClusters();
    } catch {
      tagClusters = null;
    }
  }

  function focusCluster(clusterId: number | null): void {
    focusedClusterId = clusterId;
  }

  function activeDatesForRow(row: CoincidenceRow): string[] {
    return row.days.filter((day) => isRowActiveOnDay(row, day.date)).map((day) => day.date);
  }

  function openCheckQuestion(): void {
    if (pinned.length < 2) return;
    const firstRow = coincidenceRows.find((row) => row.id === pinned[0]);
    if (!firstRow) return;
    dispatch('checkQuestion', {
      windows: datesToEventWindows(activeDatesForRow(firstRow), firstRow.label),
      label: firstRow.label,
    });
  }

  function setMode(next: CompareMode): void {
    // #482: Strips now share the Lines bucket aggregation, so the zoom stage
    // carries across modes — no gate, no reset.
    mode = next;
    writeCompareMode(next);
    dispatch('modeChange', { value: next });
  }

  function setSortMode(next: CompareSortMode): void {
    sortMode = next;
    writeCompareSortMode(next);
    dispatch('sortChange', { value: next });
  }

  function setZoomStage(next: CompareZoomStageIndex): void {
    pendingFocusDate = null;
    zoomStage = next;
    writeCompareZoomStage(next);
    timelineCursor.clear();
  }

  function zoomOut(): void {
    setZoomStage(clampZoomStageForWindow(zoomStage + 1, windowDays));
  }

  function zoomIn(): void {
    setZoomStage(clampZoomStageForWindow(zoomStage - 1, windowDays));
  }

  /**
   * CAZ-2: multi-day tap zooms one stage finer and keeps the interval in view.
   * #482: also active in Strips mode now that strips share the bucket axis, so
   * zoomable heatmap/strip cells behave the same in both modes.
   */
  function zoomInBucket(bucket: AxisBucket): void {
    if (zoomStage === 0 || bucket.dates.length <= 1) return;
    pendingFocusDate = bucket.start;
    zoomStage = clampZoomStageForWindow(zoomStage - 1, windowDays);
    writeCompareZoomStage(zoomStage);
  }

  function handleZoomInBucket(event: CustomEvent<{ bucket: AxisBucket }>): void {
    zoomInBucket(event.detail.bucket);
  }

  function handlePinToggle(event: CustomEvent<{ rowId: string; pinned: boolean }>): void {
    const { rowId, pinned: shouldPin } = event.detail;
    if (shouldPin) {
      if (!canPinMore(pinned.length) || pinned.includes(rowId)) return;
      pinned = [...pinned, rowId];
    } else {
      pinned = pinned.filter((id) => id !== rowId);
    }
    writeLocal(PINS_KEY, pinned);
  }

  function setCoincidenceHighlight(next: boolean): void {
    coincidenceHighlight = next;
    writeCompareCoincidenceHighlight(next);
    dispatch('coincidenceChange', { value: next });
  }

  function setLag1Highlight(next: boolean): void {
    lag1Highlight = next;
    writeCompareLag1Highlight(next);
    dispatch('lag1Change', { value: next });
  }

  function dismissOverlayPinHint(): void {
    overlayHintDismissed = true;
    writeCompareOverlayHintDismissed(true);
    dispatch('overlayHintDismiss');
  }

  function joinSubjectLabels(labels: readonly string[]): string {
    if (labels.length === 0) return '';
    if (labels.length === 1) return labels[0]!;
    const andWord = $_('trends.compare.coincidence.and');
    if (labels.length === 2) return `${labels[0]} ${andWord} ${labels[1]}`;
    return `${labels.slice(0, -1).join(', ')} ${andWord} ${labels[labels.length - 1]}`;
  }

  async function scrollToLatest(): Promise<void> {
    await tick();
    if (axisScroller) axisScroller.scrollLeft = axisScroller.scrollWidth;
  }

  async function scrollDateIntoView(date: string): Promise<void> {
    await tick();
    if (!axisScroller) return;
    const targetBucket = findBucketForDate(axisBuckets, date);
    const focusKey = targetBucket?.start ?? date;
    const cell = axisScroller.querySelector(`[data-date="${focusKey}"]`);
    if (cell instanceof HTMLElement && typeof cell.scrollIntoView === 'function') {
      cell.scrollIntoView({ inline: 'center', block: 'nearest' });
    }
    timelineCursor.setDate(focusKey, 'tap');
  }

  $: rawAxisStart =
    tagHeatmap?.start_date ??
    symptomHeatmap?.start_date ??
    workContextHeatmap?.start_date ??
    points[0]?.period_start ??
    '';
  $: rawAxisEnd =
    tagHeatmap?.end_date ??
    symptomHeatmap?.end_date ??
    workContextHeatmap?.end_date ??
    points[points.length - 1]?.period_end ??
    points[points.length - 1]?.period_start ??
    '';
  /**
   * #676: heatmap/context bounds can extend past the user's first/last logged day
   * and leave an empty scroll region with no hard stop. Clamp the axis to days
   * that actually hold entries so the timeline stops at the data on both ends.
   */
  $: dataDates = points.filter((point) => point.entry_count > 0).map((point) => point.period_start);
  $: ({ start: axisStart, end: axisEnd } = clampAxisRangeToData(
    rawAxisStart,
    rawAxisEnd,
    dataDates
  ));
  $: axisDates = axisStart && axisEnd ? buildIsoDateRange(axisStart, axisEnd) : [];
  /**
   * #482: Strips share the Lines bucket aggregation (Option A — mean of logged
   * days, then divergent-encode), so the zoom stage applies to both modes.
   */
  $: effectiveZoomStage = zoomStage;
  $: axisBuckets = buildAxisBuckets(axisDates, effectiveZoomStage);
  $: bucketAxisLayout =
    effectiveZoomStage === 0
      ? axisLayout
      : {
          ...axisLayout,
          dayWidth: Math.max(axisLayout.dayWidth, 28),
        };
  $: maxZoomStage = maxZoomStageForWindow(windowDays);
  $: {
    const clamped = clampZoomStageForWindow(zoomStage, windowDays);
    if (clamped !== zoomStage) {
      zoomStage = clamped;
      writeCompareZoomStage(clamped);
    }
  }
  $: zoomDays = stageDays(effectiveZoomStage);
  $: canZoomOut = zoomStage < maxZoomStage;
  $: canZoomIn = zoomStage > 0;
  $: axisKey = `${axisStart}:${axisEnd}:${axisDates.length}:${effectiveZoomStage}:${mode}`;
  $: if (axisKey && axisKey !== lastAxisKey) {
    lastAxisKey = axisKey;
    if (pendingFocusDate) {
      const focus = pendingFocusDate;
      pendingFocusDate = null;
      void scrollDateIntoView(focus);
    } else {
      void scrollToLatest();
    }
  }
  /** Kontextzeilen only make sense when the selected range has at least one entry. */
  $: hasEntriesInRange = points.some((point) => point.entry_count > 0);

  $: cursorBucket = $timelineCursorDate
    ? findBucketForDate(axisBuckets, $timelineCursorDate)
    : null;
  $: cursorEntryDays = cursorBucket
    ? cursorBucket.dates.reduce((count, date) => {
        const point = points.find((item) => item.period_start === date);
        return count + (point && point.entry_count > 0 ? 1 : 0);
      }, 0)
    : 0;
  $: cursorCoverageLabel = cursorBucket
    ? $_(cursorBucket.partial ? 'trends.compare.zoom.partial' : 'trends.compare.zoom.coverage', {
        values: cursorBucket.partial
          ? { present: cursorBucket.presentDays, size: cursorBucket.dayCount }
          : { active: cursorEntryDays, present: cursorBucket.presentDays },
      })
    : '';
  $: cursorDetailLabel =
    cursorBucket && cursorCoverageLabel
      ? $_('trends.compare.zoom.detail', {
          values: {
            range: formatBucketRangeLabel(cursorBucket),
            coverage: cursorCoverageLabel,
          },
        })
      : '';

  /** #908: presence rows for coincidence — mirrors ComparisonHeatmap rawRows ids/labels. */
  $: coincidenceRows = [
    ...(showTags
      ? (tagHeatmap?.tags ?? []).map((tag): CoincidenceRow => ({
          id: tag.tag_id,
          label: tag.name,
          days: tag.days,
        }))
      : []),
    ...(showSymptoms
      ? (symptomHeatmap?.symptoms ?? []).map((symptom): CoincidenceRow => ({
          id: symptom.symptom_id,
          label: symptom.name,
          days: symptom.days,
        }))
      : []),
    ...(showWorkContexts
      ? (workContextHeatmap?.contexts ?? []).map((context): CoincidenceRow => ({
          id: `work_context:${context.context}`,
          label: $_(`entry.work_context.${context.context}`),
          days: context.days,
        }))
      : []),
  ];

  $: coincidence = deriveCoincidence(pinned, coincidenceRows);
  $: coincidenceByDate = new Map(coincidence.days.map((day) => [day.date, day]));
  $: coincidenceActive = coincidenceHighlight && coincidence.canHighlight;

  $: coincidenceMarkers = coincidenceActive
    ? coincidenceDaysToMarkers(
        coincidence.days,
        (labels) =>
          $_('trends.compare.coincidence.marker', {
            values: { subjects: joinSubjectLabels(labels) },
          }),
        $_('trends.compare.coincidence.legend')
      )
    : [];

  $: lag1 = deriveLag1(pinned, coincidenceRows);
  $: lag1ByDate = new Map(lag1.days.map((day) => [day.date, day]));
  $: lag1Active = lag1Highlight && lag1.canHighlight;

  $: lag1Markers = lag1Active
    ? lag1DaysToMarkers(
        lag1.days,
        (from, to) => $_('trends.compare.lag1.marker', { values: { from, to } }),
        $_('trends.compare.lag1.legend')
      )
    : [];

  $: activeMarkers = dedupeEventMarkers([...markers, ...coincidenceMarkers, ...lag1Markers]);

  $: cursorCoincidenceSubjects = (() => {
    if (!coincidenceActive || !$timelineCursorDate) return null;
    const exact = coincidenceByDate.get($timelineCursorDate);
    if (exact) return exact.subjects;
    if (!cursorBucket) return null;
    for (const date of cursorBucket.dates) {
      const hit = coincidenceByDate.get(date);
      if (hit) return hit.subjects;
    }
    return null;
  })();

  $: cursorCoincidenceLabel = cursorCoincidenceSubjects
    ? $_('trends.compare.coincidence.cursor', {
        values: {
          subjects: joinSubjectLabels(cursorCoincidenceSubjects.map((subject) => subject.label)),
        },
      })
    : '';

  $: cursorLag1Sequences = (() => {
    if (!lag1Active || !$timelineCursorDate) return null;
    const exact = lag1ByDate.get($timelineCursorDate);
    if (exact) return exact.sequences;
    if (!cursorBucket) return null;
    for (const date of cursorBucket.dates) {
      const hit = lag1ByDate.get(date);
      if (hit) return hit.sequences;
    }
    return null;
  })();

  $: cursorLag1Label = cursorLag1Sequences?.length
    ? cursorLag1Sequences
        .map((seq) =>
          $_('trends.compare.lag1.cursor', {
            values: { from: seq.from.label, to: seq.to.label },
          })
        )
        .join(' · ')
    : '';

  // #917: natural frequencies beside each overlay — counts with a denominator,
  // never rates or p-values (v1c decision in FEATURE_EVENT_INTERACTION_TIMELINE).
  $: coincidenceSummaryLines = coincidenceActive
    ? summarizeCoincidence(pinned, coincidenceRows).map((pair) =>
        $_('trends.compare.coincidence.summary', {
          values: {
            a: pair.a.label,
            b: pair.b.label,
            both: pair.both,
            aTotal: pair.aTotal,
            bTotal: pair.bTotal,
          },
        })
      )
    : [];

  // The markers only draw the pin-order direction, so tying the numbers to
  // lag1Active would hide exactly the pairs whose reverse order dominates.
  $: lag1Summaries = summarizeLag1(pinned, coincidenceRows, { axisDates });
  $: lag1SummaryLines = hasReportableLag1(lag1Summaries)
    ? lag1Summaries.map((pair) =>
        $_('trends.compare.lag1.summary', {
          values: {
            from: pair.from.label,
            to: pair.to.label,
            forward: pair.forward,
            forwardTotal: pair.forwardTotal,
            reverse: pair.reverse,
            reverseTotal: pair.reverseTotal,
          },
        })
      )
    : [];

  $: showFrequencyNote = coincidenceSummaryLines.length > 0 || lag1SummaryLines.length > 0;

  $: overlayAvailabilityBinding = {
    pinnedCount: pinned.length,
    coincidence: coincidence.canHighlight,
    lag1: lag1.canHighlight,
  };
</script>

<section class="compare" class:compare--compact={compactChrome} data-testid="trends-compare-panel">
  {#if !compactChrome}
    <header class="compare__header">
      <div>
        <h2>{$_('trends.compare.heading')}</h2>
        <p>{$_('trends.compare.body')}</p>
      </div>
      <div class="compare__layers" aria-label={$_('trends.compare.layers')}>
        <label>
          <input
            type="checkbox"
            checked={showTags}
            on:change={(event) =>
              dispatch('layerChange', {
                showTags: event.currentTarget.checked,
                showSymptoms,
                showWorkContexts,
              })}
          />
          {$_('trends.compare.tags')}
        </label>
        <label>
          <input
            type="checkbox"
            checked={showSymptoms}
            on:change={(event) =>
              dispatch('layerChange', {
                showTags,
                showSymptoms: event.currentTarget.checked,
                showWorkContexts,
              })}
          />
          {$_('trends.compare.symptoms')}
        </label>
        <label>
          <input
            type="checkbox"
            checked={showWorkContexts}
            on:change={(event) =>
              dispatch('layerChange', {
                showTags,
                showSymptoms,
                showWorkContexts: event.currentTarget.checked,
              })}
          />
          {$_('trends.compare.work_contexts')}
        </label>
      </div>
    </header>

    <div class="compare__controls" data-testid="trends-compare-controls">
      <div class="compare__mode" role="group" aria-label={$_('trends.compare.mode_label')}>
        <span class="compare__control-label">{$_('trends.compare.mode_label')}</span>
        <button
          type="button"
          class="compare__chip"
          class:compare__chip--active={mode === 'lines'}
          aria-pressed={mode === 'lines'}
          on:click={() => setMode('lines')}
        >
          {$_('trends.compare.mode_lines')}
        </button>
        <button
          type="button"
          class="compare__chip"
          class:compare__chip--active={mode === 'strips'}
          aria-pressed={mode === 'strips'}
          on:click={() => setMode('strips')}
        >
          {$_('trends.compare.mode_strips')}
        </button>
      </div>

      <label class="compare__sort">
        <span class="compare__control-label">{$_('trends.compare.sort_label')}</span>
        <select
          value={sortMode}
          on:change={(event) => setSortMode(event.currentTarget.value as CompareSortMode)}
        >
          <option value="frequency">{$_('trends.compare.sort_frequency')}</option>
          <option value="recent">{$_('trends.compare.sort_recent')}</option>
          <option value="correlation">{$_('trends.compare.sort_correlation')}</option>
          <option value="pinned">{$_('trends.compare.sort_pinned')}</option>
          <option value="clustered" disabled={!clustersAvailable}>
            {$_('trends.compare.sort_clustered')}
          </option>
        </select>
      </label>
    </div>
  {/if}

  {#if pinned.length >= 2}
    <p class="compare__check" data-testid="trends-compare-check-question">
      <a href="/insights">{$_('trends.compare.check_question')}</a>
      <span class="compare__check-hint">{$_('trends.compare.check_question_hint')}</span>
    </p>
  {/if}

  {#if clustersAvailable && showTags}
    <div
      class="compare__clusters"
      class:compare__clusters--compact={compactChrome}
      role="group"
      aria-label={$_('trends.compare.focus_label')}
      data-testid="trends-compare-focus"
    >
      <button
        type="button"
        class="compare__chip"
        class:compare__chip--active={focusedClusterId === null}
        aria-pressed={focusedClusterId === null}
        on:click={() => focusCluster(null)}
      >
        {$_('trends.compare.focus_all')}
      </button>
      {#each tagClusterMeta.labels as cluster (cluster.cluster_id)}
        <button
          type="button"
          class="compare__chip"
          class:compare__chip--active={focusedClusterId === cluster.cluster_id}
          aria-pressed={focusedClusterId === cluster.cluster_id}
          data-testid="trends-compare-focus-chip"
          on:click={() =>
            focusCluster(focusedClusterId === cluster.cluster_id ? null : cluster.cluster_id)}
        >
          {cluster.label}
        </button>
      {/each}
    </div>
  {/if}

  {#if axisDates.length > 0}
    <div class="compare__zoom-block" data-testid="trends-compare-zoom-block">
      <p class="compare__window-label" data-testid="trends-compare-window-label">
        {$_('habits.window_last', { values: { n: windowDays } })}
      </p>
      <div
        class="compare__zoom"
        role="group"
        aria-label={$_('trends.compare.zoom.label')}
        data-testid="trends-compare-zoom"
      >
        <button
          type="button"
          class="compare__zoom-btn"
          data-testid="trends-compare-zoom-decrease"
          aria-label={$_('trends.compare.zoom.decrease_aria')}
          disabled={!canZoomOut}
          on:click={zoomOut}
        >
          −
        </button>
        <span class="compare__zoom-status" data-testid="trends-compare-zoom-status">
          {$_('trends.compare.zoom.status', { values: { days: zoomDays } })}
        </span>
        <button
          type="button"
          class="compare__zoom-btn"
          data-testid="trends-compare-zoom-increase"
          aria-label={$_('trends.compare.zoom.increase_aria')}
          disabled={!canZoomIn}
          on:click={zoomIn}
        >
          +
        </button>
      </div>
      <CompareOverlayControls
        {coincidenceHighlight}
        {lag1Highlight}
        {overlayHintDismissed}
        availability={overlayAvailabilityBinding}
        on:coincidenceChange={(event) => setCoincidenceHighlight(event.detail.value)}
        on:lag1Change={(event) => setLag1Highlight(event.detail.value)}
        on:dismissPinHint={dismissOverlayPinHint}
      >
        <svelte:fragment slot="coincidence-detail">
          {#if coincidenceActive}
            <!-- Count first, disclaimer second: the number is what the user came for. -->
            {#each coincidenceSummaryLines as line, index (index)}
              <p
                class="compare__coincidence-summary"
                data-testid="trends-compare-coincidence-summary"
              >
                {line}
              </p>
            {/each}
            <p class="compare__coincidence-legend" data-testid="trends-compare-coincidence-legend">
              {$_('trends.compare.coincidence.legend')}
            </p>
          {/if}
        </svelte:fragment>
        <svelte:fragment slot="lag1-detail">
          <!-- Not gated on lag1Active: the markers only draw the pin-order
               direction, so that gate would hide reverse-heavy pairs. -->
          {#if lag1SummaryLines.length > 0}
            {#each lag1SummaryLines as line, index (index)}
              <p class="compare__coincidence-summary" data-testid="trends-compare-lag1-summary">
                {line}
              </p>
            {/each}
            <p class="compare__coincidence-legend" data-testid="trends-compare-lag1-legend">
              {$_('trends.compare.lag1.legend')}
            </p>
          {/if}
        </svelte:fragment>
      </CompareOverlayControls>
      {#if esmUnlocked && pinned.length >= 2}
        <Button
          variant="secondary"
          size="sm"
          data-testid="trends-compare-check-question"
          on:click={openCheckQuestion}
        >
          {$_('trends.compare.check_question')}
        </Button>
      {/if}
      {#if showFrequencyNote}
        <p class="compare__coincidence-hint" data-testid="trends-compare-frequency-note">
          {$_('trends.compare.frequency_note')}
        </p>
      {/if}
      <p class="compare__zoom-hint" data-testid="trends-compare-zoom-encoding">
        {$_('trends.compare.zoom.encoding_hint')}
      </p>
      {#if mode === 'lines' && zoomStage > 0}
        <p class="compare__zoom-hint" data-testid="trends-compare-zoom-tap-hint">
          {$_('trends.compare.zoom.tap_hint')}
        </p>
      {/if}
      {#if cursorDetailLabel}
        <p class="compare__zoom-detail" data-testid="trends-compare-zoom-detail">
          {cursorDetailLabel}
        </p>
      {/if}
      <!-- #919: keyboard users move the cursor without seeing the chart, so the
           overlay read-out has to be announced rather than only drawn. -->
      <div aria-live="polite" data-testid="trends-compare-overlay-live">
        {#if cursorCoincidenceLabel}
          <p class="compare__zoom-detail" data-testid="trends-compare-coincidence-detail">
            {cursorCoincidenceLabel}
          </p>
        {/if}
        {#if cursorLag1Label}
          <p class="compare__zoom-detail" data-testid="trends-compare-lag1-detail">
            {cursorLag1Label}
          </p>
        {/if}
      </div>
    </div>
  {/if}

  <div
    class="compare__axis-scroller"
    bind:this={axisScroller}
    aria-label={$_('trends.compare.shared_axis')}
  >
    {#if mode === 'strips'}
      <UnifiedStripChart
        {points}
        {enabled}
        {loading}
        {axisDates}
        buckets={axisBuckets}
        axisLayout={bucketAxisLayout}
        markers={activeMarkers}
        enableCursor
        on:selectDate={(event) => dispatch('selectDate', { date: event.detail.date })}
        on:zoomInBucket={handleZoomInBucket}
      />
    {:else}
      <MetricTimeseries
        {points}
        {range}
        {enabled}
        {loading}
        {axisDates}
        buckets={axisBuckets}
        axisLayout={bucketAxisLayout}
        markers={activeMarkers}
        {noteDates}
        enableCursor
        on:selectDate={(event) => dispatch('selectDate', { date: event.detail.date })}
        on:zoomInBucket={handleZoomInBucket}
      />
    {/if}

    {#if hasEntriesInRange}
      <ComparisonHeatmap
        {tagHeatmap}
        {symptomHeatmap}
        {workContextHeatmap}
        {showTags}
        {showSymptoms}
        {showWorkContexts}
        {loading}
        dates={axisDates}
        buckets={axisBuckets}
        axisLayout={bucketAxisLayout}
        markers={activeMarkers}
        enableCursor
        {sortMode}
        {pinned}
        maxPins={MAX_COMPARE_PINS}
        {correlationScores}
        clusterMeta={tagClusterMeta}
        bind:focusedClusterId
        scrollable={false}
        autoScroll={false}
        {pruneSparseAxes}
        on:selectDate={(event) => dispatch('selectDate', { date: event.detail.date })}
        on:zoomInBucket={handleZoomInBucket}
        on:pinToggle={handlePinToggle}
      />
    {/if}
  </div>
</section>

<style>
  .compare {
    display: grid;
    gap: var(--space-4);
  }

  .compare--compact {
    gap: 0;
  }

  .compare__header {
    display: flex;
    align-items: flex-start;
    justify-content: space-between;
    gap: var(--space-4);
  }

  .compare__header h2,
  .compare__header p {
    margin: 0;
  }

  .compare__header h2 {
    font-size: var(--text-lg);
  }

  .compare__header p {
    margin-top: var(--space-1);
    color: var(--color-text-muted);
    font-size: var(--text-sm);
  }

  .compare__layers {
    display: flex;
    flex-wrap: wrap;
    justify-content: flex-end;
    gap: var(--space-2);
  }

  .compare__layers label {
    min-height: 44px;
    display: inline-flex;
    align-items: center;
    gap: var(--space-1);
    font-size: var(--text-sm);
    font-weight: 700;
  }

  .compare__axis-scroller {
    display: grid;
    gap: var(--space-4);
    overflow-x: auto;
    padding-bottom: var(--space-2);
    /* #629: hard stop at first/last data — no rubber-band past the axis. */
    overscroll-behavior-x: contain;
  }

  /* Sprint 2 (ADR-0035) — token-only, hue-agnostic controls. */
  .compare__controls {
    display: flex;
    flex-wrap: wrap;
    align-items: center;
    gap: var(--space-3);
  }

  .compare__check {
    margin: 0;
    display: flex;
    flex-direction: column;
    gap: 0.25rem;
    font-size: var(--text-sm);
  }

  .compare__check a {
    color: var(--color-primary);
    font-weight: 600;
    text-decoration: none;
  }

  .compare__check-hint {
    color: var(--color-text-muted);
    font-size: var(--text-xs);
  }

  .compare__mode {
    display: inline-flex;
    align-items: center;
    gap: var(--space-1);
    background: var(--color-strip-track-bg);
    border-radius: var(--radius-md, 8px);
    padding: 2px;
  }

  .compare__control-label {
    color: var(--color-text-muted);
    font-size: var(--text-xs);
    padding: 0 var(--space-1);
  }

  .compare__chip {
    background: transparent;
    border: 0;
    padding: var(--space-1) var(--space-2);
    border-radius: var(--radius-md, 8px);
    color: var(--color-text);
    cursor: pointer;
    font-size: var(--text-sm);
    font-weight: 600;
    min-height: var(--tap-target);
  }

  .compare__chip--active {
    background: var(--color-surface);
    color: var(--color-fg);
    box-shadow: 0 0 0 1px var(--color-border-chart, var(--color-cursor-halo));
  }

  .compare__chip:focus-visible {
    outline: 2px solid var(--color-cursor-halo);
    outline-offset: 1px;
  }

  .compare__sort {
    display: inline-flex;
    align-items: center;
    gap: var(--space-1);
    font-size: var(--text-sm);
  }

  .compare__sort select {
    min-height: var(--tap-target);
    padding: var(--space-1) var(--space-2);
    border-radius: var(--radius-md, 8px);
    border: 1px solid var(--color-border, var(--color-border-chart));
    background: var(--color-surface);
    color: var(--color-text);
    font: inherit;
  }

  .compare__clusters {
    display: flex;
    flex-wrap: wrap;
    gap: var(--space-2);
  }

  .compare__clusters--compact {
    gap: var(--space-1);
    margin-top: var(--space-1);
  }

  .compare__clusters--compact .compare__chip {
    font-size: var(--text-xs);
    padding: var(--space-1) var(--space-2);
  }

  .compare__zoom-block {
    display: grid;
    gap: var(--space-1);
  }

  .compare__window-label {
    margin: 0;
    color: var(--color-text-muted);
    font-size: var(--text-sm);
    font-weight: 600;
  }

  .compare__zoom {
    display: inline-flex;
    align-items: center;
    gap: var(--space-2);
    flex-wrap: wrap;
  }

  .compare__zoom-hint,
  .compare__zoom-detail {
    margin: 0;
    color: var(--color-text-muted);
    font-size: var(--text-xs);
  }

  .compare__zoom-detail {
    font-weight: 600;
  }

  .compare__coincidence-hint,
  .compare__coincidence-legend {
    margin: 0;
    color: var(--color-text-muted);
    font-size: var(--text-xs);
  }

  /* #917: counts sit closer to the eye than the legend disclaimer. */
  .compare__coincidence-summary {
    margin: 0;
    color: var(--color-fg);
    font-size: var(--text-xs);
    font-variant-numeric: tabular-nums;
  }

  .compare__zoom-btn {
    min-width: var(--tap-target);
    min-height: var(--tap-target);
    padding: 0 var(--space-2);
    border-radius: var(--radius-md, 8px);
    border: 1px solid var(--color-border, var(--color-border-chart));
    background: var(--color-surface);
    color: var(--color-text);
    font-size: var(--text-lg);
    font-weight: 700;
    line-height: 1;
    cursor: pointer;
  }

  .compare__zoom-btn:disabled {
    opacity: 0.45;
    cursor: not-allowed;
  }

  .compare__zoom-btn:focus-visible {
    outline: 2px solid var(--color-cursor-halo);
    outline-offset: 1px;
  }

  .compare__zoom-status {
    color: var(--color-text-muted);
    font-size: var(--text-sm);
    font-weight: 600;
    min-width: 7rem;
    text-align: center;
  }

  @media (max-width: 480px) {
    .compare__header {
      flex-direction: column;
    }

    .compare__layers {
      justify-content: flex-start;
    }
  }
</style>
