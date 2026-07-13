<script lang="ts">
  import { onMount } from 'svelte';
  import { _ } from 'svelte-i18n';
  import { auth } from '$lib/stores/auth';
  import Button from '$lib/components/common/Button.svelte';
  import DataState from '$lib/components/common/DataState.svelte';
  import IconRender from '$lib/components/common/IconRender.svelte';
  import InlineAlert from '$lib/components/common/InlineAlert.svelte';
  import Panel from '$lib/components/common/Panel.svelte';
  import ScreenHeader from '$lib/components/common/ScreenHeader.svelte';
  import {
    TAG_CATEGORIES,
    createTag,
    deleteTag,
    listDefaultTags,
    listVisibleTags,
    updateTag,
    type TagCategory,
    type HabitType,
    type TagResponse,
  } from '$lib/api/tags';
  import { ICON_SIZE_MD } from '$lib/constants/iconSizes';
  import { defaultTagColorForCurrentTheme } from '$lib/constants/tagDefaults';
  import { refreshTags } from '$lib/stores/tags';

  type Draft = {
    name: string;
    category: TagCategory;
    icon: string;
    color: string;
    habit_type: HabitType;
    target_frequency: number;
  };

  let loading = true;
  let savingId: string | null = null;
  let error = '';
  let tags: TagResponse[] = [];
  let defaultBySlug: Record<string, TagResponse> = {};
  let drafts: Record<string, Draft> = {};
  let creating = false;
  let newDraft: Draft = {
    name: '',
    category: 'other',
    icon: '',
    color: defaultTagColorForCurrentTheme(),
    habit_type: 'none',
    target_frequency: 3,
  };

  function slugifyName(name: string): string {
    return name
      .toLowerCase()
      .replace(/[^a-z0-9]+/g, '-')
      .replace(/^-+|-+$/g, '')
      .slice(0, 64);
  }

  function resetNewDraft(): void {
    newDraft = {
      name: '',
      category: 'other',
      icon: '',
      color: defaultTagColorForCurrentTheme(),
      habit_type: 'none',
      target_frequency: 3,
    };
  }

  function draftFrom(tag: TagResponse): Draft {
    return {
      name: tag.name,
      category: tag.category,
      icon: tag.icon ?? '',
      color: tag.color ?? defaultTagColorForCurrentTheme(),
      habit_type: tag.habit_type,
      target_frequency: tag.target_frequency ?? 3,
    };
  }

  async function load(): Promise<void> {
    if ($auth.status !== 'authenticated') {
      loading = false;
      return;
    }
    loading = true;
    error = '';
    try {
      const [defaults, visible] = await Promise.all([
        listDefaultTags(),
        listVisibleTags({ include_hidden: true }),
      ]);
      defaultBySlug = Object.fromEntries(defaults.map((tag) => [tag.slug, tag]));
      tags = visible;
      drafts = Object.fromEntries(visible.map((tag) => [tag.id, draftFrom(tag)]));
    } catch (err) {
      error = err instanceof Error ? err.message : $_('settings.tags.error_load');
    } finally {
      loading = false;
    }
  }

  function isOverride(tag: TagResponse): boolean {
    return !tag.is_default && Boolean(defaultBySlug[tag.slug]);
  }

  function setDraft(id: string, patch: Partial<Draft>): void {
    drafts = {
      ...drafts,
      [id]: {
        ...drafts[id],
        ...patch,
      },
    };
  }

  async function createNewTag(): Promise<void> {
    const name = newDraft.name.trim();
    if (!name) return;
    creating = true;
    error = '';
    try {
      await createTag({
        slug: slugifyName(name) || 'tag',
        name,
        category: newDraft.category,
        icon: newDraft.icon.trim() ? newDraft.icon.trim() : null,
        color: newDraft.color,
        habit_type: newDraft.habit_type,
        target_frequency: newDraft.habit_type === 'none' ? null : newDraft.target_frequency,
      });
      resetNewDraft();
      await load();
      await refreshTags();
    } catch (err) {
      error = err instanceof Error ? err.message : $_('settings.tags.error_create');
    } finally {
      creating = false;
    }
  }

  function setNewDraft(patch: Partial<Draft>): void {
    newDraft = { ...newDraft, ...patch };
  }

  async function save(tag: TagResponse): Promise<void> {
    const draft = drafts[tag.id];
    if (!draft) return;
    savingId = tag.id;
    error = '';
    try {
      await updateTag(tag.id, {
        name: draft.name,
        category: draft.category,
        icon: draft.icon.trim() ? draft.icon.trim() : null,
        color: draft.color,
        habit_type: draft.habit_type,
        target_frequency: draft.habit_type === 'none' ? null : draft.target_frequency,
      });
      await load();
      await refreshTags();
    } catch (err) {
      error = err instanceof Error ? err.message : $_('settings.tags.error_save');
    } finally {
      savingId = null;
    }
  }

  async function toggleHidden(tag: TagResponse): Promise<void> {
    savingId = tag.id;
    error = '';
    try {
      await updateTag(tag.id, { is_hidden: !tag.is_hidden });
      await load();
      await refreshTags();
    } catch (err) {
      error = err instanceof Error ? err.message : $_('settings.tags.error_save');
    } finally {
      savingId = null;
    }
  }

  async function resetOverride(tag: TagResponse): Promise<void> {
    savingId = tag.id;
    error = '';
    try {
      await deleteTag(tag.id);
      await load();
      await refreshTags();
    } catch (err) {
      error = err instanceof Error ? err.message : $_('settings.tags.error_reset');
    } finally {
      savingId = null;
    }
  }

  function sortTags(input: TagResponse[]): TagResponse[] {
    return [...input].sort((a, b) => a.name.localeCompare(b.name));
  }

  $: activeTags = sortTags(tags.filter((tag) => !tag.is_hidden));
  $: inactiveTags = sortTags(tags.filter((tag) => tag.is_hidden));
  $: tagGroups = [
    {
      id: 'active',
      heading: 'settings.tags.active_heading',
      body: 'settings.tags.active_body',
      empty: 'settings.tags.active_empty',
      tags: activeTags,
    },
    {
      id: 'inactive',
      heading: 'settings.tags.inactive_heading',
      body: 'settings.tags.inactive_body',
      empty: 'settings.tags.inactive_empty',
      tags: inactiveTags,
    },
  ];

  onMount(() => {
    void load();
  });
