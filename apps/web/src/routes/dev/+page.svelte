<script lang="ts">
  import { goto } from '$app/navigation';
  import { onDestroy, onMount } from 'svelte';
  import { get } from 'svelte/store';
  import { _ } from 'svelte-i18n';
  import IconRender from '$lib/components/common/IconRender.svelte';
  import ThemeToggle from '$lib/components/common/ThemeToggle.svelte';
  import { ApiError } from '$lib/api/client';
  import { fetchDevInfo, type DevInfoResponse } from '$lib/api/dev';
  import { ICON_SIZE_MD } from '$lib/constants/iconSizes';
  import { developerMode } from '$lib/stores/developerMode';

  const COMMIT_BASE_URL = 'https://github.com/sturmi77/correlcore/commit/';
  const REFRESH_MS = 30_000;

  let info: DevInfoResponse | null = null;
  let loading = true;
  let error = '';
  let backendUnavailable = false;
  let copied: 'commit' | 'digest' | null = null;
  let controller: AbortController | null = null;
  let interval: ReturnType<typeof setInterval> | null = null;
  let copyTimer: ReturnType<typeof setTimeout> | null = null;
  let activeCommitUrl: string | null = null;

  $: activeCommitUrl = info ? commitUrl(info.git_commit) : null;

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

  async function load(): Promise<void> {
    controller?.abort();
    controller = new AbortController();
    loading = !info;
    error = '';
    backendUnavailable = false;
    try {
      info = await fetchDevInfo(controller.signal);
    } catch (err) {
      if ((err as Error).name === 'AbortError') return;
      if (err instanceof ApiError && err.status === 404) {
        // Only redirect when the developer mode store is NOT manually active.
        // When the user enabled the toggle in Settings, stay on the page and
        // show an informational notice instead of bouncing them back.
        if (!get(developerMode)) {
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

  {#if backendUnavailable}
    <section class="dev__panel dev__panel--notice" role="status">
      <p>
        <strong>{$_('dev.backend_unavailable_title')}</strong><br />
        {$_('dev.backend_unavailable_body')}
      </p>
      <a class="btn btn-sm variant-ghost-surface" href="/settings">{$_('dev.back_settings')}</a>
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

    <section class="dev__grid">
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

    <p class="dev__footer">
      {$_('dev.auto_refresh')} <code>/api/v1/dev/info</code>.
      {#if copied === 'commit'}
        {$_('dev.commit_copied')}{/if}
    </p>
  {/if}
</main>

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

  .dev__intro {
    display: flex;
    flex-direction: column;
    gap: 0.35rem;
  }

  .dev__intro h1,
  .dev__panel h2 {
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
  .dev__panel {
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

  .dev__panel {
    padding: 1rem;
    display: flex;
    flex-direction: column;
    gap: 1rem;
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

  @media (max-width: 720px) {
    .dev {
      padding: 1rem;
    }

    .dev__grid {
      grid-template-columns: 1fr;
    }

    .dev__hero {
      align-items: flex-start;
    }
  }
</style>
