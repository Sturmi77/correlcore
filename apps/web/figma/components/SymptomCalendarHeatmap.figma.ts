// url=https://www.figma.com/design/XjijHnzMJubA1iuPQxHOwS?node-id=144-4120
// source=apps/web/src/lib/components/insights/symptoms/SymptomCalendarHeatmap.svelte
// component=SymptomCalendarHeatmap
// @ts-nocheck
import figma from 'figma';

const instance = figma.selectedInstance;
const phase = instance.getEnum('Phase', {
  Early: 'early_patterns',
  Provisional: 'provisional',
  Robust: 'robust',
});

export default {
  id: 'symptom-calendar-heatmap',
  imports: [
    'import SymptomCalendarHeatmap from "$lib/components/insights/symptoms/SymptomCalendarHeatmap.svelte";',
  ],
  example: figma.code`<SymptomCalendarHeatmap
  symptom={selectedSymptom}
  startDate={rangeStart}
  endDate={rangeEnd}
  phase="${phase}"
/>`,
  metadata: { nestable: true },
};
