// url=https://www.figma.com/design/XjijHnzMJubA1iuPQxHOwS?node-id=146-4151
// source=apps/web/src/lib/components/insights/symptoms/SymptomAnalyticsSection.svelte
// component=SymptomAnalyticsSection
// @ts-nocheck
import figma from 'figma';

const instance = figma.selectedInstance;
const state = instance.getEnum('State', {
  Ready: 'ready',
  Loading: 'loading',
});

export default {
  id: 'symptom-analytics-section',
  imports: [
    'import SymptomAnalyticsSection from "$lib/components/insights/symptoms/SymptomAnalyticsSection.svelte";',
  ],
  example: figma.code`<SymptomAnalyticsSection
  heatmap={symptomHeatmap}
  entries={recentEntries}
  cooccurrence={symptomCooccurrence}
  cooccurrenceLoading={cooccurrenceLoading}
  phase={maturity?.phase ?? null}
  ${state === 'loading' ? 'loading' : ''}
  on:selectDate={(event) => openEntryHistory(event.detail.date)}
  on:selectCell={(event) => openSymptomDetail(event.detail.cell)}
/>`,
  metadata: { nestable: true },
};
