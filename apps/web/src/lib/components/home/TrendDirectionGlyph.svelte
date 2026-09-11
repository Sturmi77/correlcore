<script lang="ts">
  import Minus from '@lucide/svelte/icons/minus';
  import TrendingDown from '@lucide/svelte/icons/trending-down';
  import TrendingUp from '@lucide/svelte/icons/trending-up';
  import type { VisibleTrendDirection } from '$lib/utils/metricTrend';

  export let direction: VisibleTrendDirection;
  /**
   * Lucide fallback size in px. CSS sizes the SVG to 1em so cramped Home
   * chips/cells can scale the glyph without clipping a 14px icon.
   */
  export let size: number = 12;
</script>

<span class="trend-direction-glyph" data-direction={direction}>
  {#if direction === 'up'}
    <TrendingUp {size} color="currentColor" aria-hidden="true" />
  {:else if direction === 'down'}
    <TrendingDown {size} color="currentColor" aria-hidden="true" />
  {:else}
    <Minus {size} color="currentColor" aria-hidden="true" />
  {/if}
</span>

<style>
  .trend-direction-glyph {
    display: inline-flex;
    flex: 0 0 auto;
    align-items: center;
    justify-content: center;
    line-height: 0;
    color: inherit;
  }

  .trend-direction-glyph :global(svg) {
    display: block;
    width: 1em;
    height: 1em;
    overflow: visible;
  }
</style>
