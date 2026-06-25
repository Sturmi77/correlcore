// url=https://www.figma.com/design/XjijHnzMJubA1iuPQxHOwS?node-id=6-64
// source=apps/web/src/lib/components/common/Button.svelte
// component=Button
// @ts-nocheck
import figma from 'figma';

const instance = figma.selectedInstance;
const label = instance.getString('Label');
const variant = instance.getEnum('Style', {
  Primary: 'primary',
  Secondary: 'secondary',
  Ghost: 'ghost',
  Danger: 'danger',
  Link: 'link',
});
const size = instance.getEnum('Size', {
  Small: 'sm',
  Medium: 'md',
  Large: 'lg',
});
const disabled = instance.getEnum('State', {
  Default: false,
  Disabled: true,
});

export default {
  id: 'button',
  imports: ['import Button from "$lib/components/common/Button.svelte";'],
  example: figma.code`<Button variant="${variant}" size="${size}" ${disabled ? 'disabled' : ''}>${label}</Button>`,
  metadata: { nestable: true },
};
