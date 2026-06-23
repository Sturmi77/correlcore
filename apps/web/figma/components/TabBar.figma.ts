// @ts-nocheck
// url=https://www.figma.com/design/XjijHnzMJubA1iuPQxHOwS?node-id=13-45
// source=apps/web/src/lib/components/common/TabBar.svelte
// component=TabBar
import figma from 'figma';

const instance = figma.selectedInstance;
const value = instance.getEnum('Active', {
  First: 'overview',
  Second: 'insights',
  Third: 'settings',
});
const disabled = instance.getEnum('State', {
  Default: false,
  Disabled: true,
});
const tab1 = instance.getString('Tab label 1');
const tab2 = instance.getString('Tab label 2');
const tab3 = instance.getString('Tab label 3');

export default {
  id: 'tab-bar',
  imports: ['import TabBar from "$lib/components/common/TabBar.svelte";'],
  example: figma.code`<TabBar
  value="${value}"
  ariaLabel="Tabs"
  options={[
    { id: 'overview', label: '${tab1}', disabled: ${disabled} },
    { id: 'insights', label: '${tab2}', disabled: ${disabled} },
    { id: 'settings', label: '${tab3}', disabled: ${disabled} }
  ]}
/>`,
  metadata: { nestable: true }
};
