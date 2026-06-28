// url=https://www.figma.com/design/XjijHnzMJubA1iuPQxHOwS?node-id=144-3995
// source=apps/web/src/lib/components/insights/symptoms/SymptomCooccurrenceHeatmap.svelte
// component=SymptomCooccurrenceHeatmap
// @ts-nocheck
import figma from 'figma';

const instance = figma.selectedInstance;
const phase = instance.getEnum('Phase', {
  Early: 'early_patterns',
  Provisional: 'provisional',
  Robust: 'robust',
});
const sortMode = instance.getEnum('Sort', {
  Alphabetical: 'alphabetical',
  Clustered: 'clustered',
});

export default {
  id: 'symptom-cooccurrence-heatmap',
  imports: [
    'import SymptomCooccurrenceHeatmap from "$lib/components/insights/symptoms/SymptomCooccurrenceHeatmap.svelte";',
  ],
  example: figma.code`<SymptomCooccurrenceHeatmap
  data={symptomCooccurrence}
  loading={loading}
  phase="${phase}"
  sortMode="${sortMode}"
  on:selectCell={(event) => openDetail(event.detail.cell)}
/>`,
  metadata: { nestable: true },
};
