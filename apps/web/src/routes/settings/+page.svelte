<script lang="ts">
  import { onMount } from 'svelte';
  import { _ } from 'svelte-i18n';
  import { auth, currentUser } from '$lib/stores/auth';
  import {
    devPhase,
    devForceVisualizations,
    devForceVisualizationsControl,
    devMode,
    type DevInsightMaturity,
  } from '$lib/stores/devMode';
  import { DEV_PHASE_PRESETS, type DevPhasePresetId } from '$lib/dev/phaseFixtures';
  import Button from '$lib/components/common/Button.svelte';
  import CorrelCoreLogo from '$lib/components/common/CorrelCoreLogo.svelte';
  import IconButton from '$lib/components/common/IconButton.svelte';
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
  const devInsightPhases: DevInsightMaturity[] = [
    'collecting',
    'early_patterns',
    'provisional',
    'robust',
  ];
  $: selectedDevPreset = DEV_PHASE_PRESETS[$devPhase.presetId];

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

  function updateDevEntryCount(value: string): void {
    const parsed = Number.parseInt(value, 10);
    devPhase.setEntryCount(Number.isFinite(parsed) ? parsed : 0);
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

    <!-- DEVELOPER entry: gated (7×-tap client dev mode or backend DEV_VIEW_ENABLED) -->
    {#if $devMode || devAvailable}
      <section class="settings__panel settings__panel--developer" data-testid="developer-section">
        <div class="settings__gated-head">
          <span class="settings__section-kicker">{$_('settings.section.developer')}</span>
          <h2>{$_('settings.developer.heading')}</h2>
          <p>{$_('settings.developer.body')}</p>
        </div>
        <label class="settings__toggle-label">
          <input
            type="checkbox"
            class="settings__toggle"
            checked={$devMode}
            aria-label={$_('settings.developer.toggle_aria')}
            data-testid="developer-toggle"
            on:change={(e) => devMode.set(e.currentTarget.checked)}
          />
          <span>{$_('settings.developer.toggle_label')}</span>
        </label>
        {#if $devMode}
          <p class="settings__dev-hint" data-testid="developer-client-active-hint">
            {$_('settings.developer.client_active_hint')}
          </p>
          <label class="settings__toggle-label">
            <input
              type="checkbox"
              class="settings__toggle"
              checked={$devForceVisualizations}
              aria-label={$_('settings.developer.force_viz_aria')}
              data-testid="force-viz-toggle"
              on:change={(e) => devForceVisualizationsControl.set(e.currentTarget.checked)}
            />
            <span>{$_('settings.developer.force_viz_label')}</span>
          </label>
          <div class="settings__dev-grid" data-testid="developer-phase-controls">
            <label class="settings__field">
              <span>{$_('settings.developer.phase_label')}</span>
              <select
                value={$devPhase.presetId}
                data-testid="developer-phase-select"
                on:change={(e) => devPhase.setPreset(e.currentTarget.value as DevPhasePresetId)}
              >
                {#each devInsightPhases as phase}
                  <option value={phase}>{$_(`settings.developer.phase.${phase}`)}</option>
                {/each}
              </select>
            </label>
          </div>
          <p class="settings__dev-summary" data-testid="developer-phase-summary">
            {$_(selectedDevPreset.coverageKey, {
              values: { count: $devPhase.entryCount },
            })}
          </p>
          <details class="settings__dev-advanced">
            <summary>{$_('settings.developer.advanced')}</summary>
            <div class="settings__dev-grid">
              <label class="settings__field">
                <span>{$_('settings.developer.entry_count_label')}</span>
                <input
                  type="number"
                  min="0"
                  max="200"
                  value={$devPhase.entryCount}
                  data-testid="developer-entry-count"
                  on:input={(e) => updateDevEntryCount(e.currentTarget.value)}
                />
              </label>
              <label class="settings__toggle-label">
                <input
                  type="checkbox"
                  class="settings__toggle"
                  checked={$devPhase.onboardingCompleted}
                  data-testid="developer-onboarding-toggle"
                  on:change={(e) => devPhase.setOnboardingCompleted(e.currentTarget.checked)}
                />
                <span>{$_('settings.developer.onboarding_completed')}</span>
              </label>
            </div>
          </details>
          <div class="settings__actions">
            <Button
              variant="secondary"
              data-testid="developer-onboarding-preview"
              on:click={() => devPhase.setOnboardingPreviewOpen(true)}
            >
              {$_('settings.developer.preview_onboarding')}
            </Button>
          </div>
        {/if}

        <div class="settings__dev-backend" data-testid="developer-backend-block">
          <h3 class="settings__dev-subheading">{$_('settings.developer.backend_heading')}</h3>
          <p class="settings__dev-hint">{$_('settings.developer.backend_body')}</p>
          {#if devAvailable}
            <div class="settings__actions">
              <Button href="/dev" variant="secondary" data-testid="dev-link">
                {$_('settings.dev.open')}
              </Button>
            </div>
          {:else if $devMode}
            {#if devBackendState === 'disabled'}
              <p class="settings__dev-hint" data-testid="developer-backend-unavailable-hint">
                {$_('settings.developer.backend_unavailable_hint')}
              </p>
            {:else if devBackendState === 'error'}
              <p class="settings__dev-hint" data-testid="developer-backend-error-hint">
                {$_('settings.developer.backend_error_hint')}
              </p>
            {/if}
            <div class="settings__actions">
              <Button href="/dev" variant="secondary" data-testid="dev-link">
                {$_('settings.dev.open')}
              </Button>
            </div>
          {/if}
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

{#if $devMode && $devPhase.onboardingPreviewOpen}
  <div
    class="settings__modal-backdrop"
    role="presentation"
    on:click={() => devPhase.setOnboardingPreviewOpen(false)}
  >
    <dialog
      open
      class="settings__modal"
      aria-modal="true"
      aria-labelledby="onboarding-preview-title"
      on:click|stopPropagation
    >
      <div class="settings__modal-head">
        <h2 id="onboarding-preview-title">{$_('settings.developer.preview_title')}</h2>
        <IconButton
          type="button"
          ariaLabel={$_('settings.developer.preview_close')}
          title={$_('settings.developer.preview_close')}
          on:click={() => devPhase.setOnboardingPreviewOpen(false)}
        >
          x
        </IconButton>
      </div>
      <iframe
        class="settings__preview-frame"
        title={$_('settings.developer.preview_title')}
        src="/onboarding?preview=1"
      ></iframe>
    </dialog>
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

  .settings__toggle-label {
    display: flex;
    align-items: center;
    gap: 0.75rem;
    cursor: pointer;
    min-height: 2.75rem;
    padding-block: 0.25rem;
    user-select: none;
  }

  .settings__toggle {
    width: 1.25rem;
    height: 1.25rem;
    min-width: 1.25rem;
    cursor: pointer;
    accent-color: var(--color-primary);
  }

  .settings__dev-backend {
    display: grid;
    gap: var(--space-2);
    padding-top: var(--space-3);
    border-top: 1px solid var(--color-border);
  }

  .settings__dev-subheading {
    margin: 0;
    font-size: var(--text-sm);
    font-weight: 700;
  }

  .settings__dev-hint {
    margin: 0;
    color: var(--color-text-muted);
    font-size: var(--text-sm);
    line-height: 1.5;
  }

  .settings__dev-grid {
    display: grid;
    grid-template-columns: repeat(auto-fit, minmax(12rem, 1fr));
    gap: var(--space-3);
  }

  .settings__field {
    display: flex;
    flex-direction: column;
    gap: var(--space-2);
    font-size: var(--text-sm);
    color: var(--color-text-muted);
  }

  .settings__field select,
  .settings__field input {
    min-height: 44px;
    border: 1px solid var(--color-border);
    border-radius: var(--radius-sm);
    padding: 0 var(--space-3);
    background: var(--color-surface);
    color: var(--color-text);
  }

  .settings__dev-summary {
    margin: 0;
    color: var(--color-text-muted);
    font-size: var(--text-sm);
    line-height: 1.5;
  }

  .settings__dev-advanced {
    display: grid;
    gap: var(--space-3);
  }

  .settings__dev-advanced summary {
    min-height: 44px;
    display: flex;
    align-items: center;
    cursor: pointer;
    color: var(--color-text-muted);
    font-size: var(--text-sm);
    font-weight: 700;
  }

  .settings__modal-backdrop {
    position: fixed;
    inset: 0;
    z-index: 500;
    display: grid;
    place-items: center;
    padding: var(--space-4);
    background: color-mix(in srgb, var(--color-surface) 62%, transparent);
  }

  .settings__modal {
    width: min(100%, 42rem);
    height: min(88dvh, 52rem);
    display: flex;
    flex-direction: column;
    overflow: hidden;
    border: 1px solid var(--color-border);
    border-radius: var(--radius-md);
    background: var(--color-surface);
    box-shadow: var(--shadow-lg);
  }

  .settings__modal-head {
    display: flex;
    align-items: center;
    justify-content: space-between;
    gap: var(--space-3);
    padding: var(--space-3);
    border-bottom: 1px solid var(--color-border);
  }

  .settings__modal-head h2 {
    margin: 0;
    font-size: var(--text-base);
  }

  .settings__preview-frame {
    flex: 1;
    width: 100%;
    border: 0;
    background: var(--color-surface);
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
