<script lang="ts">
  import { onMount } from 'svelte';
  import { _ } from 'svelte-i18n';
  import { auth } from '$lib/stores/auth';
  import Button from '$lib/components/common/Button.svelte';
  import DataState from '$lib/components/common/DataState.svelte';
  import InlineAlert from '$lib/components/common/InlineAlert.svelte';
  import Panel from '$lib/components/common/Panel.svelte';
  import ScreenHeader from '$lib/components/common/ScreenHeader.svelte';
  import {
    deleteSymptom,
    listVisibleSymptoms,
    updateSymptom,
    type SymptomResponse,
  } from '$lib/api/symptoms';
  import { refreshSymptoms } from '$lib/stores/symptoms';

  type Draft = { name: string; icon: string };

  let loading = true;
  let busyId: string | null = null;
  let confirmDeleteId: string | null = null;
  let error = '';
  let symptoms: SymptomResponse[] = [];
  let drafts: Record<string, Draft> = {};

  async function load(): Promise<void> {
    if ($auth.status !== 'authenticated') {
      loading = false;
      return;
    }
    loading = true;
    error = '';
    try {
      symptoms = await listVisibleSymptoms();
      drafts = Object.fromEntries(
        symptoms.map((symptom) => [symptom.id, { name: symptom.name, icon: symptom.icon ?? '' }])
      );
    } catch (err) {
      error = err instanceof Error ? err.message : $_('settings.symptoms.error_load');
    } finally {
      loading = false;
    }
  }

  function updateDraft(id: string, patch: Partial<Draft>): void {
    drafts = { ...drafts, [id]: { ...drafts[id], ...patch } };
  }

  async function save(symptom: SymptomResponse): Promise<void> {
    const draft = drafts[symptom.id];
    if (!draft?.name.trim()) return;
    busyId = symptom.id;
    error = '';
    try {
      const updated = await updateSymptom(symptom.id, {
        name: draft.name.trim(),
        icon: draft.icon.trim() || null,
      });
      symptoms = symptoms.map((item) => (item.id === updated.id ? updated : item));
      void refreshSymptoms().catch(() => undefined);
    } catch (err) {
      error = err instanceof Error ? err.message : $_('settings.symptoms.error_save');
    } finally {
      busyId = null;
    }
  }

  async function remove(symptom: SymptomResponse): Promise<void> {
    busyId = symptom.id;
    error = '';
    try {
      await deleteSymptom(symptom.id);
      symptoms = symptoms.filter((item) => item.id !== symptom.id);
      confirmDeleteId = null;
      void refreshSymptoms().catch(() => undefined);
    } catch (err) {
      error = err instanceof Error ? err.message : $_('settings.symptoms.error_delete');
    } finally {
      busyId = null;
    }
  }

  $: defaults = symptoms.filter((symptom) => symptom.is_default);
  $: custom = symptoms.filter((symptom) => !symptom.is_default);

  onMount(() => void load());
</script>

<svelte:head>
  <title>{$_('settings.symptoms.title')} - {$_('app.name')}</title>
</svelte:head>

