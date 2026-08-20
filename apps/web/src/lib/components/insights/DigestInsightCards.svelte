<script lang="ts">
  import type { InsightDigestItem, InsightResponse } from '$lib/api/insights';
  import InsightCard from '$lib/components/insights/InsightCard.svelte';

  // Shared rendering for the digest cards, used by both the /insights/digest
  // page and the one-time weekly digest modal (#739). Keeps the item→card
  // mapping in one place.
  export let insights: InsightDigestItem[];
  export let referenceDate = '';

  function toInsightResponse(item: InsightDigestItem): InsightResponse {
    return {
      id: item.id,
      user_id: '',
      insight_type: item.insight_type,
      tier: 'developing',
      metric: item.metric,
      subject_type: null,
      subject_id: null,
      subject_label: null,
      effect_size: item.effect_size,
      confidence: item.confidence,
      sample_n: 0,
      statement: item.statement,
      flags: { medical_disclaimer_required: true, causal_claim: false },
      payload: {},
      generated_for_date: referenceDate,
      generated_at: referenceDate,
      created_at: referenceDate,
      updated_at: referenceDate,
    };
  }
</script>

<ul class="digest-cards">
  {#each insights as item (item.id)}
    <li>
      <InsightCard
        insight={toInsightResponse(item)}
        showMaturityBadge={false}
        dismissable={false}
      />
    </li>
  {/each}
</ul>

<style>
  .digest-cards {
    list-style: none;
    margin: 0;
    padding: 0;
    display: grid;
    gap: var(--space-3);
  }
</style>
