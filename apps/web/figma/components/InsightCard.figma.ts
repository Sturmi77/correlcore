// url=https://www.figma.com/design/XjijHnzMJubA1iuPQxHOwS?node-id=79-55
// source=apps/web/src/lib/components/insights/InsightCard.svelte
// component=InsightCard
// @ts-nocheck
import figma from 'figma';

const instance = figma.selectedInstance;
const state = instance.getEnum('State', {
  Ready: 'ready',
  Loading: 'loading',
  Empty: 'empty',
  Error: 'error',
  Confounded: 'confounded',
});

const loading = state === 'loading';
const error = state === 'error' ? 'Unable to load insight.' : '';
const emptyProps = state === 'empty' ? 'insight={null}' : 'insight={insight}';
const confoundedProps =
  state === 'confounded'
    ? "insight={{ ...insight, payload: { ...insight.payload, confounder: 'weekday' } }}"
    : 'insight={insight}';

export default {
  id: 'insight-card',
  imports: ['import InsightCard from "$lib/components/insights/InsightCard.svelte";'],
  example: figma.code`<InsightCard
  ${state === 'empty' ? emptyProps : confoundedProps}
  maturity={maturity}
  inactiveTagIds={inactiveTagIds}
  ${loading ? 'loading' : ''}
  ${error ? `error="${error}"` : ''}
  on:retry={() => refresh()}
  on:dismiss
/>`,
  metadata: { nestable: true },
};
