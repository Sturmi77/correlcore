<script lang="ts">
  import { onMount } from 'svelte';
  import { _ } from 'svelte-i18n';
  import { auth } from '$lib/stores/auth';
  import Button from '$lib/components/common/Button.svelte';
  import IconButton from '$lib/components/common/IconButton.svelte';
  import InlineAlert from '$lib/components/common/InlineAlert.svelte';
  import Panel from '$lib/components/common/Panel.svelte';
  import ScreenHeader from '$lib/components/common/ScreenHeader.svelte';
  import { deleteCycleData } from '$lib/api/entries';
  import { clearCycleDataOffline } from '$lib/stores/entriesOffline';
  import { downloadExport, exportFilename, saveBlob, type ExportKind } from '$lib/api/export';
  import {
    fetchUserPreferences,
    updateUserPreferences,
    type UserPreferencesResponse,
  } from '$lib/api/preferences';
  import { registerPageRefresh } from '$lib/stores/pageRefresh';

  let busy: ExportKind | null = null;
  let error = '';
  let preferences: UserPreferencesResponse | null = null;
  let preferencesBusy = false;
  let preferencesError = '';
  let cycleDeleteDialogOpen = false;
  let cycleDeleteBusy = false;
  let cycleDeleteError = '';
  let cycleDeleteMessage = '';

  async function loadPreferences(): Promise<void> {
    if ($auth.status !== 'authenticated') return;
    try {
      preferences = await fetchUserPreferences();
    } catch (err) {
      preferencesError = err instanceof Error ? err.message : $_('settings.analysis.error');
    }
  }

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

  async function toggleCycleTracking(enabled: boolean): Promise<void> {
    preferencesBusy = true;
    preferencesError = '';
    try {
      preferences = await updateUserPreferences({ cycle_tracking_enabled: enabled });
    } catch (err) {
      preferencesError = err instanceof Error ? err.message : $_('settings.analysis.error');
    } finally {
      preferencesBusy = false;
    }
  }

  function openCycleDeleteDialog(): void {
    cycleDeleteError = '';
    cycleDeleteMessage = '';
    cycleDeleteDialogOpen = true;
  }

  function closeCycleDeleteDialog(): void {
    if (cycleDeleteBusy) return;
    cycleDeleteDialogOpen = false;
    cycleDeleteError = '';
  }

  async function confirmDeleteCycleData(): Promise<void> {
    cycleDeleteBusy = true;
    cycleDeleteError = '';
    cycleDeleteMessage = '';
    try {
      const result = await deleteCycleData();
      await clearCycleDataOffline();
      cycleDeleteMessage = $_('settings.cycle.delete_success', {
        values: { count: result.cleared_entries },
      });
      cycleDeleteDialogOpen = false;
    } catch (err) {
      cycleDeleteError = err instanceof Error ? err.message : $_('settings.cycle.delete_error');
    } finally {
      cycleDeleteBusy = false;
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
  <title>{$_('settings.groups.data.title')} - {$_('app.name')}</title>
</svelte:head>

<main class="data-settings screen-stack">
  <ScreenHeader
    title={$_('settings.groups.data.title')}
    subtitle={$_('settings.groups.data.subtitle')}
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
      <div class="data-settings__head">
        <h2>{$_('settings.vocabulary.heading')}</h2>
        <p>{$_('settings.vocabulary.body')}</p>
      </div>
      <div class="data-settings__grid">
        <a class="data-settings__card" href="/settings/tags" data-testid="settings-vocab-tags">
          <strong>{$_('settings.vocabulary.tags')}</strong>
          <span>{$_('settings.vocabulary.tags_body')}</span>
        </a>
        <a
          class="data-settings__card"
          href="/settings/symptoms"
          data-testid="settings-vocab-symptoms"
        >
          <strong>{$_('settings.vocabulary.symptoms')}</strong>
          <span>{$_('settings.vocabulary.symptoms_body')}</span>
        </a>
        <a class="data-settings__card" href="/settings/tags" data-testid="settings-vocab-habits">
          <strong>{$_('settings.vocabulary.habits')}</strong>
          <span>{$_('settings.vocabulary.habits_body')}</span>
        </a>
      </div>
    </Panel>

    <Panel variant="bordered">
      <div class="data-settings__head">
        <h2>{$_('settings.cycle.heading')}</h2>
        <p>{$_('settings.cycle.body')}</p>
      </div>
      <label class="data-settings__toggle-label">
        <input
          type="checkbox"
          class="data-settings__toggle"
          checked={preferences?.cycle_tracking_enabled ?? true}
          disabled={preferencesBusy}
          data-testid="cycle-toggle"
          on:change={(e) => void toggleCycleTracking(e.currentTarget.checked)}
        />
        <span>{$_('settings.cycle.enabled')}</span>
      </label>
      <p class="data-settings__note">{$_('settings.cycle.hint')}</p>
      <div class="data-settings__actions">
        <Button
          variant="danger"
          type="button"
          data-testid="cycle-delete-data"
          disabled={preferencesBusy || cycleDeleteBusy}
          on:click={openCycleDeleteDialog}
        >
          {$_('settings.cycle.delete_action')}
        </Button>
      </div>
      {#if cycleDeleteMessage}
        <InlineAlert variant="success" message={cycleDeleteMessage} />
      {/if}
      {#if preferencesError}
        <InlineAlert variant="error" message={preferencesError} />
      {/if}
    </Panel>

    <Panel variant="bordered" data-testid="settings-section-export">
      <div class="data-settings__head">
        <h2>{$_('settings.export.heading')}</h2>
        <p>{$_('settings.export.body')}</p>
      </div>
      <div class="data-settings__actions">
        <Button
          variant="primary"
          type="button"
          loading={busy === 'zip'}
          disabled={busy !== null}
          on:click={() => handleDownload('zip')}
        >
          {busy === 'zip' ? $_('settings.export.busy') : $_('settings.export.zip')}
        </Button>
        <Button
          variant="secondary"
          type="button"
          loading={busy === 'json'}
          disabled={busy !== null}
          on:click={() => handleDownload('json')}
        >
          {busy === 'json' ? $_('settings.export.busy') : $_('settings.export.json')}
        </Button>
        <Button
          variant="secondary"
          type="button"
          loading={busy === 'csv'}
          disabled={busy !== null}
          on:click={() => handleDownload('csv')}
        >
          {busy === 'csv' ? $_('settings.export.busy') : $_('settings.export.csv')}
        </Button>
      </div>
      {#if error}
        <InlineAlert variant="error" message={error} />
      {/if}
    </Panel>
  {/if}
</main>

{#if cycleDeleteDialogOpen}
  <div
    class="data-settings__modal-backdrop"
    role="presentation"
    data-testid="cycle-delete-backdrop"
    on:click={closeCycleDeleteDialog}
  >
    <dialog
      open
      class="data-settings__modal"
      aria-modal="true"
      aria-labelledby="cycle-delete-title"
      data-testid="cycle-delete-dialog"
      on:click|stopPropagation
    >
      <div class="data-settings__modal-head">
        <h2 id="cycle-delete-title">{$_('settings.cycle.delete_title')}</h2>
        <IconButton
          type="button"
          ariaLabel={$_('settings.cycle.delete_cancel')}
          title={$_('settings.cycle.delete_cancel')}
          on:click={closeCycleDeleteDialog}
        >
          x
        </IconButton>
      </div>
      <div class="data-settings__modal-body">
        <p>{$_('settings.cycle.delete_body')}</p>
        {#if cycleDeleteError}
          <InlineAlert variant="error" message={cycleDeleteError} />
        {/if}
        <div class="data-settings__actions">
          <Button
            variant="ghost"
            type="button"
            on:click={closeCycleDeleteDialog}
            disabled={cycleDeleteBusy}
          >
            {$_('settings.cycle.delete_cancel')}
          </Button>
          <Button
            variant="danger"
            type="button"
            loading={cycleDeleteBusy}
            disabled={cycleDeleteBusy}
            data-testid="cycle-delete-confirm"
            on:click={() => void confirmDeleteCycleData()}
          >
            {cycleDeleteBusy
              ? $_('settings.cycle.delete_busy')
              : $_('settings.cycle.delete_confirm')}
          </Button>
        </div>
      </div>
    </dialog>
  </div>
{/if}

<style>
  .data-settings {
    width: min(100%, 46rem);
    margin: 0 auto;
  }

  .data-settings__head h2 {
    margin: 0;
    font-size: var(--text-lg, 1.125rem);
  }

  .data-settings__head p {
    margin: var(--space-1) 0 0;
    color: var(--color-text-muted);
    line-height: 1.5;
  }

  .data-settings__grid {
    display: grid;
    gap: var(--space-3);
    grid-template-columns: repeat(auto-fit, minmax(12rem, 1fr));
    margin-top: var(--space-3);
  }

  .data-settings__card {
    display: flex;
    flex-direction: column;
    gap: var(--space-1);
    min-height: 5.5rem;
    padding: var(--space-3);
    border: 1px solid var(--color-border);
    border-radius: var(--radius-md);
    background: var(--color-surface);
    color: inherit;
    text-decoration: none;
    transition:
      border-color var(--transition-fast),
      background-color var(--transition-fast);
  }

  .data-settings__card:hover {
    border-color: color-mix(in srgb, var(--color-primary) 35%, var(--color-border));
    background: color-mix(in srgb, var(--color-primary-soft) 28%, var(--color-surface));
  }

  .data-settings__card strong {
    font-size: var(--text-base);
  }

  .data-settings__card span {
    font-size: var(--text-sm);
    color: var(--color-text-muted);
    line-height: 1.45;
  }

  .data-settings__actions {
    display: flex;
    flex-wrap: wrap;
    gap: 0.65rem;
    margin-top: var(--space-3);
  }

  .data-settings__note {
    margin: var(--space-2) 0 0;
    color: var(--color-text-muted);
    font-size: var(--text-sm);
    line-height: 1.5;
  }

  .data-settings__toggle-label {
    display: flex;
    align-items: center;
    gap: 0.75rem;
    cursor: pointer;
    min-height: 2.75rem;
    padding-block: 0.25rem;
    user-select: none;
    margin-top: var(--space-2);
  }

  .data-settings__toggle {
    width: 1.25rem;
    height: 1.25rem;
    min-width: 1.25rem;
    cursor: pointer;
    accent-color: var(--color-primary);
  }

  .data-settings__modal-backdrop {
    position: fixed;
    inset: 0;
    z-index: 500;
    display: grid;
    place-items: center;
    padding: var(--space-4);
    background: color-mix(in srgb, var(--color-surface) 62%, transparent);
  }

  .data-settings__modal {
    width: min(100%, 28rem);
    display: flex;
    flex-direction: column;
    overflow: hidden;
    border: 1px solid var(--color-border);
    border-radius: var(--radius-md);
    background: var(--color-surface);
    box-shadow: var(--shadow-lg);
  }

  .data-settings__modal-head {
    display: flex;
    align-items: center;
    justify-content: space-between;
    gap: var(--space-3);
    padding: var(--space-3);
    border-bottom: 1px solid var(--color-border);
  }

  .data-settings__modal-head h2 {
    margin: 0;
    font-size: var(--text-base);
  }

  .data-settings__modal-body {
    display: flex;
    flex-direction: column;
    gap: var(--space-3);
    padding: var(--space-4);
  }

  .data-settings__modal-body p {
    margin: 0;
    color: var(--color-text-muted);
    line-height: 1.5;
  }
</style>
