<script lang="ts">
  import { _ } from 'svelte-i18n';
  import { page } from '$app/stores';
  import { ApiError } from '$lib/api/client';
  import { verifyEmail } from '$lib/api/auth';

  type Phase = 'idle' | 'busy' | 'success' | 'error' | 'missing-token';

  $: token = $page.url.searchParams.get('token');
  let phase: Phase = 'idle';

  // Distinguish "no token in URL" from "token present, awaiting click".
  // We deliberately do NOT auto-submit — link previews / safe-link rewriters
  // (Outlook, antivirus, mail-scanner bots) follow the URL on hover/receive
  // and would burn the single-use token before the user clicks. The user
  // must explicitly press the button (active-consent pattern, DSGVO-friendly).
  $: if (token === null && phase === 'idle') {
    phase = 'missing-token';
  }

  async function onConfirm() {
    if (!token || phase === 'busy' || phase === 'success') return;
    phase = 'busy';
    try {
      await verifyEmail(token);
      phase = 'success';
    } catch (err) {
      // Backend returns a generic 400 for invalid/expired/used tokens
      // (anti-enumeration). We map both ApiError and NetworkError to "error".
      if (err instanceof ApiError) {
        phase = 'error';
      } else {
        phase = 'error';
      }
    }
  }
</script>

<svelte:head>
  <title>{$_('auth.verify.title')} — {$_('app.name')}</title>
</svelte:head>

{#if phase === 'success'}
  <header class="auth-page-header">
    <div class="auth-icon auth-icon-success" aria-hidden="true">
      <svg viewBox="0 0 24 24" width="48" height="48" fill="none" stroke="currentColor" stroke-width="2">
        <circle cx="12" cy="12" r="10" />
        <path d="M8 12.5l3 3 5-6" stroke-linecap="round" stroke-linejoin="round" />
      </svg>
    </div>
    <h1 class="auth-page-title">{$_('auth.verify.success_title')}</h1>
  </header>
  <p class="auth-body">{$_('auth.verify.success_body')}</p>
  <nav class="auth-links">
    <a href="/auth/login" class="btn variant-filled-primary auth-submit">
      {$_('auth.verify.go_to_login')}
    </a>
  </nav>
{:else if phase === 'error'}
  <header class="auth-page-header">
    <div class="auth-icon auth-icon-error" aria-hidden="true">
      <svg viewBox="0 0 24 24" width="48" height="48" fill="none" stroke="currentColor" stroke-width="2">
        <circle cx="12" cy="12" r="10" />
        <path d="M12 8v4M12 16h.01" stroke-linecap="round" />
      </svg>
    </div>
    <h1 class="auth-page-title">{$_('auth.verify.error_title')}</h1>
  </header>
  <p class="auth-body">{$_('auth.verify.error_body')}</p>
  <nav class="auth-links">
    <a href="/auth/resend-verification" class="btn variant-filled-primary auth-submit">
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
    <a href="/auth/resend-verification" class="btn variant-filled-primary auth-submit">
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
    class="btn variant-filled-primary auth-submit"
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
    color: var(--color-ms-primary);
  }

  .auth-icon-success {
    color: rgb(var(--color-success-500));
  }

  .auth-icon-error {
    color: rgb(var(--color-error-500));
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
    color: var(--color-ms-primary);
    text-decoration: none;
    font-weight: 500;
  }

  .auth-links a:hover {
    text-decoration: underline;
  }
</style>
