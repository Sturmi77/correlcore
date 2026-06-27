// url=https://www.figma.com/design/XjijHnzMJubA1iuPQxHOwS?node-id=131-31
// source=apps/web/src/lib/components/trends/MobileTrendsSummary.svelte
// component=MobileTrendsSummary
// @ts-nocheck
import figma from 'figma';

const instance = figma.selectedInstance;
const state = instance.getEnum('State', {
  Ready: 'ready',
  Empty: 'empty',
});
const loading = false;

export default {
  id: 'mobile-trends-summary',
  imports: ['import MobileTrendsSummary from "$lib/components/trends/MobileTrendsSummary.svelte";'],
  example: figma.code`<MobileTrendsSummary
  points={timeseriesPoints}
  tagHeatmap={tagHeatmap}
  symptomHeatmap={symptomHeatmap}
  range="week"
  ${state === 'empty' ? 'points={[]}' : ''}
  ${loading ? 'loading' : ''}
/>`,
  metadata: { nestable: true },
};
