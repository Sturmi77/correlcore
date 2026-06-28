// url=https://www.figma.com/design/XjijHnzMJubA1iuPQxHOwS?node-id=144-59
// source=apps/web/src/lib/components/insights/TagGroupsSection.svelte
// component=TagGroupsSection
// @ts-nocheck
import figma from 'figma';

const instance = figma.selectedInstance;
const state = instance.getEnum('State', {
  Ready: 'ready',
  Insufficient: 'insufficient',
  Loading: 'loading',
});
const kind = instance.getEnum('Kind', {
  TagsOnly: 'tags-only',
  Mixed: 'mixed',
});

export default {
  id: 'tag-groups-section',
  imports: ['import TagGroupsSection from "$lib/components/insights/TagGroupsSection.svelte";'],
  example: figma.code`<TagGroupsSection
  data={${kind === 'mixed' ? 'mixedTagClusters' : 'tagClusters'}}
  ${state === 'loading' ? 'loading' : ''}
/>`,
  metadata: { nestable: true },
};
