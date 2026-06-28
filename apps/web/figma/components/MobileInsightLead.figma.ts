// url=https://www.figma.com/design/XjijHnzMJubA1iuPQxHOwS?node-id=98-1541
// source=apps/web/src/lib/components/insights/MobileInsightLead.svelte
// component=MobileInsightLead
// @ts-nocheck
import figma from 'figma';

const instance = figma.selectedInstance;
const showMilestone = instance.getEnum('Milestone', {
  Hidden: false,
  Visible: true,
});

export default {
  id: 'mobile-insight-lead',
  imports: ['import MobileInsightLead from "$lib/components/insights/MobileInsightLead.svelte";'],
  example: figma.code`<MobileInsightLead insight={insight} maturity={maturity} entryCount={entryCount} inactiveTagIds={inactiveTagIds} ${showMilestone ? 'showMilestone' : ''} />`,
  metadata: { nestable: true },
};
