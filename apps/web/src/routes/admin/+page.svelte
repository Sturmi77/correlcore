<script lang="ts">
  import { goto } from '$app/navigation';
  import { onMount } from 'svelte';
  import { _, locale } from 'svelte-i18n';
  import { auth } from '$lib/stores/auth';
  import { ApiError } from '$lib/api/client';
  import {
    deleteAdminUser,
    fetchAdminUser,
    fetchAdminUsers,
    setAdminUserActive,
    triggerAdminPasswordReset,
    type AdminUserDetail,
    type AdminUserListItem,
  } from '$lib/api/admin';

  const PAGE_SIZE = 50;

  let items: AdminUserListItem[] = [];
  let total = 0;
  let offset = 0;
  let searchInput = '';
  let appliedQuery = '';
  let activeFilter: 'all' | 'active' | 'disabled' = 'all';

  let loading = true;
  let forbidden = false;
  let error = '';
  let rowBusy = ''; // `${id}:${action}`
  let toast = '';
  let toastTimer: ReturnType<typeof setTimeout> | null = null;

  // Delete confirmation (typed-email guard for an irreversible action).
  let deleteTarget: AdminUserListItem | null = null;
  let deleteDetail: AdminUserDetail | null = null;
  let deleteConfirmEmail = '';
  let deleteBusy = false;
  let deleteError = '';

  $: selfId = $auth.status === 'authenticated' ? $auth.user.id : null;
  $: activeParam = activeFilter === 'all' ? undefined : activeFilter === 'active';
  $: hasPrev = offset > 0;
  $: hasNext = offset + items.length < total;
  $: rangeFrom = total === 0 ? 0 : offset + 1;
  $: rangeTo = offset + items.length;

  function showToast(msg: string): void {
    toast = msg;
    if (toastTimer) clearTimeout(toastTimer);
    toastTimer = setTimeout(() => (toast = ''), 3000);
  }

  function formatWhen(iso: string): string {
    try {
      return new Date(iso).toLocaleDateString($locale ?? undefined);
    } catch {
      return iso;
    }
  }

  function handleApiError(err: unknown, fallbackKey: string): void {
    if (err instanceof ApiError && err.status === 403) {
      forbidden = true;
      return;
    }
    if (err instanceof ApiError && err.status === 401) {
      void goto('/auth/login?next=/admin');
      return;
    }
    error = err instanceof Error ? err.message : $_(fallbackKey);
  }

  async function load(): Promise<void> {
    loading = true;
    error = '';
    try {
      const res = await fetchAdminUsers({
        query: appliedQuery || undefined,
        active: activeParam,
        limit: PAGE_SIZE,
        offset,
      });
      items = res.items;
      total = res.total;
    } catch (err) {
      handleApiError(err, 'admin.error_load');
    } finally {
      loading = false;
    }
  }

  function applySearch(): void {
    appliedQuery = searchInput.trim();
    offset = 0;
    void load();
  }

  function changeFilter(next: 'all' | 'active' | 'disabled'): void {
    if (next === activeFilter) return;
    activeFilter = next;
    offset = 0;
    void load();
  }

  function prevPage(): void {
    if (!hasPrev) return;
    offset = Math.max(0, offset - PAGE_SIZE);
    void load();
  }

  function nextPage(): void {
    if (!hasNext) return;
    offset += PAGE_SIZE;
    void load();
  }

  async function toggleActive(user: AdminUserListItem): Promise<void> {
    const key = `${user.id}:active`;
    rowBusy = key;
    error = '';
    try {
      const updated = await setAdminUserActive(user.id, !user.is_active);
      items = items.map((u) => (u.id === user.id ? { ...u, is_active: updated.is_active } : u));
      showToast(
        updated.is_active
          ? $_('admin.toast.enabled', { values: { email: user.email } })
          : $_('admin.toast.disabled', { values: { email: user.email } })
      );
    } catch (err) {
      handleApiError(err, 'admin.error_action');
    } finally {
      rowBusy = '';
    }
  }

  async function sendPasswordReset(user: AdminUserListItem): Promise<void> {
    const key = `${user.id}:reset`;
    rowBusy = key;
    error = '';
    try {
      await triggerAdminPasswordReset(user.id);
      showToast($_('admin.toast.reset_sent', { values: { email: user.email } }));
    } catch (err) {
      if (err instanceof ApiError && err.status === 409) {
        showToast($_('admin.toast.reset_conflict', { values: { email: user.email } }));
      } else {
        handleApiError(err, 'admin.error_action');
      }
    } finally {
      rowBusy = '';
    }
  }

  async function openDeleteDialog(user: AdminUserListItem): Promise<void> {
    deleteTarget = user;
    deleteDetail = null;
    deleteConfirmEmail = '';
    deleteError = '';
    try {
      deleteDetail = await fetchAdminUser(user.id);
    } catch {
      // Detail (entry_count) is a nice-to-have; the dialog still works without it.
    }
  }

  function closeDeleteDialog(): void {
    if (deleteBusy) return;
    deleteTarget = null;
    deleteDetail = null;
    deleteConfirmEmail = '';
    deleteError = '';
  }

  async function confirmDelete(): Promise<void> {
    if (!deleteTarget) return;
    if (deleteConfirmEmail.trim().toLowerCase() !== deleteTarget.email.toLowerCase()) return;
    deleteBusy = true;
    deleteError = '';
    const email = deleteTarget.email;
    try {
      await deleteAdminUser(deleteTarget.id);
      items = items.filter((u) => u.id !== deleteTarget?.id);
      total = Math.max(0, total - 1);
      deleteTarget = null;
      deleteDetail = null;
      deleteConfirmEmail = '';
      showToast($_('admin.toast.deleted', { values: { email } }));
    } catch (err) {
      if (err instanceof ApiError && err.status === 403) {
        deleteError = $_('admin.delete.forbidden');
      } else {
        deleteError = err instanceof Error ? err.message : $_('admin.error_action');
      }
    } finally {
      deleteBusy = false;
    }
  }

  onMount(() => {
    // Guard: the layout hydrates auth at boot, so by navigation time the store
    // is resolved. Anonymous → login; authenticated non-admin → forbidden state
    // (also enforced server-side, which sets `forbidden` on any 403).
    const state = $auth;
    if (state.status === 'anonymous') {
      void goto('/auth/login?next=/admin');
      return;
    }
    if (state.status === 'authenticated' && state.user.is_admin !== true) {
      forbidden = true;
      loading = false;
      return;
    }
    void load();
  });
