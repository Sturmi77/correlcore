<script lang="ts">
  /**
   * TimelineCursorOverlay — M3.8 Sprint 1 (ADR-0035)
   *
   * Renders a single vertical cursor line at the date stored in the
   * shared `timelineCursor` store. All trend components that share the
   * compare axis embed this overlay so a hover/focus in one component
   * is visually reflected in every other one.
   *
   * Token-only styling — components must not hardcode any hue.
   */
  import { dailyAxisXForDate, type DailyAxisLayout } from '$lib/utils/charts';
  import { timelineCursor } from '$lib/stores/timelineCursor';

  export let axisDates: readonly string[];
  export let axisLayout: DailyAxisLayout;
  export let height: number;
  export let top = 0;

  $: ({ date, source } = $timelineCursor);
  $: x = date ? dailyAxisXForDate(date, axisDates, axisLayout) : null;
  $: showHalo = source === 'focus' || source === 'keyboard';
</script>

{#if x !== null}
  <g class="cursor" aria-hidden="true" data-source={source ?? 'none'}>
    {#if showHalo}
      <line class="cursor__halo" x1={x} x2={x} y1={top} y2={top + height} />
    {/if}
    <line class="cursor__line" x1={x} x2={x} y1={top} y2={top + height} />
  </g>
{/if}

<style>
  .cursor__line {
    stroke: var(--color-cursor);
    stroke-width: 1.5;
    pointer-events: none;
  }

  .cursor__halo {
    stroke: var(--color-cursor-halo);
    stroke-width: 8;
    stroke-linecap: round;
    pointer-events: none;
  }
</style>
