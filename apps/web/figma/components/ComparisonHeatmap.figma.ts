// @ts-nocheck
// url=https://www.figma.com/design/XjijHnzMJubA1iuPQxHOwS?node-id=20-268
// source=apps/web/src/lib/components/trends/ComparisonHeatmap.svelte
// component=ComparisonHeatmap
import figma from 'figma';

const instance = figma.selectedInstance;
const kind = instance.getEnum('Kind', {
  Tags: 'tags',
  Symptoms: 'symptoms'
});
const state = instance.getEnum('State', {
  Ready: 'ready',
  Loading: 'loading',
  Empty: 'empty'
});

export default {
  id: 'comparison-heatmap',
  imports: ['import ComparisonHeatmap from "$lib/components/trends/ComparisonHeatmap.svelte";'],
  example: figma.code`<ComparisonHeatmap
  tagHeatmap={tagHeatmap}
  symptomHeatmap={symptomHeatmap}
  showTags={${kind === 'tags'}}
  showSymptoms={${kind === 'symptoms'}}
  loading={${state === 'loading'}}
/>`,
  metadata: { nestable: true }
};
