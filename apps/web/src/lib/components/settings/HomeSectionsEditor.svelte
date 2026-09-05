<script lang="ts">
  import { createEventDispatcher } from 'svelte';
  import type { HomeSectionPreference } from '$lib/api/preferences';
  import SectionsEditor from '$lib/components/settings/SectionsEditor.svelte';
  import {
    DEFAULT_HOME_SECTIONS,
    mergeHomeSections,
    normalizeHomeSectionsForSave,
  } from '$lib/utils/homeSections';
  import type { SectionPreference } from '$lib/utils/sectionPreferences';

  export let sections: HomeSectionPreference[] = DEFAULT_HOME_SECTIONS;
  export let disabled = false;

  const dispatch = createEventDispatcher<{
    change: HomeSectionPreference[];
  }>();

  const merge = (stored: SectionPreference[] | null | undefined): SectionPreference[] =>
    mergeHomeSections(stored as HomeSectionPreference[] | null | undefined);
  const normalize = (next: SectionPreference[]): SectionPreference[] =>
    normalizeHomeSectionsForSave(next as HomeSectionPreference[]);
</script>

<SectionsEditor
  {sections}
  {disabled}
  defaults={DEFAULT_HOME_SECTIONS}
  {merge}
  {normalize}
  testIdPrefix="home"
  i18nPrefix="settings.home"
  on:change={(event) => dispatch('change', event.detail as HomeSectionPreference[])}
/>
