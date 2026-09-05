<script lang="ts">
  import { onMount } from 'svelte';
  import { _ } from 'svelte-i18n';
  import InlineAlert from '$lib/components/common/InlineAlert.svelte';
  import Panel from '$lib/components/common/Panel.svelte';
  import ScreenHeader from '$lib/components/common/ScreenHeader.svelte';
  import InsightSectionsEditor from '$lib/components/settings/InsightSectionsEditor.svelte';
  import {
    fetchUserPreferences,
    updateUserPreferences,
    type InsightSectionPreference,
    type UserPreferencesResponse,
  } from '$lib/api/preferences';
  import { DEFAULT_INSIGHT_SECTIONS, mergeInsightSections } from '$lib/utils/insightSections';
  import { registerPageRefresh } from '$lib/stores/pageRefresh';

  let preferences: UserPreferencesResponse | null = null;
  let sections: InsightSectionPreference[] = DEFAULT_INSIGHT_SECTIONS.map((section) => ({
    ...section,
  }));
  let loading = true;
  let busy = false;
  let error = '';

  async function loadPreferences(): Promise<void> {
    loading = true;
    try {
      preferences = await fetchUserPreferences();
      sections = mergeInsightSections(preferences.insight_sections);
    } catch (err) {
      error = err instanceof Error ? err.message : $_('settings.insights.error_load');
    } finally {
      loading = false;
    }
  }

  async function persistSections(next: InsightSectionPreference[]): Promise<void> {
    const previous = sections;
    sections = next;
    busy = true;
    error = '';
    try {
      preferences = await updateUserPreferences({ insight_sections: next });
      sections = mergeInsightSections(preferences.insight_sections);
    } catch (err) {
      sections = previous;
      error = err instanceof Error ? err.message : $_('settings.insights.error_save');
    } finally {
      busy = false;
    }
  }

  onMount(() => {
    void loadPreferences();
    return registerPageRefresh(loadPreferences);
  });
</script>

<svelte:head>
  <title>{$_('settings.insights.title')} - {$_('app.name')}</title>
</svelte:head>

<main class="insights-settings screen-stack">
  <ScreenHeader
    title={$_('settings.insights.title')}
    subtitle={$_('settings.insights.subtitle')}
    compact
    back={{ href: '/settings', label: $_('nav.settings') }}
  />

  <Panel variant="bordered">
    <div class="insights-settings__intro">
      <h2>{$_('settings.insights.heading')}</h2>
      <p>{$_('settings.insights.body')}</p>
    </div>
    <InsightSectionsEditor
      {sections}
      disabled={busy || loading}
      on:change={({ detail }) => void persistSections(detail)}
    />
  </Panel>

  {#if error}
    <InlineAlert variant="error" message={error} />
  {/if}
</main>

<style>
  .insights-settings {
    width: min(100%, 44rem);
    margin: 0 auto;
  }

  .insights-settings__intro h2,
  .insights-settings__intro p {
    margin: 0;
  }

  .insights-settings__intro {
    display: grid;
    gap: var(--space-2);
    margin-bottom: var(--space-4);
  }

  .insights-settings__intro h2 {
    font-size: var(--text-base);
  }

  .insights-settings__intro p {
    color: var(--color-text-muted);
    font-size: var(--text-sm);
    line-height: 1.5;
  }
</style>
