<script lang="ts">
  import { _ } from 'svelte-i18n';
  import { goto } from '$app/navigation';
  import { ApiError } from '$lib/api/client';
  import { register } from '$lib/api/auth';
  import PasswordStrength, { evaluatePassword } from '$lib/components/auth/PasswordStrength.svelte';

  let email = '';
  let password = '';
  let displayName = '';
  let busy = false;
  let errorKey: string | null = null;

  $: strength = evaluatePassword(password);
  $: canSubmit = !busy && email.includes('@') && strength.meetsRequirements;

  async function onSubmit() {
    if (!canSubmit) return;
    errorKey = null;
    busy = true;
    try {
      await register({
        email: email.trim().toLowerCase(),
        password,
        display_name: displayName.trim() || undefined,
      });
      // Pass email forward (URL-encoded) so the check-email page can show it.
      const target = `/auth/check-email?email=${encodeURIComponent(email.trim().toLowerCase())}`;
      await goto(target);
    } catch (err) {
      errorKey = mapError(err);
    } finally {
      busy = false;
    }
  }

  function mapError(err: unknown): string {
    if (err instanceof ApiError) {
      if (err.status === 409) return 'auth.register.error_duplicate';
      if (err.status === 422 || err.status === 400) return 'auth.register.error_weak_password';
      if (err.status === 429) return 'auth.login.error_rate_limit';
    }
    return 'error.generic';
  }
</script>

<svelte:head>
  <title>{$_('auth.register.title')} — {$_('app.name')}</title>
</svelte:head>

<header class="auth-page-header">
  <h1 class="auth-page-title">{$_('auth.register.title')}</h1>
  <p class="auth-page-subtitle">{$_('auth.register.subtitle')}</p>
</header>

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

  <label class="auth-field">
    <span class="auth-label">{$_('auth.common.display_name_label')}</span>
    <input
      type="text"
      class="input"
      autocomplete="nickname"
      bind:value={displayName}
      placeholder={$_('auth.common.display_name_placeholder')}
      disabled={busy}
    />
  </label>

  <label class="auth-field">
    <span class="auth-label">{$_('auth.common.password_label')}</span>
    <input
      type="password"
      class="input"
      autocomplete="new-password"
      required
      minlength="8"
      bind:value={password}
      placeholder={$_('auth.common.password_placeholder')}
      disabled={busy}
    />
    <PasswordStrength {password} />
    <span class="auth-hint">{$_('auth.register.password_hint')}</span>
  </label>

  {#if errorKey}
    <p class="auth-error" role="alert">{$_(errorKey)}</p>
  {/if}

  <button type="submit" class="btn variant-filled-primary auth-submit" disabled={!canSubmit}>
    {busy ? $_('auth.common.submit_busy') : $_('auth.register.submit')}
  </button>

  <p class="auth-privacy">{$_('auth.register.privacy_note')}</p>
</form>

<nav class="auth-links">
  <p>
    {$_('auth.register.have_account')}
    <a href="/auth/login">{$_('auth.register.login_link')}</a>
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

  .auth-hint {
    font-size: var(--text-xs);
    opacity: 0.7;
  }

  .auth-error {
    font-size: var(--text-sm);
    color: rgb(var(--color-error-500));
    background: rgb(var(--color-error-500) / 0.1);
    border-left: 3px solid rgb(var(--color-error-500));
    padding: var(--space-2) var(--space-3);
    border-radius: 6px;
  }

  .auth-submit {
    margin-top: var(--space-2);
  }

  .auth-privacy {
    font-size: var(--text-xs);
    opacity: 0.7;
    line-height: 1.5;
  }

  .auth-links {
    margin-top: var(--space-6);
    text-align: center;
    font-size: var(--text-sm);
  }

  .auth-links a {
    color: var(--color-ms-primary);
    text-decoration: none;
    font-weight: 500;
  }

  .auth-links a:hover {
    text-decoration: underline;
  }
</style>
