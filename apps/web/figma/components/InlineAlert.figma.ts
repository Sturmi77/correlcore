// @ts-nocheck
// url=https://www.figma.com/design/XjijHnzMJubA1iuPQxHOwS?node-id=10-43
// source=apps/web/src/lib/components/common/InlineAlert.svelte
// component=InlineAlert
import figma from 'figma';

const instance = figma.selectedInstance;
const variant = instance.getEnum('Variant', {
  Info: 'info',
  Success: 'success',
  Warning: 'warning',
  Error: 'error',
});
const actionVisible = instance.getEnum('Action', {
  Hidden: false,
  Visible: true,
});
const message = instance.getString('Message');
const actionLabel = instance.getString('Action label');

export default {
  id: 'inline-alert',
  imports: ['import InlineAlert from "$lib/components/common/InlineAlert.svelte";'],
  example: figma.code`<InlineAlert variant="${variant}" message="${message}" ${actionVisible ? figma.code`actionLabel="${actionLabel}"` : ''} />`,
  metadata: { nestable: true },
};
