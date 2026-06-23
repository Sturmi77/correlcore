// @ts-nocheck
// url=https://www.figma.com/design/XjijHnzMJubA1iuPQxHOwS?node-id=12-45
// source=apps/web/src/lib/components/common/SegmentedControl.svelte
// component=SegmentedControl
import figma from 'figma';

const instance = figma.selectedInstance;
const value = instance.getEnum('Active', {
  First: 'first',
  Second: 'second',
  Third: 'third',
});
const disabled = instance.getEnum('State', {
  Default: false,
  Disabled: true,
});
const option1 = instance.getString('Option 1');
const option2 = instance.getString('Option 2');
const option3 = instance.getString('Option 3');

export default {
  id: 'segmented-control',
  imports: ['import SegmentedControl from "$lib/components/common/SegmentedControl.svelte";'],
  example: figma.code`<SegmentedControl
  value="${value}"
  ariaLabel="Segmented control"
  options={[
    { id: 'first', label: '${option1}', disabled: ${disabled} },
    { id: 'second', label: '${option2}', disabled: ${disabled} },
    { id: 'third', label: '${option3}', disabled: ${disabled} }
  ]}
/>`,
  metadata: { nestable: true },
};
