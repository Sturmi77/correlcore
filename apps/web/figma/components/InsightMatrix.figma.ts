// url=https://www.figma.com/design/XjijHnzMJubA1iuPQxHOwS?node-id=131-62
// source=apps/web/src/lib/components/insights/InsightMatrix.svelte
// component=InsightMatrix
// @ts-nocheck
import figma from 'figma';

const instance = figma.selectedInstance;
const variant = instance.getEnum('Variant', {
  List: 'list',
  Chart: 'chart',
});

export default {
  id: 'insight-matrix',
  imports: ['import InsightMatrix from "$lib/components/insights/InsightMatrix.svelte";'],
  example: figma.code`<InsightMatrix insights={insights} />`,
  metadata: { nestable: true, variant },
};
