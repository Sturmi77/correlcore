// url=https://www.figma.com/design/XjijHnzMJubA1iuPQxHOwS?node-id=144-97
// source=apps/web/src/lib/components/insights/symptoms/SymptomCooccurrenceDetailSheet.svelte
// component=SymptomCooccurrenceDetailSheet
// @ts-nocheck
import figma from 'figma';

const instance = figma.selectedInstance;
const confounder = instance.getEnum('Confounder', {
  None: 'none',
  Weekday: 'weekday',
});

export default {
  id: 'symptom-cooccurrence-detail-sheet',
  imports: [
    'import SymptomCooccurrenceDetailSheet from "$lib/components/insights/symptoms/SymptomCooccurrenceDetailSheet.svelte";',
  ],
  example: figma.code`<SymptomCooccurrenceDetailSheet
  open={true}
  cell={${confounder === 'weekday' ? 'confoundedSymptomTagCell' : 'symptomTagCell'}}
  on:close={() => (open = false)}
  on:openDisclaimer={() => (disclaimerOpen = true)}
/>`,
  metadata: { nestable: true },
};
