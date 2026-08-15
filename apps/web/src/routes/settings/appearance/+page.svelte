<script lang="ts">
  import { _, locale } from 'svelte-i18n';
  import { auth } from '$lib/stores/auth';
  import Button from '$lib/components/common/Button.svelte';
  import Panel from '$lib/components/common/Panel.svelte';
  import ScreenHeader from '$lib/components/common/ScreenHeader.svelte';
  import SegmentedControl, {
    type SegmentedControlOption,
  } from '$lib/components/common/SegmentedControl.svelte';
  import ThemeToggle from '$lib/components/common/ThemeToggle.svelte';
  import { setAppLocale, type AppLocale } from '$lib/i18n';

  const localeOptions: SegmentedControlOption[] = [
    { id: 'de', label: 'DE', testId: 'language-de' },
    { id: 'en', label: 'EN', testId: 'language-en' },
  ];

  function selectLocale(nextLocale: AppLocale): void {
    setAppLocale(nextLocale);
  }
</script>

<svelte:head>
  <title>{$_('settings.groups.appearance.title')} - {$_('app.name')}</title>
</svelte:head>

<main class="appearance-settings screen-stack">
  <ScreenHeader
    title={$_('settings.groups.appearance.title')}
    subtitle={$_('settings.groups.appearance.subtitle')}
    compact
  >
    <Button slot="actions" href="/settings" variant="ghost" size="sm">
      {$_('settings.back')}
    </Button>
  </ScreenHeader>

  {#if $auth.status !== 'authenticated'}
    <Panel variant="bordered">
      <p>{$_('settings.auth_required')}</p>
      <Button href="/auth/login" variant="primary" size="sm">{$_('auth.login.submit')}</Button>
    </Panel>
  {:else}
    <Panel variant="bordered">
      <div class="appearance-settings__head">
        <h2>{$_('settings.appearance.heading')}</h2>
        <p>{$_('settings.appearance.body')}</p>
      </div>
      <div class="appearance-settings__row">
        <span>{$_('settings.appearance.theme')}</span>
        <ThemeToggle testId="settings-theme-toggle-panel" />
      </div>
      <SegmentedControl
        value={$locale ?? 'de'}
        options={localeOptions}
        ariaLabel={$_('settings.appearance.language')}
        testId="settings-language-control"
        equalWidth={false}
        on:change={(event) => selectLocale(event.detail.value as AppLocale)}
      />
      <div class="appearance-settings__actions">
        <Button href="/settings/home" variant="secondary" data-testid="settings-home-layout">
          {$_('settings.home.open')}
        </Button>
        <Button href="/settings/app" variant="secondary" data-testid="settings-app-open">
          {$_('settings.app.open')}
        </Button>
      </div>
    </Panel>
  {/if}
</main>

<style>
  .appearance-settings {
    width: min(100%, 46rem);
    margin: 0 auto;
  }

  .appearance-settings__head h2 {
    margin: 0;
    font-size: var(--text-lg, 1.125rem);
  }

  .appearance-settings__head p {
    margin: var(--space-1) 0 0;
    color: var(--color-text-muted);
    line-height: 1.5;
  }

  .appearance-settings__row {
    display: flex;
    align-items: center;
    justify-content: space-between;
    gap: var(--space-3);
    margin-top: var(--space-3);
  }

  .appearance-settings__actions {
    display: flex;
    flex-wrap: wrap;
    gap: 0.65rem;
    margin-top: var(--space-3);
  }
</style>