</script>

<svelte:head>
  <title>{$_('admin.title')} - {$_('app.name')}</title>
</svelte:head>

<main class="admin screen-stack">
  <header class="admin__top">
    <a class="btn btn-sm variant-ghost-surface" href="/settings">{$_('nav.settings')}</a>
  </header>

  <section class="admin__intro">
    <p class="admin__eyebrow">{$_('admin.eyebrow')}</p>
    <h1>{$_('admin.title')}</h1>
    <p>{$_('admin.subtitle')}</p>
  </section>

  {#if forbidden}
    <section class="admin__panel admin__panel--notice" role="status" data-testid="admin-forbidden">
      <p>
        <strong>{$_('admin.forbidden_title')}</strong><br />
        {$_('admin.forbidden_body')}
      </p>
      <a class="btn btn-sm variant-ghost-surface" href="/settings">{$_('admin.back_settings')}</a>
    </section>
  {:else}
    <section class="admin__panel">
      <form
        class="admin__controls"
        on:submit|preventDefault={applySearch}
        data-testid="admin-search-form"
      >
        <input
          class="admin__search"
          type="search"
          placeholder={$_('admin.search_placeholder')}
          aria-label={$_('admin.search_placeholder')}
          bind:value={searchInput}
          data-testid="admin-search-input"
        />
        <button class="btn btn-sm variant-filled-primary" type="submit">
          {$_('admin.search_action')}
        </button>
        <div class="admin__filter" role="group" aria-label={$_('admin.filter.label')}>
          {#each [{ id: 'all', label: $_('admin.filter.all') }, { id: 'active', label: $_('admin.filter.active') }, { id: 'disabled', label: $_('admin.filter.disabled') }] as opt}
            <button
              type="button"
              class="admin__chip"
              class:admin__chip--on={activeFilter === opt.id}
              aria-pressed={activeFilter === opt.id}
              data-testid={`admin-filter-${opt.id}`}
              on:click={() => changeFilter(opt.id as 'all' | 'active' | 'disabled')}
            >
              {opt.label}
            </button>
          {/each}
        </div>
      </form>

      {#if error}
        <p class="admin__error" role="alert">{error}</p>
      {/if}

      {#if loading}
        <p class="admin__muted">{$_('admin.loading')}</p>
      {:else if items.length === 0}
        <p class="admin__muted" data-testid="admin-empty">{$_('admin.empty')}</p>
      {:else}
        <div class="admin__table-wrap">
          <table class="admin__table" data-testid="admin-user-table">
            <thead>
              <tr>
                <th>{$_('admin.col.user')}</th>
                <th>{$_('admin.col.status')}</th>
                <th>{$_('admin.col.created')}</th>
                <th class="admin__col-actions">{$_('admin.col.actions')}</th>
              </tr>
            </thead>
            <tbody>
              {#each items as user (user.id)}
                <tr data-testid={`admin-user-row-${user.id}`}>
                  <td>
                    <div class="admin__user">
                      <span class="admin__email">{user.email}</span>
                      {#if user.display_name}
                        <span class="admin__name">{user.display_name}</span>
                      {/if}
                    </div>
                  </td>
                  <td>
                    <div class="admin__badges">
                      {#if user.id === selfId}
                        <span class="admin__badge admin__badge--self">{$_('admin.badge.you')}</span>
                      {/if}
                      {#if user.is_admin}
                        <span class="admin__badge admin__badge--admin"
                          >{$_('admin.badge.admin')}</span
                        >
                      {/if}
                      <span
                        class="admin__badge"
                        class:admin__badge--ok={user.is_active}
                        class:admin__badge--off={!user.is_active}
                      >
                        {user.is_active ? $_('admin.badge.active') : $_('admin.badge.disabled')}
                      </span>
                      {#if !user.is_verified}
                        <span class="admin__badge admin__badge--warn">
                          {$_('admin.badge.unverified')}
                        </span>
                      {/if}
                    </div>
                  </td>
                  <td class="admin__muted">{formatWhen(user.created_at)}</td>
                  <td>
                    <div class="admin__row-actions">
                      <button
                        type="button"
                        class="btn btn-sm variant-ghost-surface"
                        disabled={!!rowBusy}
                        on:click={() => void sendPasswordReset(user)}
                        data-testid={`admin-reset-${user.id}`}
                      >
                        {rowBusy === `${user.id}:reset`
                          ? $_('admin.busy')
                          : $_('admin.action.reset')}
                      </button>
                      <button
                        type="button"
                        class="btn btn-sm variant-ghost-surface"
                        disabled={!!rowBusy || user.id === selfId}
                        title={user.id === selfId ? $_('admin.self_hint') : ''}
                        on:click={() => void toggleActive(user)}
                        data-testid={`admin-toggle-${user.id}`}
                      >
                        {rowBusy === `${user.id}:active`
                          ? $_('admin.busy')
                          : user.is_active
                            ? $_('admin.action.disable')
                            : $_('admin.action.enable')}
                      </button>
                      <button
                        type="button"
                        class="btn btn-sm admin__danger"
                        disabled={!!rowBusy || user.id === selfId}
                        title={user.id === selfId ? $_('admin.self_hint') : ''}
                        on:click={() => void openDeleteDialog(user)}
                        data-testid={`admin-delete-${user.id}`}
                      >
                        {$_('admin.action.delete')}
                      </button>
                    </div>
                  </td>
                </tr>
              {/each}
            </tbody>
          </table>
        </div>

        <div class="admin__pager">
          <span class="admin__muted" data-testid="admin-range">
            {$_('admin.range', { values: { from: rangeFrom, to: rangeTo, total } })}
          </span>
          <div class="admin__pager-buttons">
            <button
              type="button"
              class="btn btn-sm variant-ghost-surface"
              disabled={!hasPrev || loading}
              on:click={prevPage}
            >
              {$_('admin.prev')}
            </button>
            <button
              type="button"
              class="btn btn-sm variant-ghost-surface"
              disabled={!hasNext || loading}
              on:click={nextPage}
            >
              {$_('admin.next')}
            </button>
          </div>
        </div>
      {/if}
    </section>
  {/if}
</main>

{#if toast}
  <div class="admin__toast" role="status" aria-live="polite" data-testid="admin-toast">{toast}</div>
{/if}

{#if deleteTarget}
  <div
    class="admin__modal-backdrop"
    role="presentation"
    data-testid="admin-delete-backdrop"
    on:click={closeDeleteDialog}
  >
    <dialog
      open
      class="admin__modal"
      aria-modal="true"
      aria-labelledby="admin-delete-title"
      data-testid="admin-delete-dialog"
      on:click|stopPropagation
    >
      <h2 id="admin-delete-title">{$_('admin.delete.title')}</h2>
      <p class="admin__muted">
        {$_('admin.delete.body', {
          values: {
            email: deleteTarget.email,
            count: deleteDetail?.entry_count ?? 0,
          },
        })}
      </p>
      <p class="admin__delete-warn">{$_('admin.delete.irreversible')}</p>
      <label class="admin__field">
        <span>{$_('admin.delete.confirm_label', { values: { email: deleteTarget.email } })}</span>
        <input
          type="text"
          autocomplete="off"
          bind:value={deleteConfirmEmail}
          data-testid="admin-delete-confirm-input"
        />
      </label>
      {#if deleteError}
        <p class="admin__error" role="alert">{deleteError}</p>
      {/if}
      <div class="admin__modal-actions">
        <button
          type="button"
          class="btn btn-sm variant-ghost-surface"
          on:click={closeDeleteDialog}
          disabled={deleteBusy}
        >
          {$_('admin.delete.cancel')}
        </button>
        <button
          type="button"
          class="btn btn-sm admin__danger"
          disabled={deleteBusy ||
            deleteConfirmEmail.trim().toLowerCase() !== deleteTarget.email.toLowerCase()}
          on:click={() => void confirmDelete()}
          data-testid="admin-delete-confirm"
        >
          {deleteBusy ? $_('admin.busy') : $_('admin.delete.confirm')}
        </button>
      </div>
    </dialog>
  </div>
{/if}

<style>
  .admin {
    width: min(100%, 64rem);
    margin: 0 auto;
  }

  .admin__top {
    display: flex;
    align-items: center;
    justify-content: space-between;
    gap: 1rem;
  }

  .admin__intro {
    display: flex;
    flex-direction: column;
    gap: 0.35rem;
  }

  .admin__intro h1 {
    margin: 0;
    font-size: var(--text-2xl, 1.5rem);
  }

  .admin__intro p,
  .admin__muted {
    margin: 0;
    color: var(--color-text-muted);
  }

  .admin__eyebrow {
    font-size: var(--text-xs);
    text-transform: uppercase;
    font-weight: 700;
    color: var(--color-primary);
  }

  .admin__panel {
    padding: 1rem;
    display: flex;
    flex-direction: column;
    gap: 1rem;
    border-radius: var(--radius-md);
    background: var(--color-surface-chart-bg);
    border: 1px solid var(--color-border-chart);
  }

  .admin__panel--notice {
    border-color: color-mix(in oklch, var(--color-warning) 40%, transparent);
    background: color-mix(in oklch, var(--color-warning) 12%, var(--color-surface));
    color: var(--color-warning);
  }

  .admin__controls {
    display: flex;
    flex-wrap: wrap;
    align-items: center;
    gap: 0.6rem;
  }

  .admin__search {
    flex: 1 1 16rem;
    min-height: 2.5rem;
    padding: 0 var(--space-3);
    border: 1px solid var(--color-border);
    border-radius: var(--radius-sm);
    background: var(--color-surface);
    color: var(--color-text);
  }

  .admin__filter {
    display: inline-flex;
    gap: 0.35rem;
  }

  .admin__chip {
    padding: 0.4rem 0.7rem;
    border-radius: var(--radius-sm);
    border: 1px solid var(--color-border);
    background: var(--color-surface);
    color: var(--color-text-muted);
    font-size: var(--text-sm);
    font-weight: 600;
    cursor: pointer;
  }

  .admin__chip--on {
    border-color: var(--color-primary);
    color: var(--color-primary);
    background: color-mix(in srgb, var(--color-primary-soft) 28%, var(--color-surface));
  }

  .admin__table-wrap {
    overflow-x: auto;
  }

  .admin__table {
    width: 100%;
    border-collapse: collapse;
    font-size: var(--text-sm);
  }

  .admin__table th,
  .admin__table td {
    text-align: left;
    padding: 0.55rem 0.5rem;
    border-bottom: 1px solid var(--color-border);
    vertical-align: top;
  }

  .admin__col-actions {
    text-align: right;
  }

  .admin__user {
    display: flex;
    flex-direction: column;
    gap: 0.15rem;
    min-width: 0;
  }

  .admin__email {
    font-weight: 600;
    overflow-wrap: anywhere;
  }

  .admin__name {
    color: var(--color-text-muted);
  }

  .admin__badges {
    display: flex;
    flex-wrap: wrap;
    gap: 0.3rem;
  }

  .admin__badge {
    padding: 0.15rem 0.45rem;
    border-radius: var(--radius-sm);
    font-size: var(--text-xs);
    font-weight: 700;
    background: var(--color-surface);
    border: 1px solid var(--color-border);
    color: var(--color-text-muted);
  }

  .admin__badge--ok {
    color: var(--color-success);
    background: color-mix(in oklch, var(--color-success) 14%, var(--color-surface));
    border-color: transparent;
  }

  .admin__badge--off {
    color: var(--color-error);
    background: var(--color-error-highlight);
    border-color: transparent;
  }

  .admin__badge--admin {
    color: var(--color-primary);
    border-color: var(--color-primary);
  }

  .admin__badge--warn {
    color: var(--color-warning);
    border-color: color-mix(in oklch, var(--color-warning) 45%, transparent);
  }

  .admin__badge--self {
    color: var(--color-text);
    border-style: dashed;
  }

  .admin__row-actions {
    display: flex;
    flex-wrap: wrap;
    gap: 0.4rem;
    justify-content: flex-end;
  }

  .admin__danger {
    border: 1px solid color-mix(in oklch, var(--color-error) 45%, transparent);
    background: transparent;
    color: var(--color-error);
  }

  .admin__danger:disabled {
    opacity: 0.45;
  }

  .admin__pager {
    display: flex;
    align-items: center;
    justify-content: space-between;
    gap: 1rem;
    flex-wrap: wrap;
  }

  .admin__pager-buttons {
    display: flex;
    gap: 0.5rem;
  }

  .admin__error {
    margin: 0;
    color: var(--color-error);
  }

  .admin__toast {
    position: fixed;
    bottom: var(--space-6, 1.5rem);
    left: 50%;
    transform: translateX(-50%);
    background: var(--color-surface-2);
    border: 1px solid var(--color-border);
    border-radius: var(--radius-md);
    padding: var(--space-3) var(--space-5);
    font-size: var(--text-sm);
    color: var(--color-text);
    box-shadow: var(--shadow-lg);
    z-index: 300;
    max-width: min(92vw, 30rem);
  }

  .admin__modal-backdrop {
    position: fixed;
    inset: 0;
    z-index: 500;
    display: grid;
    place-items: center;
    padding: var(--space-4);
    background: color-mix(in srgb, var(--color-surface) 62%, transparent);
  }

  .admin__modal {
    width: min(100%, 30rem);
    display: flex;
    flex-direction: column;
    gap: 0.85rem;
    padding: var(--space-4);
    border: 1px solid var(--color-border);
    border-radius: var(--radius-md);
    background: var(--color-surface);
    box-shadow: var(--shadow-lg);
  }

  .admin__modal h2 {
    margin: 0;
    font-size: var(--text-lg);
  }

  .admin__delete-warn {
    margin: 0;
    color: var(--color-error);
    font-weight: 600;
    font-size: var(--text-sm);
  }

  .admin__field {
    display: flex;
    flex-direction: column;
    gap: var(--space-2);
    font-size: var(--text-sm);
    color: var(--color-text-muted);
  }

  .admin__field input {
    min-height: 2.75rem;
    border: 1px solid var(--color-border);
    border-radius: var(--radius-sm);
    padding: 0 var(--space-3);
    background: var(--color-surface);
    color: var(--color-text);
  }

  .admin__modal-actions {
    display: flex;
    justify-content: flex-end;
    gap: 0.5rem;
  }
</style>
