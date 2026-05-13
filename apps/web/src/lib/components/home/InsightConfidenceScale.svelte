<script lang="ts">
  /**
   * Backward-compatibility re-export stub — ADR-0018.
   *
   * The canonical component lives at components/insights/InsightConfidenceScale.svelte.
   * This stub keeps the existing import in routes/+page.svelte working without
   * a separate refactor commit. It passes all props through unchanged.
   *
   * Remove this stub once +page.svelte is updated to import from components/insights/.
   */
  import InsightConfidenceScaleImpl from '$lib/components/insights/InsightConfidenceScale.svelte';
  import type { InsightTier } from '$lib/api/insights';

  export let confidenceScore = 0.05;
  export let currentTier: InsightTier = 'none';
  export let entryCount = 0;
  export let loading = false;
  export let showRawPercent = false;
</script>

<InsightConfidenceScaleImpl
  {confidenceScore}
  {currentTier}
  {entryCount}
  {loading}
  {showRawPercent}
/>
