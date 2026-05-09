<script lang="ts">
  import { _ } from 'svelte-i18n';
  import { auth } from '$lib/stores/auth';
  import ThemeToggle from '$lib/components/common/ThemeToggle.svelte';
  import { downloadExport, exportFilename, saveBlob, type ExportKind } from '$lib/api/export';

  let busy: ExportKind | null = null;
  let error = '';

  async function handleDownload(kind: ExportKind): Promise<void> {
    busy = kind;
    error = '';
    try {
      const blob = await downloadExport(kind);
      saveBlob(blob, exportFilename(kind));
    } catch (err) {
      error = err instanceof Error ? err.message : $_('settings.export.error');
    } finally {
      busy = null;
    }
  }
</script>

<svelte:head>
  <title>{$_('settings.title')} - {$_('app.name')}</title>
</svelte:head>

<main class="settings">
  <header class="settings__top">
    <a class="btn btn-sm variant-ghost-surface" href="/">{$_('nav.home')}</a>
    <ThemeToggle testId="settings-theme-toggle" />
  </header>

  <section class="settings__intro">
    <h1>{$_('settings.title')}</h1>
    <p>{$_('settings.subtitle')}</p>
  </section>

  {#if $auth.status !== 'authenticated'}
    <section class="settings__panel">
      <p>{$_('settings.auth_required')}</p>
      <a class="btn btn-sm variant-filled-primary" href="/auth/login">{$_('auth.login.submit')}</a>
    </section>
  {:else}
    <section class="settings__panel">
      <div class="settings__panel-head">
        <h2>{$_('settings.export.heading')}</h2>
        <p>{$_('settings.export.body')}</p>
      </div>
      <div class="settings__downloads">
        <button
          class="btn variant-filled-primary"
          type="button"
          disabled={busy !== null}
          on:click={() => handleDownload('zip')}
        >
          {busy === 'zip' ? $_('settings.export.busy') : $_('settings.export.zip')}
        </button>
        <button
          class="btn variant-soft-primary"
          type="button"
          disabled={busy !== null}
          on:click={() => handleDownload('json')}
        >
          {busy === 'json' ? $_('settings.export.busy') : $_('settings.export.json')}
        </button>
        <button
          class="btn variant-soft-primary"
          type="button"
          disabled={busy !== null}
          on:click={() => handleDownload('csv')}
        >
          {busy === 'csv' ? $_('settings.export.busy') : $_('settings.export.csv')}
        </button>
      </div>
      {#if error}
        <p class="settings__error" role="alert">{error}</p>
      {/if}
    </section>
  {/if}
</main>

<style>
  .settings {
    width: min(100%, 46rem);
    margin: 0 auto;
    padding: 1.25rem;
    display: flex;
    flex-direction: column;
    gap: 1rem;
  }

  .settings__top {
    display: flex;
    align-items: center;
    justify-content: space-between;
  }

  .settings__intro h1 {
    margin: 0;
    font-size: var(--text-2xl, 1.5rem);
  }

  .settings__intro p,
  .settings__panel-head p {
    margin: 0.25rem 0 0;
    opacity: 0.72;
  }

  .settings__panel {
    display: flex;
    flex-direction: column;
    gap: 1rem;
    padding: 1rem;
    border-radius: 0.5rem;
    background: rgb(var(--color-surface-50, 249 250 251) / 0.78);
    border: 1px solid rgb(var(--color-surface-300, 209 213 219) / 0.5);
  }

  .settings__panel-head h2 {
    margin: 0;
    font-size: var(--text-lg, 1.125rem);
  }

  .settings__downloads {
    display: flex;
    flex-wrap: wrap;
    gap: 0.65rem;
  }

  .settings__error {
    margin: 0;
    color: #b91c1c;
  }
</style>
