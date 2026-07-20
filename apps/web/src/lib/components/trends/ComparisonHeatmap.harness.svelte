<script lang="ts">
  import ComparisonHeatmap from './ComparisonHeatmap.svelte';
  import type { TagHeatmapResponse } from '$lib/api/stats';

  export let pruneSparseAxes = true;
  export let dates = ['2026-07-01', '2026-07-02', '2026-07-03'];

  const tagHeatmap: TagHeatmapResponse = {
    start_date: '2026-07-01',
    end_date: '2026-07-03',
    tags: [
      {
        tag_id: 't1',
        slug: 'run',
        name: 'Run',
        category: 'activity',
        color: null,
        days: [
          { date: '2026-07-01', count: 2 },
          { date: '2026-07-02', count: 0 },
          { date: '2026-07-03', count: 0 },
        ],
      },
      {
        tag_id: 't2',
        slug: 'empty',
        name: 'Empty',
        category: 'activity',
        color: null,
        days: [
          { date: '2026-07-01', count: 0 },
          { date: '2026-07-02', count: 0 },
          { date: '2026-07-03', count: 0 },
        ],
      },
    ],
  };
</script>

<ComparisonHeatmap
  {tagHeatmap}
  showTags
  showSymptoms={false}
  showWorkContexts={false}
  {dates}
  {pruneSparseAxes}
  scrollable={false}
  autoScroll={false}
/>
