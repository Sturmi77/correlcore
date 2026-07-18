<script lang="ts">
  import { _ } from 'svelte-i18n';
  import CorrelCoreLogo from '$lib/components/common/CorrelCoreLogo.svelte';
  import ThemeToggle from '$lib/components/common/ThemeToggle.svelte';
  import { BRAND_MARK_LG } from '$lib/constants/iconSizes';
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
      <CorrelCoreLogo size={BRAND_MARK_LG} title="" />
      <span class="auth-brand-text">{$_('app.name')}</span>
    </a>

    <ThemeToggle withLabel={false} iconSize={16} testId="auth-theme-toggle" />
  </header>

  <main class="auth-main">
    <div class="auth-card">
      <slot />
    </div>

    <footer class="auth-footer">
      <nav class="auth-legal" aria-label={$_('landing.footer.nav_label')}>
        <a href="/privacy" data-testid="auth-footer-privacy">{$_('landing.footer.privacy')}</a>
        <a href="/impressum" data-testid="auth-footer-impressum">{$_('landing.footer.impressum')}</a
        >
      </nav>
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
    padding: max(var(--space-4), env(safe-area-inset-top, 0px)) var(--space-6) var(--space-4);
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
    max-width: 360px;
    padding: var(--space-8) var(--space-6);
    border-radius: var(--radius-xl);
    background: color-mix(in oklch, var(--color-surface) 82%, transparent);
    box-shadow: var(--shadow-md);
    backdrop-filter: blur(8px);
  }

  .auth-footer {
    max-width: 360px;
    text-align: center;
  }

  .auth-legal {
    display: flex;
    justify-content: center;
    gap: var(--space-4);
    margin-bottom: var(--space-3);
    font-size: var(--text-xs);
  }

  .auth-legal a {
    color: var(--color-text-muted);
    text-decoration: none;
  }

  .auth-legal a:hover {
    color: var(--color-primary);
    text-decoration: underline;
  }

  .auth-disclaimer {
    font-size: var(--text-xs);
    opacity: 0.7;
    line-height: 1.5;
  }
</style>
