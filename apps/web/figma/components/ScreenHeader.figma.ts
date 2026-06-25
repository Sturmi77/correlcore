// url=https://www.figma.com/design/XjijHnzMJubA1iuPQxHOwS?node-id=11-33
// source=apps/web/src/lib/components/common/ScreenHeader.svelte
// component=ScreenHeader
// @ts-nocheck
import figma from 'figma';

const instance = figma.selectedInstance;
const compact = instance.getEnum('Compact', {
  False: false,
  True: true,
});
const title = instance.getString('Title');
const subtitle = instance.getString('Subtitle');
const eyebrow = instance.getString('Eyebrow');

export default {
  id: 'screen-header',
  imports: ['import ScreenHeader from "$lib/components/common/ScreenHeader.svelte";'],
  example: figma.code`<ScreenHeader title="${title}" subtitle="${subtitle}" eyebrow="${eyebrow}" ${compact ? 'compact' : ''} />`,
  metadata: { nestable: true },
};
