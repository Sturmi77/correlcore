<script lang="ts">
  import { _ } from 'svelte-i18n';
  import { requestPasswordReset } from '$lib/api/auth';
  import { mapApiError, type ApiErrorMap } from '$lib/utils/error';

  let email = '';
  let busy = false;
  let success = false;
  let errorKey: string | null = null;

  const ERROR_MAP: ApiErrorMap = {
    429: 'auth.forgot.error_rate_limit',
  };

  async function onSubmit() {
    if (busy) return;
    errorKey = null;
    success = false;
    busy = true;
    try {
      await requestPasswordReset(email.trim().toLowerCase());
      success = true;
    } catch (err) {
      errorKey = mapApiError(err, ERROR_MAP);
    } finally {
      busy = false;
    }
  }
</script>

<svelte:head>
  <title>{$_('auth.forgot.title')} — {$_('app.name')}</title>
</svelte:head>

<header class="auth-page-header">
  <h1 class="auth-page-title">{$_('auth.forgot.title')}</h1>
</header>

<p class="auth-body">{$_('auth.forgot.body')}</p>

{#if success}
  <p class="auth-success" role="status">{$_('auth.forgot.success')}</p>
  <nav class="auth-links">
    <a href="/auth/login" class="btn btn--primary auth-submit">
      {$_('auth.common.back_to_login')}
    </a>
  </nav>
{:else}
  <form class="auth-form" on:submit|preventDefault={onSubmit} novalidate>
    <label class="auth-field">
      <span class="auth-label">{$_('auth.common.email_label')}</span>
      <input
        type="email"
        class="input"
        autocomplete="email"
        inputmode="email"
        required
        bind:value={email}
        placeholder={$_('auth.common.email_placeholder')}
        disabled={busy}
      />
    </label>

    {#if errorKey}
      <p class="auth-error" role="alert">{$_(errorKey)}</p>
    {/if}

    <button type="submit" class="btn btn--primary auth-submit" disabled={busy || !email}>
      {busy ? $_('auth.common.submit_busy') : $_('auth.forgot.submit')}
    </button>
  </form>

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

  .auth-success {
    font-size: var(--text-sm);
    color: var(--color-success);
    background: var(--color-success-highlight);
    border-left: 3px solid var(--color-success);
    padding: var(--space-2) var(--space-3);
    border-radius: 6px;
    margin-bottom: var(--space-4);
  }

  .auth-submit {
    width: 100%;
    margin-top: var(--space-2);
  }

  .auth-links {
    margin-top: var(--space-6);
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
