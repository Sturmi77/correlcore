<script lang="ts">
  import { _ } from 'svelte-i18n';
  import { DOCS_SITE_URL, REPO_URL } from '$lib/constants/publicUrls';
</script>

<footer class="legal-footer" data-testid="legal-footer">
  <nav class="legal-footer__nav" aria-label={$_('landing.footer.nav_label')}>
    <a href="/privacy" data-testid="legal-footer-privacy">{$_('landing.footer.privacy')}</a>
    <a href="/impressum" data-testid="legal-footer-impressum">{$_('landing.footer.impressum')}</a>
    <a href={DOCS_SITE_URL} target="_blank" rel="noopener noreferrer" data-testid="legal-footer-docs">
      {$_('landing.footer.docs')}
    </a>
    <a href={REPO_URL} target="_blank" rel="noopener noreferrer" data-testid="legal-footer-source">
      {$_('landing.footer.source')}
    </a>
  </nav>
  <p class="legal-footer__disclaimer">{$_('disclaimer.medical')}</p>
</footer>

<style>
  .legal-footer {
    display: flex;
    flex-direction: column;
    align-items: center;
    gap: var(--space-3);
    text-align: center;
    padding: var(--space-6) var(--space-4);
  }

  .legal-footer__nav {
    display: flex;
    flex-wrap: wrap;
    justify-content: center;
    gap: var(--space-3) var(--space-5);
    font-size: var(--text-sm);
  }

  .legal-footer__nav a {
    color: var(--color-text-muted);
    text-decoration: none;
  }

  .legal-footer__nav a:hover {
    color: var(--color-primary);
    text-decoration: underline;
  }

  .legal-footer__disclaimer {
    margin: 0;
    max-width: 36rem;
    font-size: var(--text-xs);
    color: var(--color-text-muted);
    line-height: 1.5;
  }
</style>
