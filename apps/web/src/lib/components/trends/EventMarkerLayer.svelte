<script lang="ts" context="module">
  /**
   * EventMarkerLayer — M3.8 Sprint 1 (ADR-0035)
   *
   * Renders neutral vertical markers across the shared daily axis used
   * by MetricTimeseries / TagHeatmap / ComparisonHeatmap. Markers are
   * theme-agnostic: they read --color-event-marker / --color-event-marker-soft
   * and never hardcode a hue. See ADR-0035 §10.
   *
   * Marker kinds are descriptive only. Callers compute the marker set
   * from domain data (phase transitions, symptom onsets, habit goal
   * changes, cycle phases). The component itself is rendering-only —
   * no business logic, no API calls.
   */
  export type EventMarkerKind =
    | 'phase_transition'
    | 'symptom_onset'
    | 'habit_change'
    | 'cycle_phase'
    | 'compare_lag1'
    | 'generic';

  export interface EventMarker {
    /** Inclusive start (ISO date YYYY-MM-DD). */
    date: string;
    /** Optional inclusive end — when set the marker renders as a soft band. */
    endDate?: string;
    /** Marker kind for screen readers + dataset attributes (styling stays uniform). */
    kind?: EventMarkerKind;
    /** Accessible label, surfaced via aria-label and tooltip. */
    label: string;
    /** Optional secondary description (e.g. phase name, severity). */
    description?: string;
  }

  /** Collapse markers that share the same display axis key (e.g. after bucket remap). */
  export function dedupeEventMarkers(markers: readonly EventMarker[]): EventMarker[] {
    const seen = new Set<string>();
    const out: EventMarker[] = [];
    for (const marker of markers) {
      const key = `${marker.date}|${marker.endDate ?? ''}|${marker.kind ?? 'generic'}`;
      if (seen.has(key)) continue;
      seen.add(key);
      out.push(marker);
    }
    return out;
  }
</script>

<script lang="ts">
  import { _ } from 'svelte-i18n';
  import { dailyAxisXForDate, type DailyAxisLayout } from '$lib/utils/charts';

  export let markers: readonly EventMarker[] = [];
  export let axisDates: readonly string[];
  export let axisLayout: DailyAxisLayout;
  export let height: number;
  /** Optional Y offset where the marker line starts (default 0). */
  export let top = 0;

  type ResolvedMarker = {
    marker: EventMarker;
    xStart: number;
    bandX: number | null;
    bandWidth: number | null;
    soft: boolean;
  };

  // #919: the same string drives aria-label and <title> — a hover-only tooltip
  // left keyboard and screen-reader users without the marker at all.
  function markerAccessibleName(marker: EventMarker): string {
    return marker.description ? `${marker.label} — ${marker.description}` : marker.label;
  }

  $: uniqueMarkers = dedupeEventMarkers(markers);
  $: resolved = uniqueMarkers.flatMap((marker): ResolvedMarker[] => {
    const xStart = dailyAxisXForDate(marker.date, axisDates, axisLayout);
    if (xStart === null) return [];
    // Soft band when endDate is set (inclusive). Single-day bands use dayWidth
    // because center-to-center width would be 0 when date === endDate (#908).
    if (marker.endDate) {
      const xEnd = dailyAxisXForDate(marker.endDate, axisDates, axisLayout);
      if (xEnd === null) return [];
      const half = axisLayout.dayWidth / 2;
      return [
        {
          marker,
          xStart,
          bandX: xStart - half,
          bandWidth: Math.max(axisLayout.dayWidth, xEnd - xStart + axisLayout.dayWidth),
          soft: true,
        },
      ];
    }
    return [{ marker, xStart, bandX: null, bandWidth: null, soft: false }];
  });
</script>

{#if resolved.length > 0}
  <g class="event-markers" role="group" aria-label={$_('trends.markers.aria')}>
    {#each resolved as { marker, xStart, bandX, bandWidth, soft } (marker.date + ':' + (marker.endDate ?? '') + ':' + (marker.kind ?? 'generic'))}
      {#if soft && bandX !== null && bandWidth !== null}
        <rect
          class="event-markers__band"
          x={bandX}
          y={top}
          width={bandWidth}
          {height}
          data-kind={marker.kind ?? 'generic'}
          data-testid="event-marker-band"
          role="img"
          aria-label={markerAccessibleName(marker)}
        >
          <title>{markerAccessibleName(marker)}</title>
        </rect>
      {:else}
        <line
          class="event-markers__line"
          x1={xStart}
          x2={xStart}
          y1={top}
          y2={top + height}
          data-kind={marker.kind ?? 'generic'}
          role="img"
          aria-label={markerAccessibleName(marker)}
        >
          <title>{markerAccessibleName(marker)}</title>
        </line>
      {/if}
    {/each}
  </g>
{/if}

<style>
  .event-markers__line {
    stroke: var(--color-event-marker);
    stroke-width: 1.5;
    stroke-dasharray: 4 3;
    pointer-events: auto;
  }

  .event-markers__band {
    fill: var(--color-event-marker-soft);
    pointer-events: auto;
  }

  /* Subtle kind variants — still rendered with the same neutral token,
     only stroke-dasharray differs so the rule "no hue per kind" holds. */
  .event-markers__line[data-kind='symptom_onset'] {
    stroke-dasharray: 2 3;
  }

  .event-markers__line[data-kind='habit_change'] {
    stroke-dasharray: 6 4;
  }

  .event-markers__line[data-kind='cycle_phase'] {
    stroke-dasharray: 1 2;
  }

  /* #910: Lag-1 — narrower dashed line vs A∩B soft bands. */
  .event-markers__line[data-kind='compare_lag1'] {
    stroke-width: 1;
    stroke-dasharray: 3 2;
  }
</style>
