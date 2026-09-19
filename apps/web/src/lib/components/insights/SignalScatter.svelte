<script lang="ts">
  /**
   * G1 scatter + L3 mean±SE bands for signal verification (Phase 7).
   * Behind progressive disclosure on /insights/signal/[id].
   */
  import { _ } from 'svelte-i18n';

  export let points: { date: string; value: number; present: boolean }[] = [];
  export let withMean: number | null = null;
  export let withoutMean: number | null = null;
  export let withSe: number | null = null;
  export let withoutSe: number | null = null;
  export let subjectLabel = '';
  export let showUncertainty = true;

  const width = 320;
  const height = 180;
  const pad = { top: 16, right: 16, bottom: 28, left: 36 };
  const plotW = width - pad.left - pad.right;
  const plotH = height - pad.top - pad.bottom;

  function yFor(value: number): number {
    return pad.top + (1 - (value - 1) / 4) * plotH;
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
  <text x={pad.left - 6} y={yFor(5) + 3} class="scatter__tick">5</text>
  <text x={pad.left - 6} y={yFor(1) + 3} class="scatter__tick">1</text>
  <text x={pad.left + plotW * 0.32} y={height - 8} class="scatter__tick" text-anchor="middle">
    {$_('insights.signal.scatter_with')}
  </text>
  <text x={pad.left + plotW * 0.68} y={height - 8} class="scatter__tick" text-anchor="middle">
    {$_('insights.signal.scatter_without')}
  </text>

  {#if showUncertainty && withMean != null && withSe != null}
    <rect
      x={pad.left + plotW * 0.18}
      y={yFor(withMean + withSe)}
      width={plotW * 0.28}
      height={Math.max(2, yFor(withMean - withSe) - yFor(withMean + withSe))}
      class="scatter__band scatter__band--with"
      data-testid="signal-scatter-band-with"
    />
  {/if}
  {#if showUncertainty && withoutMean != null && withoutSe != null}
    <rect
      x={pad.left + plotW * 0.54}
      y={yFor(withoutMean + withoutSe)}
      width={plotW * 0.28}
      height={Math.max(2, yFor(withoutMean - withoutSe) - yFor(withoutMean + withoutSe))}
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
