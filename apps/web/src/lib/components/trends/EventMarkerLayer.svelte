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
    'phase_transition' | 'symptom_onset' | 'habit_change' | 'cycle_phase' | 'generic';

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

  $: uniqueMarkers = dedupeEventMarkers(markers);
  $: resolved = uniqueMarkers
    .map((marker) => {
      const xStart = dailyAxisXForDate(marker.date, axisDates, axisLayout);
      const xEnd = marker.endDate ? dailyAxisXForDate(marker.endDate, axisDates, axisLayout) : null;
      if (xStart === null) return null;
      return { marker, xStart, xEnd };
    })
    .filter(
      (item): item is { marker: EventMarker; xStart: number; xEnd: number | null } => item !== null
    );
</script>

{#if resolved.length > 0}
  <g class="event-markers" role="group" aria-label={$_('trends.markers.aria')}>
    {#each resolved as { marker, xStart, xEnd } (marker.date + ':' + (marker.endDate ?? ''))}
      {#if xEnd !== null && xEnd > xStart}
        <rect
          class="event-markers__band"
          x={xStart}
          y={top}
          width={xEnd - xStart}
          {height}
          data-kind={marker.kind ?? 'generic'}
        >
          <title>{marker.label}{marker.description ? ` — ${marker.description}` : ''}</title>
        </rect>
      {:else}
        <line
          class="event-markers__line"
          x1={xStart}
          x2={xStart}
          y1={top}
          y2={top + height}
          data-kind={marker.kind ?? 'generic'}
        >
          <title>{marker.label}{marker.description ? ` — ${marker.description}` : ''}</title>
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
</style>
