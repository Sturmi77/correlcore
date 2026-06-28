// url=https://www.figma.com/design/XjijHnzMJubA1iuPQxHOwS?node-id=144-4169
// source=apps/web/src/lib/components/insights/CooccurrenceEntrySheet.svelte
// component=CooccurrenceEntrySheet
// @ts-nocheck
import figma from 'figma';

const instance = figma.selectedInstance;
const state = instance.getEnum('State', {
  Ready: 'ready',
  Loading: 'loading',
  Empty: 'empty',
});

export default {
  id: 'cooccurrence-entry-sheet',
  imports: [
    'import CooccurrenceEntrySheet from "$lib/components/insights/CooccurrenceEntrySheet.svelte";',
  ],
  example: figma.code`<CooccurrenceEntrySheet
  open={true}
  title="Headache + Sport"
  ${state === 'loading' ? 'loading' : ''}
  details={${state === 'empty' ? '[]' : 'sharedDayDetails'}}
  on:close={() => (open = false)}
/>`,
  metadata: { nestable: true },
};
