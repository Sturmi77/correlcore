<script lang="ts">
  import { onMount } from 'svelte';
  import { _ } from 'svelte-i18n';
  import { auth } from '$lib/stores/auth';
  import ThemeToggle from '$lib/components/common/ThemeToggle.svelte';
  import IconRender from '$lib/components/common/IconRender.svelte';
  import {
    TAG_CATEGORIES,
    deleteTag,
    listDefaultTags,
    listVisibleTags,
    updateTag,
    type TagCategory,
    type TagResponse,
  } from '$lib/api/tags';
  import { refreshTags } from '$lib/stores/tags';

  type Draft = {
    name: string;
    category: TagCategory;
    icon: string;
    color: string;
  };

  let loading = true;
  let savingId: string | null = null;
  let error = '';
  let tags: TagResponse[] = [];
  let defaultBySlug: Record<string, TagResponse> = {};
  let drafts: Record<string, Draft> = {};

  function draftFrom(tag: TagResponse): Draft {
    return {
      name: tag.name,
      category: tag.category,
      icon: tag.icon ?? '',
      color: tag.color ?? '#6356d9',
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

<main class="tag-settings">
  <header class="tag-settings__top">
    <a class="btn btn-sm variant-ghost-surface" href="/settings">{$_('nav.settings')}</a>
    <ThemeToggle testId="tag-settings-theme-toggle" />
  </header>

  <section class="tag-settings__intro">
    <h1>{$_('settings.tags.title')}</h1>
    <p>{$_('settings.tags.subtitle')}</p>
  </section>

  {#if $auth.status !== 'authenticated'}
    <section class="tag-settings__panel">
      <p>{$_('settings.auth_required')}</p>
      <a class="btn btn-sm variant-filled-primary" href="/auth/login">{$_('auth.login.submit')}</a>
    </section>
  {:else if loading}
    <section class="tag-settings__panel" aria-busy="true">
      <p>{$_('tag.loading')}</p>
    </section>
  {:else}
    {#if error}
      <p class="tag-settings__error" role="alert">{error}</p>
    {/if}

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
                      <IconRender icon={draft.icon} size={18} />
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
                  </div>
                {/if}

                <div class="tag-settings__actions">
                  <button
                    class="btn btn-sm variant-filled-primary"
                    type="button"
                    disabled={savingId !== null}
                    on:click={() => save(tag)}
                  >
                    {savingId === tag.id ? $_('settings.tags.saving') : $_('settings.tags.save')}
                  </button>
                  <button
                    class="btn btn-sm variant-soft-primary"
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
    padding: 1.25rem;
    display: flex;
    flex-direction: column;
    gap: 1rem;
  }

  .tag-settings__top {
    display: flex;
    align-items: center;
    justify-content: space-between;
  }

  .tag-settings__intro h1 {
    margin: 0;
    font-size: var(--text-2xl, 1.5rem);
  }

  .tag-settings__intro p {
    margin: 0.25rem 0 0;
    opacity: 0.72;
  }

  .tag-settings__panel,
  .tag-settings__section {
    padding: 1rem;
    border-radius: 0.5rem;
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
    font-size: 0.78rem;
    opacity: 0.7;
  }

  .tag-settings__icon {
    width: 2rem;
    height: 2rem;
    border-radius: 999px;
    display: inline-flex;
    align-items: center;
    justify-content: center;
    color: var(--color-text-inverse);
    background: var(--tag-color, var(--color-primary));
    flex: 0 0 auto;
  }

  .tag-settings__fields {
    display: grid;
    grid-template-columns: minmax(8rem, 1.4fr) minmax(7rem, 1fr) minmax(6rem, 0.9fr) auto;
    gap: 0.55rem;
    align-items: end;
  }

  .tag-settings__fields label {
    display: flex;
    flex-direction: column;
    gap: 0.25rem;
  }

  .tag-settings__fields label span {
    font-size: 0.72rem;
    opacity: 0.72;
  }

  .tag-settings__color {
    width: 2.6rem;
    min-height: 2.35rem;
    border: 1px solid var(--color-border);
    border-radius: 0.45rem;
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

  .tag-settings__error {
    margin: 0;
    color: var(--color-error);
  }

  @media (max-width: 860px) {
    .tag-settings__row {
      grid-template-columns: 1fr;
      align-items: stretch;
    }

    .tag-settings__fields {
      grid-template-columns: 1fr 1fr;
    }

    .tag-settings__actions {
      justify-content: flex-start;
    }
  }

  @media (max-width: 520px) {
    .tag-settings {
      padding: 1rem;
    }

    .tag-settings__fields {
      grid-template-columns: 1fr;
    }
  }
</style>
