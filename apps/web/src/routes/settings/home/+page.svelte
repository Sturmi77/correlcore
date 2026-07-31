<script lang="ts">
  import { onMount } from 'svelte';
  import { _ } from 'svelte-i18n';
  import Button from '$lib/components/common/Button.svelte';
  import InlineAlert from '$lib/components/common/InlineAlert.svelte';
  import Panel from '$lib/components/common/Panel.svelte';
  import ScreenHeader from '$lib/components/common/ScreenHeader.svelte';
  import HomeSectionsEditor from '$lib/components/settings/HomeSectionsEditor.svelte';
  import {
    fetchUserPreferences,
    updateUserPreferences,
    type HomeSectionPreference,
    type UserPreferencesResponse,
  } from '$lib/api/preferences';
  import { DEFAULT_HOME_SECTIONS, mergeHomeSections } from '$lib/utils/homeSections';
  import { registerPageRefresh } from '$lib/stores/pageRefresh';

  let preferences: UserPreferencesResponse | null = null;
  let sections: HomeSectionPreference[] = DEFAULT_HOME_SECTIONS.map((section) => ({ ...section }));
  let busy = false;
  let error = '';

  async function loadPreferences(): Promise<void> {
    try {
      preferences = await fetchUserPreferences();
      sections = mergeHomeSections(preferences.home_sections);
    } catch (err) {
      error = err instanceof Error ? err.message : $_('settings.home.error_load');
    }
  }

  async function persistSections(next: HomeSectionPreference[]): Promise<void> {
    const previous = sections;
    sections = next;
    busy = true;
    error = '';
    try {
      preferences = await updateUserPreferences({ home_sections: next });
      sections = mergeHomeSections(preferences.home_sections);
    } catch (err) {
      sections = previous;
      error = err instanceof Error ? err.message : $_('settings.home.error_save');
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
  <title>{$_('settings.home.title')} - {$_('app.name')}</title>
</svelte:head>

<main class="home-settings screen-stack">
  <ScreenHeader title={$_('settings.home.title')} subtitle={$_('settings.home.subtitle')} compact>
    <Button slot="actions" href="/settings" variant="ghost" size="sm">
      {$_('settings.home.back_settings')}
    </Button>
  </ScreenHeader>

  <Panel variant="bordered">
    <div class="home-settings__intro">
      <h2>{$_('settings.home.heading')}</h2>
      <p>{$_('settings.home.body')}</p>
    </div>
    <HomeSectionsEditor
      {sections}
      disabled={busy}
      on:change={({ detail }) => void persistSections(detail)}
    />
  </Panel>

  {#if error}
    <InlineAlert variant="error" message={error} />
  {/if}
</main>

<style>
  .home-settings {
    width: min(100%, 44rem);
    margin: 0 auto;
  }

  .home-settings__intro h2,
  .home-settings__intro p {
    margin: 0;
  }

  .home-settings__intro {
    display: grid;
    gap: var(--space-2);
    margin-bottom: var(--space-4);
  }

  .home-settings__intro h2 {
    font-size: var(--text-base);
  }

  .home-settings__intro p {
    color: var(--color-text-muted);
    font-size: var(--text-sm);
    line-height: 1.5;
  }
</style>
