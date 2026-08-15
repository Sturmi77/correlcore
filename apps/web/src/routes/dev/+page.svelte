<script lang="ts">
  import { goto } from '$app/navigation';
  import { onDestroy, onMount } from 'svelte';
  import { get } from 'svelte/store';
  import { _ } from 'svelte-i18n';
  import IconRender from '$lib/components/common/IconRender.svelte';
  import IconButton from '$lib/components/common/IconButton.svelte';
  import TabBar, { type TabBarOption } from '$lib/components/common/TabBar.svelte';
  import ThemeToggle from '$lib/components/common/ThemeToggle.svelte';
  import { ApiError } from '$lib/api/client';
  import {
    createDevDbBackup,
    fetchDevDbBackups,
    fetchDevInfo,
    fetchWorkerRuns,
    fetchWorkerRunsLatest,
    restoreDevDbBackup,
    runDevInsightsOnce,
    type DevDbBackupItem,
    type DevInfoResponse,
    type WorkerRunResponse,
    type WorkerRunsLatestResponse,
  } from '$lib/api/dev';
  import { ICON_SIZE_MD } from '$lib/constants/iconSizes';
  import { regenerateInsights } from '$lib/api/insights';
  import {
    devPhase,
    devForceVisualizations,
    devForceVisualizationsControl,
    devMode,
    type DevInsightMaturity,
  } from '$lib/stores/devMode';
  import { DEV_PHASE_PRESETS, type DevPhasePresetId } from '$lib/dev/phaseFixtures';

  const COMMIT_BASE_URL = 'https://github.com/sturmi77/correlcore/commit/';
  const REFRESH_MS = 30_000;

  type DevTab = 'version' | 'runtime' | 'workers' | 'db' | 'devviz';
  let activeTab: DevTab = 'version';
  $: tabOptions = [
    { id: 'version', label: $_('dev.tabs.version'), testId: 'dev-tab-version' },
    { id: 'runtime', label: $_('dev.tabs.runtime'), testId: 'dev-tab-runtime' },
    { id: 'workers', label: $_('dev.tabs.workers'), testId: 'dev-tab-workers' },
    { id: 'db', label: $_('dev.tabs.db'), testId: 'dev-tab-db' },
    { id: 'devviz', label: $_('dev.tabs.devviz'), testId: 'dev-tab-devviz' },
  ] satisfies TabBarOption[];

  let info: DevInfoResponse | null = null;
  let latest: WorkerRunsLatestResponse | null = null;
  let runs: WorkerRunResponse[] = [];
  let backups: DevDbBackupItem[] = [];
  let backupDir = '';
  let backupsAvailable = false;
  let loading = true;
  let error = '';
  let backendUnavailable = false;
  let actionBusy = '';
  let actionMessage = '';
  let actionError = '';
  let copied: 'commit' | 'digest' | null = null;
  let controller: AbortController | null = null;
  let interval: ReturnType<typeof setInterval> | null = null;
  let copyTimer: ReturnType<typeof setTimeout> | null = null;
  let activeCommitUrl: string | null = null;

  $: activeCommitUrl = info ? commitUrl(info.git_commit) : null;

  // Dev-Visualization (client-only fixtures) — moved here from Settings (#695).
  const devInsightPhases: DevInsightMaturity[] = [
    'collecting',
    'early_patterns',
    'provisional',
    'robust',
  ];
  $: selectedDevPreset = DEV_PHASE_PRESETS[$devPhase.presetId];

  function updateDevEntryCount(value: string): void {
    const parsed = Number.parseInt(value, 10);
    devPhase.setEntryCount(Number.isFinite(parsed) ? parsed : 0);
  }

  function shortCommit(commit: string): string {
    if (!commit || commit === 'unknown') return commit || 'unknown';
    return commit.slice(0, 12);
  }

  function commitUrl(commit: string): string | null {
    if (!commit || commit === 'unknown') return null;
    return `${COMMIT_BASE_URL}${commit}`;
  }

  function formatUptime(seconds: number): string {
    const days = Math.floor(seconds / 86_400);
    const hours = Math.floor((seconds % 86_400) / 3_600);
    const minutes = Math.floor((seconds % 3_600) / 60);
    if (days > 0) return `${days}d ${hours}h`;
    if (hours > 0) return `${hours}h ${minutes}m`;
    return `${minutes}m`;
  }

  function formatWhen(iso: string | null | undefined): string {
    if (!iso) return '—';
    try {
      return new Date(iso).toLocaleString();
    } catch {
      return iso;
    }
  }

  function formatBytes(size: number): string {
    if (size < 1024) return `${size} B`;
    if (size < 1024 * 1024) return `${(size / 1024).toFixed(1)} KB`;
    return `${(size / (1024 * 1024)).toFixed(1)} MB`;
  }

  function resultPreview(run: WorkerRunResponse | null | undefined): string {
    if (!run) return '—';
    const r = run.result ?? {};
    const parts: string[] = [];
    if (typeof r.insight_count === 'number') parts.push(`insights=${r.insight_count}`);
    if (typeof r.generated_insights === 'number') parts.push(`generated=${r.generated_insights}`);
    if (typeof r.processed_users === 'number') parts.push(`users=${r.processed_users}`);
    if (typeof r.failed_users === 'number' && r.failed_users > 0) {
      parts.push(`failed=${r.failed_users}`);
    }
    if (typeof r.tag_clusters_status === 'string') parts.push(`clusters=${r.tag_clusters_status}`);
    if (typeof r.deleted_unverified_accounts === 'number') {
      parts.push(`cleanup_accounts=${r.deleted_unverified_accounts}`);
    }
    if (parts.length === 0) return JSON.stringify(r);
    return parts.join(' · ');
  }

  async function load(): Promise<void> {
    controller?.abort();
    controller = new AbortController();
    loading = !info;
    error = '';
    backendUnavailable = false;
    try {
      info = await fetchDevInfo(controller.signal);
      const [latestResp, runsResp] = await Promise.all([
        fetchWorkerRunsLatest(controller.signal),
        fetchWorkerRuns({ limit: 20, signal: controller.signal }),
      ]);
      latest = latestResp;
      runs = runsResp.items;
      try {
        const backupResp = await fetchDevDbBackups(controller.signal);
        backups = backupResp.items;
        backupDir = backupResp.backup_dir;
        backupsAvailable = true;
      } catch (backupErr) {
        if (backupErr instanceof ApiError && backupErr.status === 404) {
          backupsAvailable = false;
        } else if (!(backupErr instanceof Error && backupErr.name === 'AbortError')) {
          backupsAvailable = false;
        }
      }
    } catch (err) {
      if ((err as Error).name === 'AbortError') return;
      if (err instanceof ApiError && err.status === 404) {
        // Soft-fail when Settings Developer Mode is unlocked: the client-only
        // Dev-Visualization tab still works without a backend.
        if (!get(devMode)) {
          await goto('/');
          return;
        }
        backendUnavailable = true;
        return;
      }
      if (err instanceof ApiError && err.status === 401) {
        await goto('/auth/login?next=/dev');
        return;
      }
      error = err instanceof Error ? err.message : $_('dev.error_load');
    } finally {
      loading = false;
    }
  }

  async function copyValue(kind: 'commit' | 'digest', value: string | null): Promise<void> {
    if (!value) return;
    await navigator.clipboard.writeText(value);
    copied = kind;
    if (copyTimer) clearTimeout(copyTimer);
    copyTimer = setTimeout(() => {
      copied = null;
    }, 1800);
  }

  async function withAction(key: string, fn: () => Promise<void>): Promise<void> {
    actionBusy = key;
    actionMessage = '';
    actionError = '';
    try {
      await fn();
      await load();
    } catch (err) {
      actionError = err instanceof Error ? err.message : $_('dev.action_failed');
    } finally {
      actionBusy = '';
    }
  }

  onMount(() => {
    void load();
    interval = setInterval(() => void load(), REFRESH_MS);
  });

  onDestroy(() => {
    if (interval) clearInterval(interval);
    if (copyTimer) clearTimeout(copyTimer);
    controller?.abort();
  });