</script>

<svelte:head>
  <title>{$_('settings.tags.title')} - {$_('app.name')}</title>
</svelte:head>

<main class="tag-settings screen-stack">
  <ScreenHeader title={$_('settings.tags.title')} subtitle={$_('settings.tags.subtitle')} compact>
    <Button slot="actions" href="/settings" variant="ghost" size="sm">
      {$_('settings.tags.back_settings')}
    </Button>
  </ScreenHeader>

  {#if $auth.status !== 'authenticated'}
    <Panel variant="bordered">
      <p>{$_('settings.auth_required')}</p>
      <Button href="/auth/login" variant="primary" size="sm">{$_('auth.login.submit')}</Button>
    </Panel>
  {:else if loading}
    <DataState state="loading" loadingText={$_('tag.loading')} testId="tag-settings-loading" />
  {:else}
    {#if error}
      <InlineAlert variant="error" message={error} testId="tag-settings-error" />
    {/if}

    <section
      class="tag-settings__section tag-settings__create"
      data-testid="tag-settings-create"
      aria-labelledby="tag-settings-create-heading"
    >
      <div class="tag-settings__section-head">
        <h2 id="tag-settings-create-heading">{$_('settings.tags.create_heading')}</h2>
        <p>{$_('settings.tags.create_body')}</p>
      </div>
      <div class="tag-settings__create-form">
        <label>
          <span>{$_('settings.tags.name')}</span>
          <input
            class="input"
            value={newDraft.name}
            maxlength="64"
            on:input={(event) =>
              setNewDraft({ name: (event.currentTarget as HTMLInputElement).value })}
          />
        </label>
        <label>
          <span>{$_('settings.tags.category')}</span>
          <select
            class="input"
            value={newDraft.category}
            on:change={(event) =>
              setNewDraft({
                category: (event.currentTarget as HTMLSelectElement).value as TagCategory,
              })}
          >
            {#each TAG_CATEGORIES as category}
              <option value={category}>{$_(`tag.category.${category}`)}</option>
            {/each}
          </select>
        </label>
        <label>
          <span>{$_('settings.tags.icon')}</span>
          <input
            class="input"
            value={newDraft.icon}
            maxlength="32"
            on:input={(event) =>
              setNewDraft({ icon: (event.currentTarget as HTMLInputElement).value })}
          />
        </label>
        <label>
          <span>{$_('settings.tags.color')}</span>
          <input
            class="tag-settings__color"
            type="color"
            value={newDraft.color}
            on:input={(event) =>
              setNewDraft({ color: (event.currentTarget as HTMLInputElement).value })}
          />
        </label>
        <label>
          <span>{$_('settings.tags.habit_type')}</span>
          <select
            class="input"
            value={newDraft.habit_type}
            on:change={(event) =>
              setNewDraft({
                habit_type: (event.currentTarget as HTMLSelectElement).value as HabitType,
              })}
          >
            <option value="none">{$_('settings.tags.habit_none')}</option>
            <option value="build">{$_('settings.tags.habit_build')}</option>
            <option value="reduce">{$_('settings.tags.habit_reduce')}</option>
          </select>
        </label>
        <label>
          <span>{$_('settings.tags.target_frequency')}</span>
          <input
            class="input"
            type="number"
            min="1"
            max="7"
            value={newDraft.target_frequency}
            disabled={newDraft.habit_type === 'none'}
            on:input={(event) =>
              setNewDraft({
                target_frequency: Number((event.currentTarget as HTMLInputElement).value || 1),
              })}
          />
        </label>
        <button
          class="btn btn-sm btn--primary"
          type="button"
          disabled={creating ||
            !newDraft.name.trim() ||
            (newDraft.habit_type !== 'none' &&
              (newDraft.target_frequency < 1 || newDraft.target_frequency > 7))}
          on:click={createNewTag}
        >
          {creating ? $_('settings.tags.creating') : $_('settings.tags.create_submit')}
        </button>
      </div>
    </section>

    {#each tagGroups as group (group.id)}
      <section
        class="tag-settings__section"
        data-testid={`tag-settings-${group.id}`}
        aria-labelledby={`tag-settings-${group.id}`}
      >
        <div class="tag-settings__section-head">
          <h2 id={`tag-settings-${group.id}`}>{$_(group.heading)}</h2>
          <p>{$_(group.body)}</p>
        </div>

        {#if group.tags.length === 0}
          <p class="tag-settings__empty">{$_(group.empty)}</p>
        {:else}
          <div class="tag-settings__rows">
            {#each group.tags as tag (tag.id)}
              {@const draft = drafts[tag.id]}
              <article class="tag-settings__row" class:muted={tag.is_hidden}>
                <div class="tag-settings__identity">
                  <span
                    class="tag-settings__icon"
                    style={tag.color ? `--tag-color: ${tag.color}` : ''}
                  >
                    {#if draft?.icon}
                      <IconRender icon={draft.icon} size={ICON_SIZE_MD} />
                    {:else}
                      <span aria-hidden="true">#</span>
                    {/if}
                  </span>
                  <div>
                    <strong>{tag.name}</strong>
                    <span>
                      {$_(`tag.category.${tag.category}`)} ·
                      {tag.is_default
                        ? $_('settings.tags.default')
                        : isOverride(tag)
                          ? $_('settings.tags.override')
                          : $_('settings.tags.custom')}
                      {tag.is_hidden ? ` · ${$_('settings.tags.hidden')}` : ''}
                    </span>
                  </div>
                </div>

                {#if draft}
                  <div class="tag-settings__fields">
                    <label>
                      <span>{$_('settings.tags.name')}</span>
                      <input
                        class="input"
                        value={draft.name}
                        maxlength="64"
                        on:input={(event) =>
                          setDraft(tag.id, {
                            name: (event.currentTarget as HTMLInputElement).value,
                          })}
                      />
                    </label>
                    <label>
                      <span>{$_('settings.tags.category')}</span>
                      <select
                        class="input"
                        value={draft.category}
                        on:change={(event) =>
                          setDraft(tag.id, {
                            category: (event.currentTarget as HTMLSelectElement)
                              .value as TagCategory,
                          })}
                      >
                        {#each TAG_CATEGORIES as category}
                          <option value={category}>{$_(`tag.category.${category}`)}</option>
                        {/each}
                      </select>
                    </label>
                    <label>
                      <span>{$_('settings.tags.icon')}</span>
                      <input
                        class="input"
                        value={draft.icon}
                        maxlength="32"
                        on:input={(event) =>
                          setDraft(tag.id, {
                            icon: (event.currentTarget as HTMLInputElement).value,
                          })}
                      />
                    </label>
                    <label>
                      <span>{$_('settings.tags.color')}</span>
                      <input
                        class="tag-settings__color"
                        type="color"
                        value={draft.color}
                        on:input={(event) =>
                          setDraft(tag.id, {
                            color: (event.currentTarget as HTMLInputElement).value,
                          })}
                      />
                    </label>
                    <label>
                      <span>{$_('settings.tags.habit_type')}</span>
                      <select
                        class="input"
                        value={draft.habit_type}
                        on:change={(event) =>
                          setDraft(tag.id, {
                            habit_type: (event.currentTarget as HTMLSelectElement)
                              .value as HabitType,
                          })}
                      >
                        <option value="none">{$_('settings.tags.habit_none')}</option>
                        <option value="build">{$_('settings.tags.habit_build')}</option>
                        <option value="reduce">{$_('settings.tags.habit_reduce')}</option>
                      </select>
                    </label>
                    <label>
                      <span>{$_('settings.tags.target_frequency')}</span>
                      <input
                        class="input"
                        type="number"
                        min="1"
                        max="7"
                        value={draft.target_frequency}
                        disabled={draft.habit_type === 'none'}
                        on:input={(event) =>
                          setDraft(tag.id, {
                            target_frequency: Number(
                              (event.currentTarget as HTMLInputElement).value || 1
                            ),
                          })}
                      />
                    </label>
                  </div>
                {/if}

                <div class="tag-settings__actions">
                  <button
                    class="btn btn-sm btn--primary"
                    type="button"
                    disabled={savingId !== null ||
                      (draft?.habit_type !== 'none' &&
                        (draft?.target_frequency < 1 || draft?.target_frequency > 7))}
                    on:click={() => save(tag)}
                  >
                    {savingId === tag.id ? $_('settings.tags.saving') : $_('settings.tags.save')}
                  </button>
                  <button
                    class="btn btn-sm btn--secondary"
                    type="button"
                    disabled={savingId !== null}
                    on:click={() => toggleHidden(tag)}
                  >
                    {tag.is_hidden
                      ? $_('settings.tags.reactivate')
                      : $_('settings.tags.deactivate')}
                  </button>
                  {#if isOverride(tag)}
                    <button
                      class="btn btn-sm variant-ghost-surface"
                      type="button"
                      disabled={savingId !== null}
                      on:click={() => resetOverride(tag)}
                    >
                      {$_('settings.tags.reset')}
                    </button>
                  {/if}
                </div>
              </article>
            {/each}
          </div>
        {/if}
      </section>
    {/each}
  {/if}
</main>

<style>
  .tag-settings {
    width: min(100%, 62rem);
    margin: 0 auto;
  }

  .tag-settings__section {
    padding: 1rem;
    border-radius: var(--radius-md);
    background: var(--color-surface-chart-bg);
    border: 1px solid var(--color-border-chart);
  }

  .tag-settings__section-head {
    margin-bottom: 0.85rem;
  }

  .tag-settings__section-head h2 {
    margin: 0;
    font-size: var(--text-lg, 1.125rem);
  }

  .tag-settings__section-head p,
  .tag-settings__empty {
    margin: 0.2rem 0 0;
    opacity: 0.72;
    font-size: var(--text-sm, 0.875rem);
  }

  .tag-settings__rows {
    display: flex;
    flex-direction: column;
    gap: 0.75rem;
  }

  .tag-settings__row {
    display: grid;
    grid-template-columns: minmax(12rem, 16rem) 1fr auto;
    gap: 0.9rem;
    align-items: center;
    padding: 0.75rem 0;
    border-top: 1px solid var(--color-border);
  }

  .tag-settings__row:first-child {
    border-top: 0;
  }

  .tag-settings__row.muted {
    opacity: 0.62;
  }

  .tag-settings__identity {
    display: flex;
    align-items: center;
    gap: 0.65rem;
    min-width: 0;
  }

  .tag-settings__identity strong,
  .tag-settings__identity span {
    display: block;
    overflow: hidden;
    text-overflow: ellipsis;
    white-space: nowrap;
  }

  .tag-settings__identity span {
    font-size: var(--text-xs);
    opacity: 0.7;
  }

  .tag-settings__icon {
    width: 2rem;
    height: 2rem;
    border-radius: var(--radius-full);
    display: inline-flex;
    align-items: center;
    justify-content: center;
    color: var(--color-text-inverse);
    background: var(--tag-color, var(--color-primary));
    flex: 0 0 auto;
  }

  .tag-settings__fields {
    display: grid;
    grid-template-columns:
      minmax(8rem, 1.4fr) minmax(7rem, 1fr) minmax(6rem, 0.9fr) auto
      minmax(8rem, 1fr) minmax(5rem, 0.6fr);
    gap: 0.55rem;
    align-items: end;
  }

  .tag-settings__fields label {
    display: flex;
    flex-direction: column;
    gap: 0.25rem;
  }

  .tag-settings__fields label span {
    font-size: var(--text-2xs);
    opacity: 0.72;
  }

  .tag-settings__color {
    width: 2.6rem;
    min-height: 2.35rem;
    border: 1px solid var(--color-border);
    border-radius: var(--radius-md);
    background: var(--color-surface);
    color: var(--color-text);
    padding: 0.15rem;
  }

  .tag-settings__actions {
    display: flex;
    flex-wrap: wrap;
    justify-content: flex-end;
    gap: 0.45rem;
  }

  .tag-settings__create-form {
    display: grid;
    grid-template-columns:
      minmax(8rem, 1.4fr) minmax(7rem, 1fr) minmax(6rem, 0.9fr) auto
      minmax(8rem, 1fr) minmax(5rem, 0.6fr) auto;
    gap: 0.55rem;
    align-items: end;
  }

  .tag-settings__create-form label {
    display: flex;
    flex-direction: column;
    gap: 0.25rem;
  }

  .tag-settings__create-form label span {
    font-size: var(--text-2xs);
    opacity: 0.72;
  }

  @media (max-width: 1024px) {
    .tag-settings__row {
      grid-template-columns: 1fr;
      align-items: stretch;
    }

    .tag-settings__fields {
      grid-template-columns: 1fr 1fr;
    }

    .tag-settings__create-form {
      grid-template-columns: 1fr 1fr;
    }

    .tag-settings__actions {
      justify-content: flex-start;
    }
  }

  @media (max-width: 480px) {
    .tag-settings__fields {
      grid-template-columns: 1fr;
    }

    .tag-settings__create-form {
      grid-template-columns: 1fr;
    }
  }
</style>
