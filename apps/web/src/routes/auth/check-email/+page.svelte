<script lang="ts">
  import { _ } from 'svelte-i18n';
  import { page } from '$app/stores';

  $: email = $page.url.searchParams.get('email') ?? '';
</script>

<svelte:head>
  <title>{$_('auth.check_email.title')} — {$_('app.name')}</title>
</svelte:head>

<header class="auth-page-header">
  <div class="auth-icon" aria-hidden="true">
    <svg
      viewBox="0 0 24 24"
      width="48"
      height="48"
      fill="none"
      stroke="currentColor"
      stroke-width="1.5"
    >
      <rect x="3" y="5" width="18" height="14" rx="2" />
      <path d="M3 7l9 6 9-6" />
    </svg>
  </div>
  <h1 class="auth-page-title">{$_('auth.check_email.title')}</h1>
</header>

<p class="auth-body">
  {#if email}
    {$_('auth.check_email.body', { values: { email } })}
  {:else}
    {$_('auth.check_email.body', {
      values: { email: $_('auth.common.email_label').toLowerCase() },
    })}
  {/if}
</p>

<ul class="auth-hints">
  <li>{$_('auth.check_email.ttl_hint')}</li>
  <li>{$_('auth.check_email.spam_hint')}</li>
</ul>

<nav class="auth-links">
  <p>
    <a href="/auth/resend-verification">{$_('auth.check_email.resend_link')}</a>
  </p>
  <p>
    <a href="/auth/login">{$_('auth.common.back_to_login')}</a>
  </p>
</nav>

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

  .auth-page-title {
    font-size: var(--text-lg);
    font-weight: 600;
  }

  .auth-body {
    font-size: var(--text-sm);
    line-height: 1.6;
    text-align: center;
    margin-bottom: var(--space-4);
  }

  .auth-hints {
    list-style: none;
    padding: 0;
    margin: 0 0 var(--space-6) 0;
    display: flex;
    flex-direction: column;
    gap: var(--space-2);
    font-size: var(--text-xs);
    opacity: 0.75;
    text-align: center;
  }

  .auth-links {
    margin-top: var(--space-4);
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
