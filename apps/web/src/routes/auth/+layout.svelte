<script lang="ts">
  import { _ } from 'svelte-i18n';
  import ThemeToggle from '$lib/components/common/ThemeToggle.svelte';
</script>

<!--
  Auth layout — Issue #40.
  Centered, minimal chrome (no main nav). Used for /auth/login,
  /auth/register, /auth/verify-email, /auth/check-email,
  /auth/resend-verification.
-->

<div class="auth-shell">
  <header class="auth-header">
    <a href="/" class="auth-brand" aria-label={$_('app.name')}>
      <svg
        viewBox="0 0 48 48"
        width="36"
        height="36"
        fill="none"
        xmlns="http://www.w3.org/2000/svg"
        aria-hidden="true"
      >
        <circle cx="24" cy="24" r="20" stroke="currentColor" stroke-width="3" opacity="0.25" />
        <path
          d="M24 4 A20 20 0 0 1 44 24"
          stroke="var(--color-primary)"
          stroke-width="3"
          stroke-linecap="round"
        />
        <path
          d="M16 26 Q24 34 32 26"
          stroke="var(--color-primary)"
          stroke-width="2.5"
          stroke-linecap="round"
          fill="none"
        />
        <circle cx="19" cy="20" r="1.5" fill="var(--color-primary)" />
        <circle cx="29" cy="20" r="1.5" fill="var(--color-primary)" />
      </svg>
      <span class="auth-brand-text">{$_('app.name')}</span>
    </a>

    <ThemeToggle withLabel={false} iconSize={16} testId="auth-theme-toggle" />
  </header>

  <main class="auth-main">
    <div class="auth-card">
      <slot />
    </div>

    <footer class="auth-footer">
      <p class="auth-disclaimer">{$_('disclaimer.medical')}</p>
    </footer>
  </main>
</div>

<style>
  .auth-shell {
    min-height: 100dvh;
    display: flex;
    flex-direction: column;
  }

  .auth-header {
    display: flex;
    align-items: center;
    justify-content: space-between;
    padding: var(--space-4) var(--space-6);
  }

  .auth-brand {
    display: inline-flex;
    align-items: center;
    gap: var(--space-2);
    text-decoration: none;
    color: inherit;
  }

  .auth-brand-text {
    font-size: var(--text-base);
    font-weight: 600;
  }

  .auth-main {
    flex: 1;
    display: flex;
    flex-direction: column;
    align-items: center;
    justify-content: center;
    padding: var(--space-6);
    gap: var(--space-8);
  }

  .auth-card {
    width: 100%;
    max-width: 420px;
    padding: var(--space-8) var(--space-6);
    border-radius: 16px;
    background: color-mix(in oklch, var(--color-surface) 82%, transparent);
    box-shadow:
      0 1px 3px rgb(0 0 0 / 0.06),
      0 8px 24px rgb(0 0 0 / 0.06);
    backdrop-filter: blur(8px);
  }

  .auth-footer {
    max-width: 420px;
    text-align: center;
  }

  .auth-disclaimer {
    font-size: var(--text-xs);
    opacity: 0.7;
    line-height: 1.5;
  }
</style>
