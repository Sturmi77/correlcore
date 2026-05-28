<script lang="ts">
  import { _ } from 'svelte-i18n';
  import { goto } from '$app/navigation';
  import { page } from '$app/stores';
  import { login } from '$lib/stores/auth';
  import { mapApiError, type ApiErrorMap } from '$lib/utils/error';

  let email = '';
  let password = '';
  let busy = false;
  let errorKey: string | null = null;

  const ERROR_MAP: ApiErrorMap = {
    401: 'auth.login.error_invalid',
    403: 'auth.login.error_unverified',
    429: 'auth.login.error_rate_limit',
  };

  /** Whitelist next-target to in-app paths to prevent open-redirect. */
  function safeNext(raw: string | null): string {
    if (!raw) return '/';
    if (!raw.startsWith('/') || raw.startsWith('//')) return '/';
    if (raw.startsWith('/auth/')) return '/';
    return raw;
  }

  async function onSubmit() {
    if (busy) return;
    errorKey = null;
    busy = true;
    try {
      await login({ email: email.trim().toLowerCase(), password });
      const target = safeNext($page.url.searchParams.get('next'));
      await goto(target, { replaceState: true });
    } catch (err) {
      errorKey = mapApiError(err, ERROR_MAP);
    } finally {
      busy = false;
    }
  }
</script>

<svelte:head>
  <title>{$_('auth.login.title')} — {$_('app.name')}</title>
</svelte:head>

<header class="auth-page-header">
  <h1 class="auth-page-title">{$_('auth.login.title')}</h1>
  <p class="auth-page-subtitle">{$_('auth.login.subtitle')}</p>
</header>

<form class="auth-form" on:submit|preventDefault={onSubmit} novalidate>
  <label class="auth-field">
    <span class="auth-label">{$_('auth.common.email_label')}</span>
    <input
      type="email"
      class="input"
      autocomplete="username"
      inputmode="email"
      required
      bind:value={email}
      placeholder={$_('auth.common.email_placeholder')}
      disabled={busy}
    />
  </label>

  <label class="auth-field">
    <span class="auth-label">{$_('auth.common.password_label')}</span>
    <input
      type="password"
      class="input"
      autocomplete="current-password"
      required
      bind:value={password}
      placeholder={$_('auth.common.password_placeholder')}
      disabled={busy}
    />
  </label>

  {#if errorKey}
    <p class="auth-error" role="alert">{$_(errorKey)}</p>
  {/if}

  <button
    type="submit"
    class="btn variant-filled-primary auth-submit"
    disabled={busy || !email || !password}
  >
    {busy ? $_('auth.common.submit_busy') : $_('auth.login.submit')}
  </button>
</form>

<nav class="auth-links">
  <p>
    {$_('auth.login.no_account')}
    <a href="/auth/register">{$_('auth.login.register_link')}</a>
  </p>
  <p>
    <a href="/auth/resend-verification">{$_('auth.check_email.resend_link')}</a>
  </p>
</nav>

<style>
  .auth-page-header {
    text-align: center;
    margin-bottom: var(--space-6);
  }

  .auth-page-title {
    font-size: var(--text-lg);
    font-weight: 600;
    margin-bottom: var(--space-2);
  }

  .auth-page-subtitle {
    font-size: var(--text-sm);
    opacity: 0.75;
  }

  .auth-form {
    display: flex;
    flex-direction: column;
    gap: var(--space-4);
  }

  .auth-field {
    display: flex;
    flex-direction: column;
    gap: var(--space-2);
  }

  .auth-label {
    font-size: var(--text-sm);
    font-weight: 500;
  }

  .auth-error {
    font-size: var(--text-sm);
    color: var(--color-error);
    background: var(--color-error-highlight);
    border-left: 3px solid var(--color-error);
    padding: var(--space-2) var(--space-3);
    border-radius: 6px;
  }

  .auth-submit {
    margin-top: var(--space-2);
  }

  .auth-links {
    margin-top: var(--space-6);
    display: flex;
    flex-direction: column;
    gap: var(--space-2);
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
