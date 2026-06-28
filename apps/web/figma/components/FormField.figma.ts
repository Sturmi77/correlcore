// url=https://www.figma.com/design/XjijHnzMJubA1iuPQxHOwS?node-id=17-58
// source=apps/web/src/lib/components/entries/TagPicker.svelte
// component=FormField
// @ts-nocheck
import figma from 'figma';

const instance = figma.selectedInstance;
const label = instance.getString('Label');
const value = instance.getString('Value');
const errorText = instance.getString('Error text');
const kind = instance.getEnum('Kind', {
  Text: 'text',
  Select: 'select',
});
const fieldState = instance.getEnum('State', {
  Default: 'default',
  Focus: 'focus',
  Error: 'error',
  Disabled: 'disabled',
});
const disabled = fieldState === 'disabled';
const hasError = fieldState === 'error';

export default {
  id: 'form-field',
  imports: ['import TagPicker from "$lib/components/entries/TagPicker.svelte";'],
  example: figma.code`<!-- FormField pattern: TagPicker custom-tag create form (${kind}, ${fieldState}) -->
<TagPicker bind:selected={selectedTagIds} ${disabled ? 'disabled' : ''} />
<!-- Field "${label}" value="${value}"${hasError ? ` error="${errorText}"` : ''} -->`,
  metadata: { nestable: true, designSubcomponent: true },
};
