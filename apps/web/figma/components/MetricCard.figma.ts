// url=https://www.figma.com/design/XjijHnzMJubA1iuPQxHOwS?node-id=19-53
// source=apps/web/src/lib/components/home/MetricCard.svelte
// component=MetricCard
// @ts-nocheck
import figma from 'figma';

const instance = figma.selectedInstance;
const metric = instance.getEnum('Metric', {
  Mood: 'mood_score',
  Energy: 'energy',
  Stress: 'stress',
  Consistency: 'tracking_consistency',
  Count: 'count',
});
const loading = instance.getEnum('State', {
  Ready: false,
  Loading: true,
});
const label = instance.getString('Label');
const value = instance.getString('Value');
const unit = instance.getString('Unit');

export default {
  id: 'metric-card',
  imports: ['import MetricCard from "$lib/components/home/MetricCard.svelte";'],
  example: figma.code`<MetricCard metric="${metric}" label="${label}" value="${value}" unit="${unit}" ${loading ? 'loading' : ''} />`,
  metadata: { nestable: true },
};
