<script lang="ts">
  import { onMount } from 'svelte';
  import { _ } from 'svelte-i18n';
  import { goto } from '$app/navigation';
  import { resetPassword } from '$lib/api/auth';
  import { drainOfflineSyncForSessionChange } from '$lib/offline/session';
  import { setUser } from '$lib/stores/auth';
  import PasswordStrength from '$lib/components/auth/PasswordStrength.svelte';
  import { evaluatePassword } from '$lib/utils/passwordStrength';
  import { mapApiError, type ApiErrorMap } from '$lib/utils/error';

  type Phase = 'idle' | 'busy' | 'error' | 'missing-token';

  let token: string | null = null;
  let phase: Phase = 'idle';
  let password = '';
  let passwordConfirm = '';
  let errorKey: string | null = null;

  const ERROR_MAP: ApiErrorMap = {
    400: 'auth.reset.error_invalid',
    422: 'auth.reset.error_weak_password',
    429: 'auth.login.error_rate_limit',
  };

  $: strength = evaluatePassword(password);
  $: passwordsMatch = password === passwordConfirm;
  $: canSubmit =
    phase !== 'busy' &&
    Boolean(token) &&
    strength.meetsRequirements &&
    passwordsMatch &&
    passwordConfirm.length > 0;

  onMount(() => {
    const url = new URL(window.location.href);
    token = url.searchParams.get('token');
    if (token === null) {
      phase = 'missing-token';
      return;
    }
    url.searchParams.delete('token');
    history.replaceState(history.state, '', `${url.pathname}${url.search}`);
  });

  async function onSubmit() {
    if (!token || !canSubmit) return;
    errorKey = null;
    phase = 'busy';
    try {
      await drainOfflineSyncForSessionChange();
      const session = await resetPassword({ token, password });
      await setUser(session.user);
      await goto('/', { replaceState: true });
    } catch (err) {
      errorKey = mapApiError(err, ERROR_MAP);
      phase = 'idle';
    }
  }
</script>

<svelte:head>
  <title>{$_('auth.reset.title')} — {$_('app.name')}</title>
</svelte:head>

{#if phase === 'missing-token'}
  <header class="auth-page-header">
    <h1 class="auth-page-title">{$_('auth.reset.error_title')}</h1>
  </header>
  <p class="auth-body" role="alert">{$_('auth.reset.missing_token')}</p>
  <nav class="auth-links">
    <a href="/auth/forgot-password" class="btn btn--primary auth-submit">
      {$_('auth.reset.go_to_forgot')}
    </a>
  </nav>
{:else}
  <header class="auth-page-header">
    <h1 class="auth-page-title">{$_('auth.reset.title')}</h1>
  </header>
  <p class="auth-body">{$_('auth.reset.body')}</p>

  <form class="auth-form" on:submit|preventDefault={onSubmit} novalidate>
    <label class="auth-field">
      <span class="auth-label">{$_('auth.common.password_label')}</span>
      <input
        type="password"
        class="input"
        autocomplete="new-password"
        required
        bind:value={password}
        placeholder={$_('auth.common.password_placeholder')}
        disabled={phase === 'busy'}
      />
      <PasswordStrength {password} />
    </label>

    <label class="auth-field">
      <span class="auth-label">{$_('auth.reset.password_confirm')}</span>
      <input
        type="password"
        class="input"
        autocomplete="new-password"
        required
        bind:value={passwordConfirm}
        placeholder={$_('auth.reset.password_confirm_placeholder')}
        disabled={phase === 'busy'}
      />
      {#if passwordConfirm && !passwordsMatch}
        <p class="auth-error" role="alert">{$_('auth.reset.password_mismatch')}</p>
      {/if}
    </label>

    {#if errorKey}
      <p class="auth-error" role="alert">{$_(errorKey)}</p>
    {/if}

    <button type="submit" class="btn btn--primary auth-submit" disabled={!canSubmit}>
      {phase === 'busy' ? $_('auth.common.submit_busy') : $_('auth.reset.submit')}
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
