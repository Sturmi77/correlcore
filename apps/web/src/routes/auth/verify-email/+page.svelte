<script lang="ts">
  import { onMount } from 'svelte';
  import { _ } from 'svelte-i18n';
  import { goto } from '$app/navigation';
  import { SessionPersistenceError } from '$lib/api/client';
  import { verifyEmail } from '$lib/api/auth';
  import { drainOfflineSyncForSessionChange } from '$lib/offline/session';
  import { setUser } from '$lib/stores/auth';
  import { OPEN_ENTRY_HOME_PATH } from '$lib/navigation/openEntry';

  type Phase = 'idle' | 'busy' | 'success' | 'error' | 'session-error' | 'missing-token';

  let token: string | null = null;
  let phase: Phase = 'idle';

  onMount(() => {
    const url = new URL(window.location.href);
    token = url.searchParams.get('token');
    if (token === null) {
      phase = 'missing-token';
      return;
    }
    // Strip the single-use token from the address bar so it does not linger
    // in browser history after the user lands from the email link.
    url.searchParams.delete('token');
    history.replaceState(history.state, '', `${url.pathname}${url.search}`);
  });

  async function onConfirm() {
    if (!token || phase === 'busy' || phase === 'success') return;
    phase = 'busy';
    try {
      await drainOfflineSyncForSessionChange();
      const session = await verifyEmail(token);
      await setUser(session.user);
      await goto(OPEN_ENTRY_HOME_PATH);
    } catch (err) {
      // Token is single-use: a cookie-persistence failure after 200 must not
      // look like "invalid/expired link" (resend would not help — account is
      // already verified). Route users to sign-in instead.
      if (err instanceof SessionPersistenceError) {
        phase = 'session-error';
        return;
      }
      // Backend returns a generic 400 for invalid/expired/used tokens
      // (anti-enumeration). ApiError and NetworkError both surface as
      // a single "error" phase — the UI never differentiates.
      phase = 'error';
    }
  }
</script>

<svelte:head>
  <title>{$_('auth.verify.title')} — {$_('app.name')}</title>
</svelte:head>

{#if phase === 'success'}
  <header class="auth-page-header">
    <div class="auth-icon auth-icon-success" aria-hidden="true">
      <svg
        viewBox="0 0 24 24"
        width="48"
        height="48"
        fill="none"
        stroke="currentColor"
        stroke-width="2"
      >
        <circle cx="12" cy="12" r="10" />
        <path d="M8 12.5l3 3 5-6" stroke-linecap="round" stroke-linejoin="round" />
      </svg>
    </div>
    <h1 class="auth-page-title">{$_('auth.verify.success_title')}</h1>
  </header>
  <p class="auth-body">{$_('auth.verify.success_body')}</p>
{:else if phase === 'session-error'}
  <header class="auth-page-header">
    <div class="auth-icon auth-icon-error" aria-hidden="true">
      <svg
        viewBox="0 0 24 24"
        width="48"
        height="48"
        fill="none"
        stroke="currentColor"
        stroke-width="2"
      >
        <circle cx="12" cy="12" r="10" />
        <path d="M12 8v4M12 16h.01" stroke-linecap="round" />
      </svg>
    </div>
    <h1 class="auth-page-title">{$_('auth.verify.session_error_title')}</h1>
  </header>
  <p class="auth-body" role="alert">{$_('auth.verify.session_error_body')}</p>
  <nav class="auth-links">
    <a href="/auth/login" class="btn btn--primary auth-submit">
      {$_('auth.verify.go_to_login')}
    </a>
  </nav>
{:else if phase === 'error'}
  <header class="auth-page-header">
    <div class="auth-icon auth-icon-error" aria-hidden="true">
      <svg
        viewBox="0 0 24 24"
        width="48"
        height="48"
        fill="none"
        stroke="currentColor"
        stroke-width="2"
      >
        <circle cx="12" cy="12" r="10" />
        <path d="M12 8v4M12 16h.01" stroke-linecap="round" />
      </svg>
    </div>
    <h1 class="auth-page-title">{$_('auth.verify.error_title')}</h1>
  </header>
  <p class="auth-body">{$_('auth.verify.error_body')}</p>
  <nav class="auth-links">
    <a href="/auth/resend-verification" class="btn btn--primary auth-submit">
      {$_('auth.verify.go_to_resend')}
    </a>
    <p>
      <a href="/auth/login">{$_('auth.common.back_to_login')}</a>
    </p>
  </nav>
{:else if phase === 'missing-token'}
  <header class="auth-page-header">
    <h1 class="auth-page-title">{$_('auth.verify.error_title')}</h1>
  </header>
  <p class="auth-body" role="alert">{$_('auth.verify.missing_token')}</p>
  <nav class="auth-links">
    <a href="/auth/resend-verification" class="btn btn--primary auth-submit">
      {$_('auth.verify.go_to_resend')}
    </a>
  </nav>
{:else}
  <header class="auth-page-header">
    <h1 class="auth-page-title">{$_('auth.verify.title')}</h1>
  </header>
  <p class="auth-body">{$_('auth.verify.body')}</p>
  <button
    type="button"
    class="btn btn--primary auth-submit"
    on:click={onConfirm}
    disabled={phase === 'busy'}
  >
    {phase === 'busy' ? $_('auth.common.submit_busy') : $_('auth.verify.submit')}
  </button>
  <nav class="auth-links">
    <p>
      <a href="/auth/login">{$_('auth.common.back_to_login')}</a>
    </p>
  </nav>
{/if}

<style>
  .auth-page-header {
    text-align: center;
    margin-bottom: var(--space-6);
    display: flex;
    flex-direction: column;
    align-items: center;
    gap: var(--space-3);
  }

  .auth-icon {
    color: var(--color-primary);
  }

  .auth-icon-success {
    color: var(--color-success);
  }

  .auth-icon-error {
    color: var(--color-error);
  }

  .auth-page-title {
    font-size: var(--text-lg);
    font-weight: 600;
  }

  .auth-body {
    font-size: var(--text-sm);
    line-height: 1.6;
    text-align: center;
    margin-bottom: var(--space-6);
  }

  .auth-submit {
    width: 100%;
    margin-top: var(--space-2);
  }

  .auth-links {
    margin-top: var(--space-4);
    display: flex;
    flex-direction: column;
    gap: var(--space-3);
    text-align: center;
    font-size: var(--text-sm);
  }

  .auth-links a {
    color: var(--color-primary);
    text-decoration: none;
    font-weight: 500;
  }

  .auth-links a:hover {
    text-decoration: underline;
  }
</style>
