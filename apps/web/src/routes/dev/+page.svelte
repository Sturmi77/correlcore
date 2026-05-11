<script lang="ts">
  import { goto } from '$app/navigation';
  import { onDestroy, onMount } from 'svelte';
  import { get } from 'svelte/store';
  import IconRender from '$lib/components/common/IconRender.svelte';
  import ThemeToggle from '$lib/components/common/ThemeToggle.svelte';
  import { ApiError } from '$lib/api/client';
  import { fetchDevInfo, type DevInfoResponse } from '$lib/api/dev';
  import { developerMode } from '$lib/stores/developerMode';

  const COMMIT_BASE_URL = 'https://github.com/sturmi77/moodsync/commit/';
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
      error = err instanceof Error ? err.message : 'Developer information could not be loaded.';
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
  <title>Developer View - MoodSync</title>
</svelte:head>

<main class="dev">
  <header class="dev__top">
    <a class="btn btn-sm variant-ghost-surface" href="/settings">Settings</a>
    <ThemeToggle testId="dev-theme-toggle" />
  </header>

  <section class="dev__intro">
    <p class="dev__eyebrow">Runtime diagnostics</p>
    <h1>Developer View</h1>
    <p>Verify the deployed GitHub commit, image tag and optional OCI digest.</p>
  </section>

  {#if backendUnavailable}
    <section class="dev__panel dev__panel--notice" role="status">
      <p>
        <strong>Backend developer endpoint not available.</strong><br />
        <code>DEV_VIEW_ENABLED</code> is set to <code>false</code> on the server. Runtime diagnostics
        are unavailable in this environment. The Developer View was opened because you enabled the manual
        toggle in Settings.
      </p>
      <a class="btn btn-sm variant-ghost-surface" href="/settings">Back to Settings</a>
    </section>
  {:else if loading && !info}
    <section class="dev__panel">
      <p class="dev__muted">Loading runtime details...</p>
    </section>
  {:else if error}
    <section class="dev__panel dev__panel--error" role="alert">
      <p>{error}</p>
      <button class="btn btn-sm variant-ghost-surface" type="button" on:click={() => void load()}>
        Retry
      </button>
    </section>
  {:else if info}
    <section class="dev__hero" aria-label="Version identity">
      <div class="dev__identity">
        <span class="dev__label">GitHub Commit</span>
        {#if activeCommitUrl}
          <a class="dev__commit" href={activeCommitUrl} target="_blank" rel="noreferrer">
            {shortCommit(info.git_commit)}
            <IconRender icon="external-link" size={18} />
          </a>
        {:else}
          <span class="dev__commit">{shortCommit(info.git_commit)}</span>
        {/if}
        <span class="dev__subtle">{info.git_branch}</span>
      </div>
      <button
        class="dev__icon-btn"
        type="button"
        aria-label="Copy GitHub commit"
        title="Copy GitHub commit"
        disabled={info.git_commit === 'unknown'}
        on:click={() => copyValue('commit', info?.git_commit ?? null)}
      >
        <IconRender icon="copy" size={18} />
      </button>
    </section>

    <section class="dev__grid">
      <article class="dev__panel">
        <div class="dev__panel-head">
          <h2>Container Image</h2>
          <button
            class="dev__icon-btn"
            type="button"
            aria-label="Refresh developer information"
            title="Refresh developer information"
            on:click={() => void load()}
          >
            <IconRender icon="refresh-cw" size={18} />
          </button>
        </div>
        <dl class="dev__facts">
          <div>
            <dt>Image Tag</dt>
            <dd>{info.image_tag}</dd>
          </div>
          <div>
            <dt>Image Digest</dt>
            <dd class:dev__missing={!info.image_digest}>
              {info.image_digest ?? 'Digest not provided'}
              {#if info.image_digest}
                <button
                  class="dev__copy-inline"
                  type="button"
                  on:click={() => copyValue('digest', info?.image_digest ?? null)}
                >
                  {copied === 'digest' ? 'Copied' : 'Copy'}
                </button>
              {/if}
            </dd>
          </div>
          <div>
            <dt>Image Hash</dt>
            <dd>{info.image_hash}</dd>
          </div>
          <div>
            <dt>Build Time</dt>
            <dd>{info.build_time ?? 'Not provided'}</dd>
          </div>
        </dl>
      </article>

      <article class="dev__panel">
        <h2>Runtime</h2>
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
            <dt>DB Migration</dt>
            <dd>{info.db_migration_head ?? 'Unavailable'}</dd>
          </div>
          <div>
            <dt>Uptime</dt>
            <dd>{formatUptime(info.uptime_seconds)}</dd>
          </div>
        </dl>
      </article>

      <article class="dev__panel">
        <h2>Infrastructure</h2>
        <div class="dev__status-list">
          <span class:dev__ok={info.health_ready} class:dev__down={!info.health_ready}>
            Health {info.health_ready ? 'ready' : 'not ready'}
          </span>
          <span class:dev__ok={info.redis_connected} class:dev__down={!info.redis_connected}>
            Redis {info.redis_connected ? 'connected' : 'down'}
          </span>
          <span class:dev__ok={info.minio_connected} class:dev__down={!info.minio_connected}>
            MinIO {info.minio_connected ? 'connected' : 'down'}
          </span>
        </div>
        <dl class="dev__facts dev__facts--compact">
          <div>
            <dt>DB Pool Size</dt>
            <dd>{info.db_pool_size ?? 'n/a'}</dd>
          </div>
          <div>
            <dt>DB Checked Out</dt>
            <dd>{info.db_checked_out ?? 'n/a'}</dd>
          </div>
        </dl>
      </article>
    </section>

    <p class="dev__footer">
      Auto-refreshes every 30 seconds. Last loaded from <code>/api/v1/dev/info</code>.
      {#if copied === 'commit'}
        Commit copied.{/if}
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
    font-size: 0.78rem;
    letter-spacing: 0;
    text-transform: uppercase;
    font-weight: 700;
    color: rgb(var(--color-primary-600, 59 130 246));
  }

  .dev__hero,
  .dev__panel {
    border-radius: 0.5rem;
    background: rgb(var(--color-surface-50, 249 250 251) / 0.82);
    border: 1px solid rgb(var(--color-surface-300, 209 213 219) / 0.5);
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
    font-size: 0.82rem;
  }

  .dev__label,
  .dev__subtle,
  .dev__facts dt {
    color: rgb(var(--color-surface-600, 75 85 99));
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
    border-color: rgb(185 28 28 / 0.35);
    color: #991b1b;
  }

  .dev__panel--notice {
    border-color: rgb(var(--color-warning-500, 202 138 4) / 0.4);
    background: rgb(var(--color-warning-50, 254 252 232) / 0.6);
    color: rgb(var(--color-warning-800, 133 77 14));
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
    font-size: 0.92rem;
    overflow-wrap: anywhere;
  }

  .dev__facts--compact {
    grid-template-columns: repeat(2, minmax(0, 1fr));
  }

  .dev__missing {
    color: rgb(var(--color-surface-600, 75 85 99));
    font-family: inherit;
  }

  .dev__icon-btn {
    width: 2.4rem;
    height: 2.4rem;
    display: inline-flex;
    align-items: center;
    justify-content: center;
    border-radius: 0.5rem;
    border: 1px solid rgb(var(--color-surface-300, 209 213 219) / 0.7);
    background: rgb(var(--color-surface-100, 243 244 246) / 0.72);
    color: inherit;
  }

  .dev__icon-btn:disabled {
    opacity: 0.42;
  }

  .dev__copy-inline {
    margin-left: 0.5rem;
    border: 0;
    background: transparent;
    color: rgb(var(--color-primary-600, 37 99 235));
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
    border-radius: 0.5rem;
    font-size: 0.84rem;
    font-weight: 700;
  }

  .dev__ok {
    color: #166534;
    background: rgb(220 252 231 / 0.7);
  }

  .dev__down {
    color: #991b1b;
    background: rgb(254 226 226 / 0.78);
  }

  .dev__footer code {
    font-size: 0.82rem;
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
