// url=https://www.figma.com/design/XjijHnzMJubA1iuPQxHOwS?node-id=79-83
// source=apps/web/src/lib/components/insights/InsightQualityMeter.svelte
// component=InsightQualityMeter
// @ts-nocheck
import figma from 'figma';

const instance = figma.selectedInstance;
const level = instance.getEnum('Level', {
  Early: 'early',
  Provisional: 'provisional',
  Robust: 'robust',
});
const loading = level === 'early';

export default {
  id: 'insight-quality-meter',
  imports: [
    'import InsightQualityMeter from "$lib/components/insights/InsightQualityMeter.svelte";',
  ],
  example: figma.code`<!-- Legacy reference: production UI uses InsightStageHeader -->
<InsightQualityMeter
  dayEntryDates={dayEntryDates}
  insightTier="none"
  confidenceScore={0.35}
  ${loading ? 'loading' : ''}
/>`,
  metadata: { nestable: true, legacy: true },
};