</script>

<svelte:head>
  <title>{$_('dev.title')} - CorrelCore</title>
</svelte:head>

<main class="dev">
  <header class="dev__top">
    <a class="btn btn-sm variant-ghost-surface" href="/settings">{$_('nav.settings')}</a>
    <ThemeToggle testId="dev-theme-toggle" />
  </header>

  <section class="dev__intro">
    <p class="dev__eyebrow">{$_('dev.eyebrow')}</p>
    <h1>{$_('dev.title')}</h1>
    <p>{$_('dev.subtitle')}</p>
  </section>

  <TabBar
    value={activeTab}
    options={tabOptions}
    ariaLabel={$_('dev.tabs.aria')}
    testId="dev-tabs"
    on:change={(e) => (activeTab = e.detail.value as DevTab)}
  />

  {#if activeTab === 'devviz'}
    <!-- Client-only fixtures — always available (no backend needed). -->
    <section class="dev__panel dev__panel--developer" data-testid="developer-viz">
      <div class="dev__panel-head">
        <h2>{$_('settings.developer.heading')}</h2>
      </div>
      <p class="dev__muted">{$_('settings.developer.body')}</p>
      <label class="dev__toggle-label">
        <input
          type="checkbox"
          class="dev__toggle"
          checked={$devMode}
          aria-label={$_('settings.developer.toggle_aria')}
          data-testid="developer-toggle"
          on:change={(e) => devMode.set(e.currentTarget.checked)}
        />
        <span>{$_('settings.developer.toggle_label')}</span>
      </label>
      {#if $devMode}
        <p class="dev__muted" data-testid="developer-client-active-hint">
          {$_('settings.developer.client_active_hint')}
        </p>
        <label class="dev__toggle-label">
          <input
            type="checkbox"
            class="dev__toggle"
            checked={$devForceVisualizations}
            aria-label={$_('settings.developer.force_viz_aria')}
            data-testid="force-viz-toggle"
            on:change={(e) => devForceVisualizationsControl.set(e.currentTarget.checked)}
          />
          <span>{$_('settings.developer.force_viz_label')}</span>
        </label>
        <div class="dev__field-grid" data-testid="developer-phase-controls">
          <label class="dev__field">
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
        <p class="dev__muted" data-testid="developer-phase-summary">
          {$_(selectedDevPreset.coverageKey, { values: { count: $devPhase.entryCount } })}
        </p>
        <details class="dev__advanced">
          <summary>{$_('settings.developer.advanced')}</summary>
          <div class="dev__field-grid">
            <label class="dev__field">
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
            <label class="dev__toggle-label">
              <input
                type="checkbox"
                class="dev__toggle"
                checked={$devPhase.onboardingCompleted}
                data-testid="developer-onboarding-toggle"
                on:change={(e) => devPhase.setOnboardingCompleted(e.currentTarget.checked)}
              />
              <span>{$_('settings.developer.onboarding_completed')}</span>
            </label>
          </div>
        </details>
        <div class="dev__actions">
          <button
            class="btn btn-sm variant-ghost-surface"
            type="button"
            data-testid="developer-onboarding-preview"
            on:click={() => devPhase.setOnboardingPreviewOpen(true)}
          >
            {$_('settings.developer.preview_onboarding')}
          </button>
        </div>
      {/if}
    </section>
  {:else if backendUnavailable}
    <section class="dev__panel dev__panel--notice" role="status" data-testid="dev-backend-notice">
      <p>
        <strong>{$_('dev.backend_unavailable_title')}</strong><br />
        {$_('dev.backend_unavailable_body')}
      </p>
    </section>
  {:else if loading && !info}
    <section class="dev__panel">
      <p class="dev__muted">{$_('dev.loading')}</p>
    </section>
  {:else if error}
    <section class="dev__panel dev__panel--error" role="alert">
      <p>{error}</p>
      <button class="btn btn-sm variant-ghost-surface" type="button" on:click={() => void load()}>
        {$_('dev.retry')}
      </button>
    </section>
  {:else if info}
    {#if activeTab === 'version'}
      <section class="dev__hero" aria-label={$_('dev.version_identity')}>
        <div class="dev__identity">
          <span class="dev__label">{$_('dev.github_commit')}</span>
          {#if activeCommitUrl}
            <a class="dev__commit" href={activeCommitUrl} target="_blank" rel="noreferrer">
              {shortCommit(info.git_commit)}
              <IconRender icon="external-link" size={ICON_SIZE_MD} />
            </a>
          {:else}
            <span class="dev__commit">{shortCommit(info.git_commit)}</span>
          {/if}
          <span class="dev__subtle">{info.git_branch}</span>
        </div>
        <button
          class="dev__icon-btn"
          type="button"
          aria-label={$_('dev.copy_commit')}
          title={$_('dev.copy_commit')}
          disabled={info.git_commit === 'unknown'}
          on:click={() => copyValue('commit', info?.git_commit ?? null)}
        >
          <IconRender icon="copy" size={ICON_SIZE_MD} />
        </button>
      </section>

      <article class="dev__panel">
        <div class="dev__panel-head">
          <h2>{$_('dev.container_image')}</h2>
          <button
            class="dev__icon-btn"
            type="button"
            aria-label={$_('dev.refresh')}
            title={$_('dev.refresh')}
            on:click={() => void load()}
          >
            <IconRender icon="refresh-cw" size={ICON_SIZE_MD} />
          </button>
        </div>
        <dl class="dev__facts">
          <div>
            <dt>{$_('dev.image_tag')}</dt>
            <dd>{info.image_tag}</dd>
          </div>
          <div>
            <dt>{$_('dev.image_digest')}</dt>
            <dd class:dev__missing={!info.image_digest}>
              {info.image_digest ?? $_('dev.digest_missing')}
              {#if info.image_digest}
                <button
                  class="dev__copy-inline"
                  type="button"
                  on:click={() => copyValue('digest', info?.image_digest ?? null)}
                >
                  {copied === 'digest' ? $_('dev.copied') : $_('dev.copy')}
                </button>
              {/if}
            </dd>
          </div>
          <div>
            <dt>{$_('dev.image_hash')}</dt>
            <dd>{info.image_hash}</dd>
          </div>
          <div>
            <dt>{$_('dev.build_time')}</dt>
            <dd>{info.build_time ?? $_('dev.not_provided')}</dd>
          </div>
        </dl>
      </article>
    {/if}

    {#if activeTab === 'runtime'}
      <section class="dev__grid">
        <article class="dev__panel">
          <h2>{$_('dev.runtime')}</h2>
          <dl class="dev__facts">
            <div>
              <dt>Python</dt>
              <dd>{info.python_version}</dd>
            </div>
            <div>
              <dt>FastAPI</dt>
              <dd>{info.fastapi_version}</dd>
            </div>
            <div>
              <dt>{$_('dev.db_migration')}</dt>
              <dd>{info.db_migration_head ?? $_('dev.unavailable')}</dd>
            </div>
            <div>
              <dt>{$_('dev.uptime')}</dt>
              <dd>{formatUptime(info.uptime_seconds)}</dd>
            </div>
          </dl>
        </article>

        <article class="dev__panel">
          <h2>{$_('dev.infrastructure')}</h2>
          <div class="dev__status-list">
            <span class:dev__ok={info.health_ready} class:dev__down={!info.health_ready}>
              {$_('dev.health')}
              {info.health_ready ? $_('dev.ready') : $_('dev.not_ready')}
            </span>
            <span class:dev__ok={info.redis_connected} class:dev__down={!info.redis_connected}>
              Redis {info.redis_connected ? $_('dev.connected') : $_('dev.down')}
            </span>
            <span class:dev__ok={info.minio_connected} class:dev__down={!info.minio_connected}>
              MinIO {info.minio_connected ? $_('dev.connected') : $_('dev.down')}
            </span>
          </div>
          <dl class="dev__facts dev__facts--compact">
            <div>
              <dt>{$_('dev.db_pool_size')}</dt>
              <dd>{info.db_pool_size ?? $_('dev.na')}</dd>
            </div>
            <div>
              <dt>{$_('dev.db_checked_out')}</dt>
              <dd>{info.db_checked_out ?? $_('dev.na')}</dd>
            </div>
          </dl>
        </article>
      </section>
    {/if}

    {#if activeTab === 'workers'}
      <section class="dev__panel" aria-label={$_('dev.workers.title')}>
        <div class="dev__panel-head">
          <h2>{$_('dev.workers.title')}</h2>
          <div class="dev__actions">
            <button
              class="btn btn-sm variant-ghost-surface"
              type="button"
              disabled={!!actionBusy}
              on:click={() =>
                void withAction('regenerate', async () => {
                  const result = await regenerateInsights();
                  actionMessage = $_('dev.workers.regenerate_done', {
                    values: { count: result.insight_count },
                  });
                })}
            >
              {actionBusy === 'regenerate'
                ? $_('dev.workers.busy')
                : $_('dev.workers.regenerate_me')}
            </button>
            <button
              class="btn btn-sm variant-filled-primary"
              type="button"
              disabled={!!actionBusy}
              on:click={() =>
                void withAction('fleet', async () => {
                  const result = await runDevInsightsOnce();
                  actionMessage = $_('dev.workers.fleet_done', {
                    values: { count: result.generated_insights },
                  });
                })}
            >
              {actionBusy === 'fleet' ? $_('dev.workers.busy') : $_('dev.workers.run_fleet')}
            </button>
          </div>
        </div>
        <p class="dev__muted">{$_('dev.workers.subtitle')}</p>
        <div class="dev__grid dev__grid--cards">
          {#each [{ key: 'daily_bundle', run: latest?.daily_bundle }, { key: 'fleet_insights', run: latest?.fleet_insights }, { key: 'user_insights', run: latest?.user_insights }] as card}
            <article class="dev__card">
              <h3>{$_(`dev.workers.card_${card.key}`)}</h3>
              {#if card.run}
                <dl class="dev__facts">
                  <div>
                    <dt>{$_('dev.workers.status')}</dt>
                    <dd>{card.run.status}</dd>
                  </div>
                  <div>
                    <dt>{$_('dev.workers.trigger')}</dt>
                    <dd>{card.run.trigger_source}</dd>
                  </div>
                  <div>
                    <dt>{$_('dev.workers.finished')}</dt>
                    <dd>{formatWhen(card.run.finished_at ?? card.run.started_at)}</dd>
                  </div>
                  <div>
                    <dt>{$_('dev.workers.result')}</dt>
                    <dd>{resultPreview(card.run)}</dd>
                  </div>
                </dl>
              {:else}
                <p class="dev__muted">{$_('dev.workers.none')}</p>
              {/if}
            </article>
          {/each}
        </div>

        <h3 class="dev__subheading">{$_('dev.workers.history')}</h3>
        {#if runs.length === 0}
          <p class="dev__muted">{$_('dev.workers.none')}</p>
        {:else}
          <div class="dev__table-wrap">
            <table class="dev__table">
              <thead>
                <tr>
                  <th>{$_('dev.workers.when')}</th>
                  <th>{$_('dev.workers.kind')}</th>
                  <th>{$_('dev.workers.trigger')}</th>
                  <th>{$_('dev.workers.status')}</th>
                  <th>{$_('dev.workers.result')}</th>
                </tr>
              </thead>
              <tbody>
                {#each runs as run}
                  <tr>
                    <td>{formatWhen(run.finished_at ?? run.started_at)}</td>
                    <td>{run.job_kind}</td>
                    <td>{run.trigger_source}</td>
                    <td>{run.status}</td>
                    <td>
                      {resultPreview(run)}
                      {#if run.error_message}
                        <span class="dev__error-inline">{run.error_message}</span>
                      {/if}
                    </td>
                  </tr>
                {/each}
              </tbody>
            </table>
          </div>
        {/if}
      </section>
    {/if}

    {#if activeTab === 'db'}
      <section class="dev__panel" aria-label={$_('dev.db.title')}>
        <div class="dev__panel-head">
          <h2>{$_('dev.db.title')}</h2>
          {#if backupsAvailable}
            <button
              class="btn btn-sm variant-filled-primary"
              type="button"
              disabled={!!actionBusy}
              on:click={() =>
                void withAction('dump', async () => {
                  const result = await createDevDbBackup();
                  actionMessage = result.message;
                })}
            >
              {actionBusy === 'dump' ? $_('dev.workers.busy') : $_('dev.db.create')}
            </button>
          {/if}
        </div>
        {#if !backupsAvailable}
          <p class="dev__muted">{$_('dev.db.unavailable')}</p>
        {:else}
          <p class="dev__muted">{$_('dev.db.subtitle', { values: { dir: backupDir } })}</p>
          <p class="dev__muted">{$_('dev.db.encryption_note')}</p>
          {#if backups.length === 0}
            <p class="dev__muted">{$_('dev.db.empty')}</p>
          {:else}
            <ul class="dev__backup-list">
              {#each backups as backup}
                <li>
                  <div>
                    <strong>{backup.name}</strong>
                    <span class="dev__subtle">
                      {formatBytes(backup.size_bytes)} · {formatWhen(backup.created_at)}
                    </span>
                  </div>
                  <button
                    class="btn btn-sm variant-ghost-surface"
                    type="button"
                    disabled={!!actionBusy}
                    on:click={() => {
                      if (
                        !confirm($_('dev.db.restore_confirm', { values: { name: backup.name } }))
                      ) {
                        return;
                      }
                      void withAction(`restore:${backup.name}`, async () => {
                        const result = await restoreDevDbBackup(backup.name);
                        actionMessage = result.message;
                      });
                    }}
                  >
                    {$_('dev.db.restore')}
                  </button>
                </li>
              {/each}
            </ul>
          {/if}
        {/if}
      </section>
    {/if}

    {#if actionMessage}
      <p class="dev__ok-msg" role="status">{actionMessage}</p>
    {/if}
    {#if actionError}
      <p class="dev__panel--error" role="alert">{actionError}</p>
    {/if}
  {/if}

  <p class="dev__footer">
    {$_('dev.auto_refresh')} <code>/api/v1/dev/*</code>.
    {#if copied === 'commit'}
      {$_('dev.commit_copied')}{/if}
  </p>
</main>

{#if $devMode && $devPhase.onboardingPreviewOpen}
  <div
    class="dev__modal-backdrop"
    role="presentation"
    on:click={() => devPhase.setOnboardingPreviewOpen(false)}
  >
    <dialog
      open
      class="dev__modal"
      aria-modal="true"
      aria-labelledby="onboarding-preview-title"
      on:click|stopPropagation
    >
      <div class="dev__modal-head">
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
        class="dev__preview-frame"
        title={$_('settings.developer.preview_title')}
        src="/onboarding?preview=1"
      ></iframe>
    </dialog>
  </div>
{/if}

<style>
  .dev {
    width: min(100%, 58rem);
    margin: 0 auto;
    padding: 1.25rem;
    display: flex;
    flex-direction: column;
    gap: 1rem;
  }

  .dev__top,
  .dev__panel-head {
    display: flex;
    align-items: center;
    justify-content: space-between;
    gap: 1rem;
  }

  .dev__actions {
    display: flex;
    flex-wrap: wrap;
    gap: 0.5rem;
  }

  .dev__intro {
    display: flex;
    flex-direction: column;
    gap: 0.35rem;
  }

  .dev__intro h1,
  .dev__panel h2,
  .dev__card h3,
  .dev__subheading {
    margin: 0;
  }

  .dev__intro h1 {
    font-size: var(--text-2xl, 1.5rem);
  }

  .dev__intro p,
  .dev__muted,
  .dev__footer {
    margin: 0;
    opacity: 0.72;
  }

  .dev__eyebrow {
    font-size: var(--text-xs);
    letter-spacing: 0;
    text-transform: uppercase;
    font-weight: 700;
    color: var(--color-primary);
  }

  .dev__hero,
  .dev__panel,
  .dev__card {
    border-radius: var(--radius-md);
    background: var(--color-surface-chart-bg);
    border: 1px solid var(--color-border-chart);
  }

  .dev__hero {
    display: flex;
    align-items: center;
    justify-content: space-between;
    gap: 1rem;
    padding: 1rem;
  }

  .dev__identity {
    min-width: 0;
    display: flex;
    flex-direction: column;
    gap: 0.25rem;
  }

  .dev__label,
  .dev__subtle,
  .dev__facts dt,
  .dev__footer {
    font-size: var(--text-sm);
  }

  .dev__label,
  .dev__subtle,
  .dev__facts dt {
    color: var(--color-text-muted);
  }

  .dev__commit {
    min-width: 0;
    display: inline-flex;
    align-items: center;
    gap: 0.45rem;
    color: inherit;
    font-family: ui-monospace, SFMono-Regular, Menlo, Monaco, Consolas, monospace;
    font-size: clamp(1.45rem, 6vw, 2rem);
    font-weight: 800;
    text-decoration: none;
    overflow-wrap: anywhere;
  }

  .dev__grid {
    display: grid;
    grid-template-columns: repeat(2, minmax(0, 1fr));
    gap: 1rem;
  }

  .dev__grid--cards {
    grid-template-columns: repeat(3, minmax(0, 1fr));
  }

  .dev__panel {
    padding: 1rem;
    display: flex;
    flex-direction: column;
    gap: 1rem;
  }

  .dev__panel--developer {
    border-color: var(--color-primary);
  }

  .dev__card {
    padding: 0.85rem;
    display: flex;
    flex-direction: column;
    gap: 0.65rem;
  }

  .dev__panel--error {
    border-color: color-mix(in oklch, var(--color-error) 35%, transparent);
    color: var(--color-error);
  }

  .dev__panel--notice {
    border-color: color-mix(in oklch, var(--color-warning) 40%, transparent);
    background: color-mix(in oklch, var(--color-warning) 12%, var(--color-surface));
    color: var(--color-warning);
  }

  .dev__toggle-label {
    display: flex;
    align-items: center;
    gap: 0.75rem;
    cursor: pointer;
    min-height: 2.75rem;
    padding-block: 0.25rem;
    user-select: none;
  }

  .dev__toggle {
    width: 1.25rem;
    height: 1.25rem;
    min-width: 1.25rem;
    cursor: pointer;
    accent-color: var(--color-primary);
  }

  .dev__field-grid {
    display: grid;
    grid-template-columns: repeat(auto-fit, minmax(12rem, 1fr));
    gap: 1rem;
  }

  .dev__field {
    display: flex;
    flex-direction: column;
    gap: 0.5rem;
    font-size: var(--text-sm);
    color: var(--color-text-muted);
  }

  .dev__field select,
  .dev__field input {
    min-height: 44px;
    border: 1px solid var(--color-border);
    border-radius: var(--radius-sm);
    padding: 0 0.75rem;
    background: var(--color-surface);
    color: var(--color-text);
  }

  .dev__advanced {
    display: grid;
    gap: 1rem;
  }

  .dev__advanced summary {
    min-height: 44px;
    display: flex;
    align-items: center;
    cursor: pointer;
    color: var(--color-text-muted);
    font-size: var(--text-sm);
    font-weight: 700;
  }

  .dev__facts {
    margin: 0;
    display: grid;
    gap: 0.8rem;
  }

  .dev__facts div {
    min-width: 0;
  }

  .dev__facts dt,
  .dev__facts dd {
    margin: 0;
  }

  .dev__facts dd {
    margin-top: 0.18rem;
    font-family: ui-monospace, SFMono-Regular, Menlo, Monaco, Consolas, monospace;
    font-size: var(--text-sm);
    overflow-wrap: anywhere;
  }

  .dev__facts--compact {
    grid-template-columns: repeat(2, minmax(0, 1fr));
  }

  .dev__missing {
    color: var(--color-text-muted);
    font-family: inherit;
  }

  .dev__icon-btn {
    width: 2.4rem;
    height: 2.4rem;
    display: inline-flex;
    align-items: center;
    justify-content: center;
    border-radius: var(--radius-md);
    border: 1px solid var(--color-border);
    background: var(--color-surface);
    color: inherit;
  }

  .dev__icon-btn:disabled {
    opacity: 0.42;
  }

  .dev__copy-inline {
    margin-left: 0.5rem;
    border: 0;
    background: transparent;
    color: var(--color-primary);
    font: inherit;
    cursor: pointer;
  }

  .dev__status-list {
    display: flex;
    flex-wrap: wrap;
    gap: 0.5rem;
  }

  .dev__status-list span {
    padding: 0.35rem 0.55rem;
    border-radius: var(--radius-md);
    font-size: var(--text-sm);
    font-weight: 700;
  }

  .dev__ok {
    color: var(--color-success);
    background: color-mix(in oklch, var(--color-success) 14%, var(--color-surface));
  }

  .dev__down {
    color: var(--color-error);
    background: var(--color-error-highlight);
  }

  .dev__footer code {
    font-size: var(--text-sm);
  }

  .dev__table-wrap {
    overflow-x: auto;
  }

  .dev__table {
    width: 100%;
    border-collapse: collapse;
    font-size: var(--text-sm);
  }

  .dev__table th,
  .dev__table td {
    text-align: left;
    padding: 0.45rem 0.35rem;
    border-bottom: 1px solid var(--color-border);
    vertical-align: top;
  }

  .dev__error-inline {
    display: block;
    color: var(--color-error);
    margin-top: 0.25rem;
  }

  .dev__backup-list {
    list-style: none;
    margin: 0;
    padding: 0;
    display: flex;
    flex-direction: column;
    gap: 0.75rem;
  }

  .dev__backup-list li {
    display: flex;
    justify-content: space-between;
    gap: 1rem;
    align-items: center;
  }

  .dev__backup-list strong {
    display: block;
  }

  .dev__ok-msg {
    margin: 0;
    color: var(--color-success);
  }

  .dev__subheading {
    margin: 0;
  }

  .dev__modal-backdrop {
    position: fixed;
    inset: 0;
    z-index: 500;
    display: grid;
    place-items: center;
    padding: 1rem;
    background: color-mix(in srgb, var(--color-surface) 62%, transparent);
  }

  .dev__modal {
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

  .dev__modal-head {
    display: flex;
    align-items: center;
    justify-content: space-between;
    gap: 0.75rem;
    padding: 0.75rem;
    border-bottom: 1px solid var(--color-border);
  }

  .dev__modal-head h2 {
    margin: 0;
    font-size: var(--text-base);
  }

  .dev__preview-frame {
    flex: 1;
    width: 100%;
    border: 0;
    background: var(--color-surface);
  }

  @media (max-width: 768px) {
    .dev {
      padding: 1rem;
    }

    .dev__grid,
    .dev__grid--cards {
      grid-template-columns: 1fr;
    }

    .dev__hero {
      align-items: flex-start;
    }

    .dev__panel-head {
      flex-direction: column;
      align-items: flex-start;
    }
  }
</style>
