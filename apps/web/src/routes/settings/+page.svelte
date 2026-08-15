<script lang="ts">
  import { onMount } from 'svelte';
  import { _ } from 'svelte-i18n';
  import { auth, currentUser } from '$lib/stores/auth';
  import { devMode } from '$lib/stores/devMode';
  import Button from '$lib/components/common/Button.svelte';
  import CorrelCoreLogo from '$lib/components/common/CorrelCoreLogo.svelte';
  import { BRAND_MARK_SM } from '$lib/constants/iconSizes';
  import Panel from '$lib/components/common/Panel.svelte';
  import ScreenHeader from '$lib/components/common/ScreenHeader.svelte';
  import { ApiError } from '$lib/api/client';
  import { fetchDevInfo } from '$lib/api/dev';
  import { registerPageRefresh } from '$lib/stores/pageRefresh';

  // Category index — the four user-facing groups (#694). Each links to a real
  // sub-route; the panels themselves live on those pages.
  const categories = [
    { href: '/settings/data', key: 'data', testId: 'settings-cat-data' },
    { href: '/settings/analysis', key: 'analysis', testId: 'settings-cat-analysis' },
    { href: '/settings/privacy', key: 'privacy', testId: 'settings-cat-privacy' },
    { href: '/settings/appearance', key: 'appearance', testId: 'settings-cat-appearance' },
  ] as const;

  // ---------------------------------------------------------------------------
  // Dev view availability (backend flag)
  // ---------------------------------------------------------------------------
  type DevBackendState = 'unknown' | 'available' | 'disabled' | 'error';
  let devBackendState: DevBackendState = 'unknown';
  $: devAvailable = devBackendState === 'available';

  async function checkDevView(): Promise<void> {
    if ($auth.status !== 'authenticated') return;
    try {
      await fetchDevInfo();
      devBackendState = 'available';
    } catch (err) {
      const status =
        err instanceof ApiError
          ? err.status
          : typeof err === 'object' && err !== null && 'status' in err
            ? Number((err as { status?: unknown }).status)
            : undefined;
      if (status === 404) {
        devBackendState = 'disabled';
        return;
      }
      devBackendState = 'error';
    }
  }

  // ---------------------------------------------------------------------------
  // 7× tap on version string (ADR-0019)
  // ---------------------------------------------------------------------------
  const REQUIRED_TAPS = 7;
  const TAP_TIMEOUT_MS = 3000;

  let tapCount = 0;
  let tapTimer: ReturnType<typeof setTimeout> | null = null;
  let toastMessage = '';
  let toastVisible = false;
  let toastTimer: ReturnType<typeof setTimeout> | null = null;

  function showToast(msg: string) {
    toastMessage = msg;
    toastVisible = true;
    if (toastTimer) clearTimeout(toastTimer);
    toastTimer = setTimeout(() => {
      toastVisible = false;
    }, 2500);
  }

  function handleVersionTap() {
    tapCount++;
    if (tapTimer) clearTimeout(tapTimer);

    if (tapCount >= REQUIRED_TAPS) {
      tapCount = 0;
      devMode.toggle();
      showToast(
        $devMode ? $_('settings.developer.toast_enabled') : $_('settings.developer.toast_disabled')
      );
      return;
    }

    tapTimer = setTimeout(() => {
      tapCount = 0;
    }, TAP_TIMEOUT_MS);
  }

  onMount(() => {
    void checkDevView();
    return registerPageRefresh(async () => {
      await checkDevView();
    });
  });
</script>

<svelte:head>
  <title>{$_('settings.title')} - {$_('app.name')}</title>
</svelte:head>

