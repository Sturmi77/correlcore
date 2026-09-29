<script lang="ts">
  /**
   * G1 scatter + L3 mean±SE bands for signal verification (Phase 7).
   * Behind progressive disclosure on /insights/signal/[id].
   */
  import { _ } from 'svelte-i18n';
  import { displayMetricValue } from '$lib/utils/metrics';
  import type { EntryMetricField } from '$lib/config/metrics';

  export let points: { date: string; value: number; present: boolean }[] = [];
  export let withMean: number | null = null;
  export let withoutMean: number | null = null;
  export let withSe: number | null = null;
  export let withoutSe: number | null = null;
  export let subjectLabel = '';
  export let showUncertainty = true;
  /**
   * Which metric the values belong to. Verification returns raw values, and
   * stress runs the other way round — plotting 5 at the top for every metric
   * put this chart at odds with Trends and with every other metric display in
   * the app (#955).
   */
  export let metric: EntryMetricField = 'mood_score';

  /** Raw → the 1–5 goodness scale the rest of the app plots. */
  const toDisplay = (raw: number): number => displayMetricValue(metric, raw);

  /**
   * Band geometry from the two raw bounds. On an inverted metric `mean + se`
   * plots *below* `mean - se`, so subtracting the two in a fixed order yields a
   * negative height and the band collapses to its minimum.
   */
  function bandFor(mean: number, se: number): { y: number; height: number } {
    const a = yFor(mean + se);
    const b = yFor(mean - se);
    const top = Math.min(a, b);
    return { y: top, height: Math.max(2, Math.abs(b - a)) };
  }

  const width = 320;
  const height = 180;
  const pad = { top: 16, right: 16, bottom: 28, left: 36 };
  const plotW = width - pad.left - pad.right;
  const plotH = height - pad.top - pad.bottom;

  function yFor(value: number): number {
    return pad.top + (1 - (toDisplay(value) - 1) / 4) * plotH;
  }

  function xFor(present: boolean, index: number, total: number): number {
    const lane = present ? 0.32 : 0.68;
    const jitter = total <= 1 ? 0 : ((index % 7) - 3) / 3;
    return pad.left + plotW * (lane + jitter * 0.08);
  }

  $: withPoints = points.filter((p) => p.present);
  $: withoutPoints = points.filter((p) => !p.present);
</script>

<svg
  class="scatter"
  viewBox={`0 0 ${width} ${height}`}
  role="img"
  aria-label={$_('insights.signal.scatter_aria', { values: { subject: subjectLabel } })}
  data-testid="signal-scatter"
>
  <line
    x1={pad.left}
    y1={pad.top + plotH}
    x2={pad.left + plotW}
    y2={pad.top + plotH}
    class="scatter__axis"
  />
  <line x1={pad.left} y1={pad.top} x2={pad.left} y2={pad.top + plotH} class="scatter__axis" />
  <text x={pad.left - 6} y={pad.top + 3} class="scatter__tick">5</text>
  <text x={pad.left - 6} y={pad.top + plotH + 3} class="scatter__tick">1</text>
  <text x={pad.left + plotW * 0.32} y={height - 8} class="scatter__tick" text-anchor="middle">
    {$_('insights.signal.scatter_with')}
  </text>
  <text x={pad.left + plotW * 0.68} y={height - 8} class="scatter__tick" text-anchor="middle">
    {$_('insights.signal.scatter_without')}
  </text>

  {#if showUncertainty && withMean != null && withSe != null}
    <rect
      x={pad.left + plotW * 0.18}
      y={bandFor(withMean, withSe).y}
      width={plotW * 0.28}
      height={bandFor(withMean, withSe).height}
      class="scatter__band scatter__band--with"
      data-testid="signal-scatter-band-with"
    />
  {/if}
  {#if showUncertainty && withoutMean != null && withoutSe != null}
    <rect
      x={pad.left + plotW * 0.54}
      y={bandFor(withoutMean, withoutSe).y}
      width={plotW * 0.28}
      height={bandFor(withoutMean, withoutSe).height}
      class="scatter__band scatter__band--without"
      data-testid="signal-scatter-band-without"
    />
  {/if}

  {#each withPoints as point, index}
    <circle
      cx={xFor(true, index, withPoints.length)}
      cy={yFor(point.value)}
      r="3.2"
      class="scatter__dot scatter__dot--with"
    />
  {/each}
  {#each withoutPoints as point, index}
    <circle
      cx={xFor(false, index, withoutPoints.length)}
      cy={yFor(point.value)}
      r="3.2"
      class="scatter__dot scatter__dot--without"
    />
  {/each}

  {#if withMean != null}
    <line
      x1={pad.left + plotW * 0.18}
      x2={pad.left + plotW * 0.46}
      y1={yFor(withMean)}
      y2={yFor(withMean)}
      class="scatter__mean scatter__mean--with"
    />
  {/if}
  {#if withoutMean != null}
    <line
      x1={pad.left + plotW * 0.54}
      x2={pad.left + plotW * 0.82}
      y1={yFor(withoutMean)}
      y2={yFor(withoutMean)}
      class="scatter__mean scatter__mean--without"
    />
  {/if}
</svg>

<style>
  .scatter {
    width: 100%;
    max-width: 22rem;
    height: auto;
    display: block;
  }
  .scatter__axis {
    stroke: oklch(from var(--color-text) l c h / 0.2);
    stroke-width: 1;
  }
  .scatter__tick {
    fill: var(--color-text-faint);
    /* token-exempt: axis micro-label needs px precision at this size (F-10). */
    font-size: 9px;
    text-anchor: end;
  }
  .scatter__dot--with {
    fill: var(--color-primary);
    opacity: 0.75;
  }
  .scatter__dot--without {
    fill: var(--color-text-muted);
    opacity: 0.55;
  }
  .scatter__mean {
    stroke-width: 1.5;
  }
  .scatter__mean--with {
    stroke: var(--color-primary);
  }
  .scatter__mean--without {
    stroke: var(--color-text-muted);
  }
  .scatter__band {
    opacity: 0.18;
  }
  .scatter__band--with {
    fill: var(--color-primary);
  }
  .scatter__band--without {
    fill: var(--color-text-muted);
  }
</style>
