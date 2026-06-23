// @ts-nocheck
// url=https://www.figma.com/design/XjijHnzMJubA1iuPQxHOwS?node-id=9-27
// source=apps/web/src/lib/components/common/Panel.svelte
// component=Panel
import figma from 'figma';

const instance = figma.selectedInstance;
const variant = instance.getEnum('Variant', {
  Plain: 'plain',
  Bordered: 'bordered',
  Elevated: 'elevated',
  Chart: 'chart',
  Danger: 'danger',
});
const body = instance.getString('Body');

export default {
  id: 'panel',
  imports: ['import Panel from "$lib/components/common/Panel.svelte";'],
  example: figma.code`<Panel variant="${variant}">${body}</Panel>`,
  metadata: { nestable: true },
};
