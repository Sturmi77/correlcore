// @ts-nocheck
// url=https://www.figma.com/design/XjijHnzMJubA1iuPQxHOwS?node-id=19-113
// source=apps/web/src/lib/components/home/HomeSummary.svelte
// component=HomeSummary
import figma from 'figma';

const instance = figma.selectedInstance;
const loading = instance.getEnum('State', {
  Ready: false,
  Loading: true,
});

export default {
  id: 'home-summary',
  imports: ['import HomeSummary from "$lib/components/home/HomeSummary.svelte";'],
  example: figma.code`<HomeSummary entries={entries} consistencyEntries={consistencyEntries} todayIso={todayIso} ${loading ? 'loading' : ''} />`,
  metadata: { nestable: true },
};
