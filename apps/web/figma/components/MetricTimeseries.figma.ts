// @ts-nocheck
// url=https://www.figma.com/design/XjijHnzMJubA1iuPQxHOwS?node-id=20-102
// source=apps/web/src/lib/components/trends/MetricTimeseries.svelte
// component=MetricTimeseries
import figma from 'figma';

const instance = figma.selectedInstance;
const state = instance.getEnum('State', {
  Ready: 'ready',
  Loading: 'loading',
  Empty: 'empty'
});

export default {
  id: 'metric-timeseries',
  imports: ['import MetricTimeseries from "$lib/components/trends/MetricTimeseries.svelte";'],
  example: figma.code`<MetricTimeseries points={points} range="week" enabled={enabled} loading={${state === 'loading'}} />`,
  metadata: { nestable: true }
};
