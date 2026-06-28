// url=https://www.figma.com/design/XjijHnzMJubA1iuPQxHOwS?node-id=144-4086
// source=apps/web/src/lib/components/insights/TagCooccurrenceHeatmap.svelte
// component=TagCooccurrenceHeatmap
// @ts-nocheck
import figma from 'figma';

const instance = figma.selectedInstance;
const sortMode = instance.getEnum('Sort', {
  Alphabetical: 'alphabetical',
  Clustered: 'clustered',
});
const range = instance.getEnum('Range', {
  '30D': '30d',
  '90D': '90d',
  '1Y': '1y',
});

export default {
  id: 'tag-cooccurrence-heatmap',
  imports: [
    'import TagCooccurrenceHeatmap from "$lib/components/insights/TagCooccurrenceHeatmap.svelte";',
  ],
  example: figma.code`<TagCooccurrenceHeatmap
  data={cooccurrence}
  loading={loading}
  range="${range}"
  sortMode="${sortMode}"
  enableClusterSort={true}
  on:selectPair={(event) => openHistory(event)}
  on:sortModeChange={(event) => (sortMode = event.detail.sortMode)}
/>`,
  metadata: { nestable: true },
};
