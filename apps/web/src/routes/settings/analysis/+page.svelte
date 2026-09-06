<script lang="ts">
  import { onMount } from 'svelte';
  import { _ } from 'svelte-i18n';
  import { auth } from '$lib/stores/auth';
  import Button from '$lib/components/common/Button.svelte';
  import InlineAlert from '$lib/components/common/InlineAlert.svelte';
  import Panel from '$lib/components/common/Panel.svelte';
  import ScreenHeader from '$lib/components/common/ScreenHeader.svelte';
  import SettingsCategoryBar from '$lib/components/settings/SettingsCategoryBar.svelte';
  import { ApiError } from '$lib/api/client';
  import {
    fetchUserPreferences,
    updateUserPreferences,
    type UserPreferencesResponse,
  } from '$lib/api/preferences';
  import { fetchLatestInsightDigest, regenerateInsights } from '$lib/api/insights';
  import { registerPageRefresh } from '$lib/stores/pageRefresh';

  let preferences: UserPreferencesResponse | null = null;
  let preferencesBusy = false;
  let preferencesError = '';
  let regenerateBusy = false;
  let regenerateMessage = '';
  let regenerateError = '';
  /** #819: digest enabled but no persisted snapshot yet (modal cannot fire). */
  let digestPendingHint = false;

  async function refreshDigestPendingHint(): Promise<void> {
    digestPendingHint = false;
    if (!preferences?.digest_enabled) return;
    try {
      const digest = await fetchLatestInsightDigest();
      digestPendingHint = !digest.generated_at;
    } catch {
      // 404 / other: no persisted digest yet.
      digestPendingHint = true;
    }
  }

  async function loadPreferences(): Promise<void> {
    if ($auth.status !== 'authenticated') return;
    try {
      preferences = await fetchUserPreferences();
      await refreshDigestPendingHint();
    } catch (err) {
      preferencesError = err instanceof Error ? err.message : $_('settings.analysis.error');
    }
  }

  async function toggleAnalytics(enabled: boolean): Promise<void> {
    preferencesBusy = true;
    preferencesError = '';
    try {
      preferences = await updateUserPreferences({ analytics_enabled: enabled });
    } catch (err) {
      preferencesError = err instanceof Error ? err.message : $_('settings.analysis.error');
    } finally {
      preferencesBusy = false;
    }
  }

  async function toggleDigest(enabled: boolean): Promise<void> {
    preferencesBusy = true;
    preferencesError = '';
    try {
      preferences = await updateUserPreferences({ digest_enabled: enabled });
      await refreshDigestPendingHint();
    } catch (err) {
      preferencesError = err instanceof Error ? err.message : $_('settings.analysis.error');
    } finally {
      preferencesBusy = false;
    }
  }

  async function handleRegenerateInsights(): Promise<void> {
    if (preferences?.analytics_enabled === false) return;
    regenerateBusy = true;
    regenerateMessage = '';
    regenerateError = '';
    try {
      const result = await regenerateInsights();
      regenerateMessage = $_('settings.analysis.regenerate_success', {
        values: { count: result.insight_count },
      });
      await refreshDigestPendingHint();
    } catch (err) {
      if (err instanceof ApiError && err.status === 429) {
        regenerateError = $_('settings.analysis.regenerate_rate_limited');
      } else if (err instanceof ApiError && err.status === 403) {
        regenerateError = $_('settings.analysis.regenerate_disabled');
      } else {
        regenerateError =
          err instanceof Error ? err.message : $_('settings.analysis.regenerate_error');
      }
    } finally {
      regenerateBusy = false;
    }
  }

  onMount(() => {
    void loadPreferences();
    return registerPageRefresh(async () => {
      await loadPreferences();
    });
  });
</script>

<svelte:head>
  <title>{$_('settings.groups.analysis.title')} - {$_('app.name')}</title>
</svelte:head>

<main class="analysis-settings screen-stack">
  <ScreenHeader
    title={$_('settings.groups.analysis.title')}
    subtitle={$_('settings.groups.analysis.subtitle')}
    compact
    back={{ href: '/settings', label: $_('nav.settings') }}
  />
  <SettingsCategoryBar />

  {#if $auth.status !== 'authenticated'}
    <Panel variant="bordered">
      <p>{$_('settings.auth_required')}</p>
      <Button href="/auth/login" variant="primary" size="sm">{$_('auth.login.submit')}</Button>
    </Panel>
  {:else}
    <Panel variant="bordered">
      <div class="analysis-settings__head">
        <p>{$_('settings.analysis.body')}</p>
      </div>
      <label class="analysis-settings__toggle-label">
        <input
          type="checkbox"
          class="analysis-settings__toggle"
          checked={preferences?.analytics_enabled ?? true}
          disabled={preferencesBusy}
          data-testid="analytics-toggle"
          on:change={(e) => void toggleAnalytics(e.currentTarget.checked)}
        />
        <span>{$_('settings.analysis.analytics_enabled')}</span>
      </label>
      <label class="analysis-settings__toggle-label">
        <input
          type="checkbox"
          class="analysis-settings__toggle"
          checked={preferences?.digest_enabled ?? false}
          disabled={preferencesBusy || preferences?.analytics_enabled === false}
          data-testid="digest-toggle"
          on:change={(e) => void toggleDigest(e.currentTarget.checked)}
        />
        <span>{$_('settings.analysis.digest_enabled')}</span>
      </label>
      <p class="analysis-settings__note">{$_('settings.analysis.digest_hint')}</p>
      {#if digestPendingHint}
        <p class="analysis-settings__note" data-testid="digest-pending-hint">
          {$_('settings.analysis.digest_pending_hint')}
        </p>
      {/if}
      <p class="analysis-settings__note">
        <a href="/insights/digest" data-testid="digest-preview-link">
          {$_('settings.analysis.digest_preview_link')}
        </a>
      </p>
      {#if preferencesError}
        <InlineAlert variant="error" message={preferencesError} />
      {/if}
      <div class="analysis-settings__actions">
        <Button
          variant="secondary"
          type="button"
          data-testid="regenerate-insights"
          loading={regenerateBusy}
          disabled={preferencesBusy || preferences?.analytics_enabled === false}
          on:click={() => void handleRegenerateInsights()}
        >
          {$_('settings.analysis.regenerate_insights')}
        </Button>
      </div>
      <p class="analysis-settings__note">{$_('settings.analysis.regenerate_hint')}</p>
      {#if regenerateMessage}
        <InlineAlert variant="success" message={regenerateMessage} />
      {/if}
      {#if regenerateError}
        <InlineAlert variant="error" message={regenerateError} />
      {/if}
    </Panel>
  {/if}
</main>

<style>
  .analysis-settings {
    width: min(100%, 46rem);
    margin: 0 auto;
  }

  .analysis-settings__head p {
    margin: 0;
    color: var(--color-text-muted);
    line-height: 1.5;
  }

  .analysis-settings__toggle-label {
    display: flex;
    align-items: center;
    gap: 0.75rem;
    cursor: pointer;
    min-height: 2.75rem;
    padding-block: 0.25rem;
    user-select: none;
  }

  .analysis-settings__toggle {
    width: 1.25rem;
    height: 1.25rem;
    min-width: 1.25rem;
    cursor: pointer;
    accent-color: var(--color-primary);
  }

  .analysis-settings__note {
    margin: var(--space-2) 0 0;
    color: var(--color-text-muted);
    font-size: var(--text-sm);
    line-height: 1.5;
  }

  .analysis-settings__actions {
    display: flex;
    flex-wrap: wrap;
    gap: 0.65rem;
    margin-top: var(--space-3);
  }
</style>
