// url=https://www.figma.com/design/XjijHnzMJubA1iuPQxHOwS?node-id=79-111
// source=apps/web/src/lib/components/insights/InsightStageHeader.svelte
// component=InsightStageHeader
// @ts-nocheck
import figma from 'figma';

const instance = figma.selectedInstance;
const phase = instance.getEnum('Phase', {
  Collecting: 'collecting',
  Early: 'early_patterns',
  Robust: 'robust',
});

export default {
  id: 'insight-stage-header',
  imports: ['import InsightStageHeader from "$lib/components/insights/InsightStageHeader.svelte";'],
  example: figma.code`<InsightStageHeader maturity={maturityForPhase('${phase}')} />`,
  metadata: { nestable: true },
};
