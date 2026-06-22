// @ts-nocheck
// url=https://www.figma.com/design/XjijHnzMJubA1iuPQxHOwS?node-id=16-107
// source=apps/web/src/lib/components/entries/ScaleSlider.svelte
// component=ScaleSlider
import figma from 'figma';

const instance = figma.selectedInstance;
const scaleType = instance.getEnum('Scale', {
  Mood: 'mood',
  Energy: 'energy',
  Stress: 'stress',
  Default: 'default',
});
const disabled = instance.getEnum('State', {
  Default: false,
  Disabled: true,
});
const label = instance.getString('Label');
const value = instance.getString('Value');

export default {
  id: 'scale-slider',
  imports: ['import ScaleSlider from "$lib/components/entries/ScaleSlider.svelte";'],
  example: figma.code`<ScaleSlider
  id="${scaleType}-score"
  bind:value={${Number(value) || 3}}
  label="${label}"
  decrementLabel="Decrease ${label}"
  incrementLabel="Increase ${label}"
  scaleType="${scaleType}"
  ${disabled ? 'disabled' : ''}
/>`,
  metadata: { nestable: true }
};
