<script lang="ts">
  import { createEventDispatcher } from 'svelte';
  import type { InsightSectionPreference } from '$lib/api/preferences';
  import SectionsEditor from '$lib/components/settings/SectionsEditor.svelte';
  import {
    DEFAULT_INSIGHT_SECTIONS,
    LOCKED_INSIGHT_SECTION_KEYS,
    mergeInsightSections,
    normalizeInsightSectionsForSave,
  } from '$lib/utils/insightSections';
  import type { SectionPreference } from '$lib/utils/sectionPreferences';

  export let sections: InsightSectionPreference[] = DEFAULT_INSIGHT_SECTIONS;
  export let disabled = false;

  const dispatch = createEventDispatcher<{
    change: InsightSectionPreference[];
  }>();

  const merge = (stored: SectionPreference[] | null | undefined): SectionPreference[] =>
    mergeInsightSections(stored as InsightSectionPreference[] | null | undefined);
  const normalize = (next: SectionPreference[]): SectionPreference[] =>
    normalizeInsightSectionsForSave(next as InsightSectionPreference[]);
</script>

<SectionsEditor
  {sections}
  {disabled}
  defaults={DEFAULT_INSIGHT_SECTIONS}
  {merge}
  {normalize}
  lockedKeys={LOCKED_INSIGHT_SECTION_KEYS}
  testIdPrefix="insights"
  i18nPrefix="settings.insights"
  on:change={(event) => dispatch('change', event.detail as InsightSectionPreference[])}
/>
