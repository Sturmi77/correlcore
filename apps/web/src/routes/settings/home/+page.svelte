<script lang="ts">
  import { onMount } from 'svelte';
  import { _ } from 'svelte-i18n';
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
  import { createLatestWinsGate } from '$lib/utils/latestWinsPersist';
  import { registerPageRefresh } from '$lib/stores/pageRefresh';

  let preferences: UserPreferencesResponse | null = null;
  let sections: HomeSectionPreference[] = DEFAULT_HOME_SECTIONS.map((section) => ({ ...section }));
  let loading = true;
  let busy = false;
  let error = '';
  /** Serialize PATCHes so a slower earlier reorder cannot overwrite a later one. */
  const persistGate = createLatestWinsGate();
  let confirmedSections: HomeSectionPreference[] = sections;

  async function loadPreferences(): Promise<void> {
    loading = true;
    try {
      preferences = await fetchUserPreferences();
      sections = mergeHomeSections(preferences.home_sections);
      confirmedSections = sections;
    } catch (err) {
      error = err instanceof Error ? err.message : $_('settings.home.error_load');
    } finally {
      loading = false;
    }
  }

  async function persistSections(next: HomeSectionPreference[]): Promise<void> {
    const seq = persistGate.begin();
    sections = next;
    busy = true;
    error = '';
    await persistGate.enqueue(async () => {
      if (!persistGate.isCurrent(seq)) return;
      try {
        const toSend = sections;
        const saved = await updateUserPreferences({ home_sections: toSend });
        confirmedSections = mergeHomeSections(saved.home_sections);
        if (!persistGate.isCurrent(seq)) return;
        preferences = saved;
        sections = confirmedSections;
      } catch (err) {
        if (!persistGate.isCurrent(seq)) return;
        sections = confirmedSections;
        error = err instanceof Error ? err.message : $_('settings.home.error_save');
      } finally {
        if (persistGate.isCurrent(seq)) busy = false;
      }
    });
  }

  async function persistDayTrend(enabled: boolean): Promise<void> {
    const previous = preferences;
    if (preferences) {
      preferences = { ...preferences, home_weekday_day_trend_enabled: enabled };
    }
    busy = true;
    error = '';
    try {
      preferences = await updateUserPreferences({ home_weekday_day_trend_enabled: enabled });
      sections = mergeHomeSections(preferences.home_sections);
    } catch (err) {
      preferences = previous;
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

<main class="home-settings screen-stack" aria-busy={busy}>
  <ScreenHeader
    title={$_('settings.home.title')}
    subtitle={$_('settings.home.subtitle')}
    compact
    back={{ href: '/settings', label: $_('nav.settings') }}
  />

  <Panel variant="bordered">
    <div class="home-settings__intro">
      <h2>{$_('settings.home.heading')}</h2>
      <p>{$_('settings.home.body')}</p>
    </div>
    <HomeSectionsEditor
      {sections}
      disabled={loading}
      on:change={({ detail }) => void persistSections(detail)}
    />
  </Panel>

  <Panel variant="bordered">
    <div class="home-settings__intro">
      <h2>{$_('settings.home.day_trend_enabled')}</h2>
      <p>{$_('settings.home.day_trend_hint')}</p>
    </div>
    <label class="home-settings__toggle-label">
      <input
        type="checkbox"
        class="home-settings__toggle"
        checked={preferences?.home_weekday_day_trend_enabled !== false}
        disabled={busy || loading}
        data-testid="weekday-day-trend-toggle"
        on:change={(e) => void persistDayTrend(e.currentTarget.checked)}
      />
      <span>{$_('settings.home.day_trend_enabled')}</span>
    </label>
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

  .home-settings__toggle-label {
    display: flex;
    align-items: center;
    gap: 0.75rem;
    cursor: pointer;
    min-height: 2.75rem;
    padding-block: 0.25rem;
    user-select: none;
  }

  .home-settings__toggle {
    width: 1.25rem;
    height: 1.25rem;
    min-width: 1.25rem;
    cursor: pointer;
    accent-color: var(--color-primary);
  }
</style>
