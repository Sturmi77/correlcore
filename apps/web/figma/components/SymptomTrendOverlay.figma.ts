// url=https://www.figma.com/design/XjijHnzMJubA1iuPQxHOwS?node-id=144-4189
// source=apps/web/src/lib/components/insights/symptoms/SymptomTrendOverlay.svelte
// component=SymptomTrendOverlay
// @ts-nocheck
import figma from 'figma';

const instance = figma.selectedInstance;
const phase = instance.getEnum('Phase', {
  Early: 'early_patterns',
  Provisional: 'provisional',
});

export default {
  id: 'symptom-trend-overlay',
  imports: [
    'import SymptomTrendOverlay from "$lib/components/insights/symptoms/SymptomTrendOverlay.svelte";',
  ],
  example: figma.code`<SymptomTrendOverlay
  symptomName="Headache"
  data={symptomTrendPoints}
  phase="${phase}"
  rollingWindowDays={7}
/>`,
  metadata: { nestable: true },
};
