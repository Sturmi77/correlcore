// url=https://www.figma.com/design/XjijHnzMJubA1iuPQxHOwS?node-id=17-18
// source=apps/web/src/lib/components/entries/TagPicker.svelte
// component=TagChip
// @ts-nocheck
import figma from 'figma';

const instance = figma.selectedInstance;
const label = instance.getString('Label');
const selected = instance.getEnum('Selected', {
  False: false,
  True: true,
});
const chipState = instance.getEnum('State', {
  Default: 'default',
  Disabled: 'disabled',
  Limit: 'limit',
});
const disabled = chipState === 'disabled' || chipState === 'limit';

export default {
  id: 'tag-chip',
  imports: ['import TagPicker from "$lib/components/entries/TagPicker.svelte";'],
  example: figma.code`<!-- TagChip is rendered inside TagPicker; bind selected IDs -->
<TagPicker bind:selected={selectedTagIds} ${disabled ? 'disabled' : ''} />
<!-- Chip "${label}" aria-pressed=${selected} -->`,
  metadata: { nestable: true, designSubcomponent: true },
};
