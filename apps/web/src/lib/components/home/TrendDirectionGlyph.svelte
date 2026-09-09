<script lang="ts">
  import Minus from '@lucide/svelte/icons/minus';
  import TrendingDown from '@lucide/svelte/icons/trending-down';
  import TrendingUp from '@lucide/svelte/icons/trending-up';
  import { ICON_SIZE_SM } from '$lib/constants/iconSizes';
  import type { VisibleTrendDirection } from '$lib/utils/metricTrend';

  export let direction: VisibleTrendDirection;
  /** Pixel size for Lucide. Caret/chip stay smaller than the SM icon cluster. */
  export let size: number = ICON_SIZE_SM;
</script>

{#if direction === 'up'}
  <TrendingUp {size} aria-hidden="true" />
{:else if direction === 'down'}
  <TrendingDown {size} aria-hidden="true" />
{:else}
  <Minus {size} aria-hidden="true" />
{/if}
