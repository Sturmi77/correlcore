<script lang="ts">
  import { _ } from 'svelte-i18n';
  import { theme } from '$lib/stores/theme';

  $: currentTheme = $theme;
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
          stroke="#01696f"
          stroke-width="3"
          stroke-linecap="round"
        />
        <path
          d="M16 26 Q24 34 32 26"
          stroke="#01696f"
          stroke-width="2.5"
          stroke-linecap="round"
          fill="none"
        />
        <circle cx="19" cy="20" r="1.5" fill="#01696f" />
        <circle cx="29" cy="20" r="1.5" fill="#01696f" />
      </svg>
      <span class="auth-brand-text">{$_('app.name')}</span>
    </a>

    <button
      type="button"
      class="btn btn-sm variant-ghost-surface"
      on:click={() => theme.toggle()}
      aria-label={currentTheme === 'dark' ? $_('theme.toggle_light') : $_('theme.toggle_dark')}
    >
      {#if currentTheme === 'dark'}
        <svg
          width="16"
          height="16"
          viewBox="0 0 24 24"
          fill="none"
          stroke="currentColor"
          stroke-width="2"
          aria-hidden="true"
        >
          <circle cx="12" cy="12" r="5" />
          <path
            d="M12 1v2M12 21v2M4.22 4.22l1.42 1.42M18.36 18.36l1.42 1.42M1 12h2M21 12h2M4.22 19.78l1.42-1.42M18.36 5.64l1.42-1.42"
          />
        </svg>
      {:else}
        <svg
          width="16"
          height="16"
          viewBox="0 0 24 24"
          fill="none"
          stroke="currentColor"
          stroke-width="2"
          aria-hidden="true"
        >
          <path d="M21 12.79A9 9 0 1 1 11.21 3 7 7 0 0 0 21 12.79z" />
        </svg>
      {/if}
    </button>
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
    background: rgb(var(--color-surface-100) / 0.6);
    box-shadow: 0 1px 3px rgb(0 0 0 / 0.06), 0 8px 24px rgb(0 0 0 / 0.06);
    backdrop-filter: blur(8px);
  }

  :global(html.dark) .auth-card {
    background: rgb(var(--color-surface-800) / 0.55);
    box-shadow: 0 1px 3px rgb(0 0 0 / 0.4), 0 12px 32px rgb(0 0 0 / 0.3);
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