<main class="settings screen-stack">
  <ScreenHeader title={$_('settings.title')} subtitle={$_('settings.subtitle')} />

  {#if $auth.status !== 'authenticated'}
    <Panel variant="bordered">
      <p>{$_('settings.auth_required')}</p>
      <Button href="/auth/login" variant="primary" size="sm">{$_('auth.login.submit')}</Button>
    </Panel>
  {:else}
    <div class="settings__index">
      {#each categories as cat}
        <a class="settings__cat" href={cat.href} data-testid={cat.testId}>
          <strong>{$_(`settings.groups.${cat.key}.title`)}</strong>
          <span>{$_(`settings.groups.${cat.key}.summary`)}</span>
        </a>
      {/each}
    </div>

    <!-- ADMIN entry: gated, deliberately outside the general category list (#677/#694) -->
    {#if $currentUser?.is_admin}
      <Panel variant="bordered" data-testid="settings-section-admin">
        <div class="settings__gated-head">
          <span class="settings__section-kicker">{$_('settings.section.admin')}</span>
          <h2>{$_('settings.admin.heading')}</h2>
          <p>{$_('settings.admin.body')}</p>
        </div>
        <div class="settings__actions">
          <Button href="/admin" variant="secondary" data-testid="settings-admin-link">
            {$_('settings.admin.open')}
          </Button>
        </div>
      </Panel>
    {/if}

    <!-- DEVELOPER entry: slim, gated (7×-tap client dev mode or backend DEV_VIEW_ENABLED).
         All dev tools/fixtures now live on /dev (#695). -->
    {#if $devMode || devAvailable}
      <section class="settings__panel settings__panel--developer" data-testid="developer-section">
        <div class="settings__gated-head">
          <span class="settings__section-kicker">{$_('settings.section.developer')}</span>
          <h2>{$_('settings.developer.heading')}</h2>
          <p>{$_('settings.developer.entry_body')}</p>
        </div>
        {#if $devMode && !devAvailable && devBackendState === 'disabled'}
          <p class="settings__dev-hint" data-testid="developer-backend-unavailable-hint">
            {$_('settings.developer.backend_unavailable_hint')}
          </p>
        {:else if $devMode && !devAvailable && devBackendState === 'error'}
          <p class="settings__dev-hint" data-testid="developer-backend-error-hint">
            {$_('settings.developer.backend_error_hint')}
          </p>
        {/if}
        <div class="settings__actions">
          <Button href="/dev" variant="secondary" data-testid="dev-link">
            {$_('settings.dev.open')}
          </Button>
        </div>
      </section>
    {/if}
  {/if}

  <!-- Version string + brand mark: 7× tap activates dev mode (ADR-0019) -->
  <footer class="settings__footer">
    <!-- svelte-ignore a11y-no-noninteractive-element-interactions -->
    <!-- svelte-ignore a11y-click-events-have-key-events -->
    <p
      class="settings__version"
      role="contentinfo"
      data-testid="version-string"
      on:click={handleVersionTap}
    >
      <CorrelCoreLogo size={BRAND_MARK_SM} title="" />
      <span>{$_('app.name')} v{$_('app.version')}</span>
    </p>
  </footer>
</main>

<!-- Toast notification -->
{#if toastVisible}
  <div class="settings__toast" role="status" aria-live="polite" data-testid="dev-toast">
    {toastMessage}
  </div>
{/if}

<style>
  .settings {
    width: min(100%, 46rem);
    margin: 0 auto;
  }

  .settings__index {
    display: grid;
    gap: var(--space-3);
    grid-template-columns: repeat(auto-fit, minmax(13rem, 1fr));
  }

  .settings__cat {
    display: flex;
    flex-direction: column;
    gap: var(--space-1);
    min-height: 6rem;
    padding: var(--space-4);
    border: 1px solid var(--color-border-chart);
    border-radius: var(--radius-md);
    background: var(--color-surface-chart-bg);
    color: inherit;
    text-decoration: none;
    transition:
      border-color var(--transition-fast),
      background-color var(--transition-fast);
  }

  .settings__cat:hover {
    border-color: color-mix(in srgb, var(--color-primary) 35%, var(--color-border));
    background: color-mix(in srgb, var(--color-primary-soft) 28%, var(--color-surface));
  }

  .settings__cat strong {
    font-size: var(--text-base);
  }

  .settings__cat span {
    font-size: var(--text-sm);
    color: var(--color-text-muted);
    line-height: 1.45;
  }

  .settings__gated-head h2 {
    margin: 0;
    font-size: var(--text-lg, 1.125rem);
  }

  .settings__gated-head p {
    margin: var(--space-1) 0 0;
    color: var(--color-text-muted);
    line-height: 1.5;
  }

  .settings__section-kicker {
    display: inline-block;
    margin-bottom: var(--space-1);
    font-size: var(--text-xs);
    font-weight: 700;
    color: var(--color-text-muted);
    letter-spacing: 0.06em;
    text-transform: uppercase;
  }

  .settings__panel {
    display: flex;
    flex-direction: column;
    gap: var(--screen-gap);
    padding: var(--space-4);
    border-radius: var(--radius-md);
    background: var(--color-surface-chart-bg);
    border: 1px solid var(--color-border-chart);
  }

  .settings__panel--developer {
    border-color: var(--color-primary);
  }

  .settings__actions {
    display: flex;
    flex-wrap: wrap;
    gap: 0.65rem;
  }

  .settings__dev-hint {
    margin: 0;
    color: var(--color-text-muted);
    font-size: var(--text-sm);
    line-height: 1.5;
  }

  .settings__footer {
    margin-top: var(--space-4, 1rem);
    text-align: center;
  }

  .settings__version {
    display: inline-flex;
    align-items: center;
    justify-content: center;
    gap: var(--space-2, 0.5rem);
    font-size: var(--text-xs, 0.75rem);
    color: var(--color-text-muted);
    cursor: default;
    user-select: none;
    margin: 0;
  }

  .settings__toast {
    position: fixed;
    bottom: var(--space-6, 1.5rem);
    left: 50%;
    transform: translateX(-50%);
    background: var(--color-surface-2);
    border: 1px solid var(--color-border);
    border-radius: var(--radius-md, 0.5rem);
    padding: var(--space-3, 0.75rem) var(--space-5, 1.25rem);
    font-size: var(--text-sm, 0.875rem);
    color: var(--color-text);
    box-shadow: var(--shadow-lg);
    z-index: 300;
    white-space: nowrap;
    animation: toastIn 180ms cubic-bezier(0.16, 1, 0.3, 1) both;
  }

  @keyframes toastIn {
    from {
      opacity: 0;
      transform: translateX(-50%) translateY(8px);
    }
    to {
      opacity: 1;
      transform: translateX(-50%) translateY(0);
    }
  }

  @media (prefers-reduced-motion: reduce) {
    .settings__toast {
      animation: none;
    }
  }
</style>
