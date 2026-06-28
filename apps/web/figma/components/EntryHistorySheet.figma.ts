// url=https://www.figma.com/design/XjijHnzMJubA1iuPQxHOwS?node-id=144-4145
// source=apps/web/src/lib/components/trends/EntryHistorySheet.svelte
// component=EntryHistorySheet
// @ts-nocheck
import figma from 'figma';

const instance = figma.selectedInstance;
const state = instance.getEnum('State', {
  Ready: 'ready',
  Loading: 'loading',
  Empty: 'empty',
  Error: 'error',
});

export default {
  id: 'entry-history-sheet',
  imports: ['import EntryHistorySheet from "$lib/components/trends/EntryHistorySheet.svelte";'],
  example: figma.code`<EntryHistorySheet
  open={true}
  date="2026-06-12"
  ${state === 'loading' ? 'loading' : ''}
  ${state === 'error' ? 'error="Could not load entry history."' : ''}
  details={${state === 'empty' ? '[]' : 'entryHistoryDetails'}}
  on:close={() => (open = false)}
/>`,
  metadata: { nestable: true },
};