<main class="symptom-settings">
  <ScreenHeader
    title={$_('settings.symptoms.title')}
    subtitle={$_('settings.symptoms.subtitle')}
    compact
  >
    <Button slot="actions" href="/settings" variant="ghost" size="sm">
      {$_('settings.symptoms.back_settings')}
    </Button>
  </ScreenHeader>

  {#if $auth.status !== 'authenticated'}
    <Panel variant="bordered">
      <p>{$_('settings.auth_required')}</p>
      <Button href="/auth/login" variant="primary" size="sm">{$_('auth.login.submit')}</Button>
    </Panel>
  {:else if loading}
    <DataState
      state="loading"
      loadingText={$_('symptom.loading')}
      testId="symptom-settings-loading"
    />
  {:else}
    {#if error}
      <InlineAlert variant="error" message={error} testId="symptom-settings-error" />
    {/if}

    <section class="symptom-settings__section" aria-labelledby="custom-symptoms-heading">
      <div class="symptom-settings__heading">
        <h2 id="custom-symptoms-heading">{$_('settings.symptoms.custom_heading')}</h2>
        <p>{$_('settings.symptoms.custom_body')}</p>
      </div>
      {#if custom.length === 0}
        <p class="symptom-settings__empty">{$_('settings.symptoms.custom_empty')}</p>
      {:else}
        <div class="symptom-settings__list">
          {#each custom as symptom (symptom.id)}
            {@const draft = drafts[symptom.id]}
            <article class="symptom-settings__row" data-testid="custom-symptom-row">
              <label>
                <span>{$_('settings.symptoms.name')}</span>
                <input
                  class="input"
                  value={draft?.name ?? ''}
                  maxlength="64"
                  on:input={(event) => updateDraft(symptom.id, { name: event.currentTarget.value })}
                />
              </label>
              <label>
                <span>{$_('settings.symptoms.icon')}</span>
                <input
                  class="input"
                  value={draft?.icon ?? ''}
                  maxlength="32"
                  on:input={(event) => updateDraft(symptom.id, { icon: event.currentTarget.value })}
                />
              </label>
              <div class="symptom-settings__actions">
                <Button
                  variant="primary"
                  size="sm"
                  disabled={busyId !== null || !draft?.name.trim()}
                  loading={busyId === symptom.id && confirmDeleteId !== symptom.id}
                  on:click={() => void save(symptom)}
                >
                  {$_('settings.symptoms.save')}
                </Button>
                {#if confirmDeleteId === symptom.id}
                  <Button
                    variant="danger"
                    size="sm"
                    disabled={busyId !== null}
                    loading={busyId === symptom.id}
                    on:click={() => void remove(symptom)}
                  >
                    {$_('settings.symptoms.confirm_delete')}
                  </Button>
                  <Button variant="ghost" size="sm" on:click={() => (confirmDeleteId = null)}>
                    {$_('settings.symptoms.cancel')}
                  </Button>
                {:else}
                  <Button variant="ghost" size="sm" on:click={() => (confirmDeleteId = symptom.id)}>
                    {$_('settings.symptoms.delete')}
                  </Button>
                {/if}
              </div>
            </article>
          {/each}
        </div>
      {/if}
    </section>

    <section class="symptom-settings__section" aria-labelledby="default-symptoms-heading">
      <div class="symptom-settings__heading">
        <h2 id="default-symptoms-heading">{$_('settings.symptoms.default_heading')}</h2>
        <p>{$_('settings.symptoms.default_body')}</p>
      </div>
      <div class="symptom-settings__defaults">
        {#each defaults as symptom (symptom.id)}
          <span>{symptom.icon ?? '#'} {symptom.name}</span>
        {/each}
      </div>
    </section>
  {/if}
</main>

<style>
  .symptom-settings {
    width: min(100%, 54rem);
    margin: 0 auto;
    padding: var(--space-4);
    display: grid;
    gap: var(--space-4);
  }

  .symptom-settings__section {
    padding: var(--space-4);
    border: 1px solid var(--color-border-chart);
    border-radius: var(--radius-md);
    background: var(--color-surface-chart-bg);
  }

  .symptom-settings__heading h2,
  .symptom-settings__heading p,
  .symptom-settings__empty {
    margin: 0;
  }

  .symptom-settings__heading h2 {
    font-size: var(--text-lg);
  }

  .symptom-settings__heading p,
  .symptom-settings__empty {
    margin-top: var(--space-1);
    color: var(--color-text-muted);
    font-size: var(--text-sm);
  }

  .symptom-settings__list {
    display: grid;
    margin-top: var(--space-3);
  }

  .symptom-settings__row {
    display: grid;
    grid-template-columns: minmax(12rem, 1fr) minmax(8rem, 0.6fr) auto;
    gap: var(--space-3);
    align-items: end;
    padding-block: var(--space-3);
    border-top: 1px solid var(--color-border);
  }

  .symptom-settings__row label {
    display: grid;
    gap: var(--space-1);
    color: var(--color-text-muted);
    font-size: var(--text-xs);
  }

  .symptom-settings__row input {
    min-height: 44px;
  }

  .symptom-settings__actions,
  .symptom-settings__defaults {
    display: flex;
    flex-wrap: wrap;
    gap: var(--space-2);
  }

  .symptom-settings__defaults {
    margin-top: var(--space-3);
  }

  .symptom-settings__defaults span {
    min-height: 44px;
    display: inline-flex;
    align-items: center;
    padding: var(--space-2) var(--space-3);
    border: 1px solid var(--color-border);
    border-radius: var(--radius-sm);
    background: var(--color-surface-2);
  }

  @media (max-width: 680px) {
    .symptom-settings__row {
      grid-template-columns: 1fr;
      align-items: stretch;
    }
  }
</style>
