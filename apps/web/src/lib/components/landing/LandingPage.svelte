<script lang="ts">
  import { _ } from 'svelte-i18n';
  import Button from '$lib/components/common/Button.svelte';
  import CorrelCoreLogo from '$lib/components/common/CorrelCoreLogo.svelte';
  import LegalFooter from '$lib/components/common/LegalFooter.svelte';
  import ThemeToggle from '$lib/components/common/ThemeToggle.svelte';
  import { BRAND_MARK_HERO, BRAND_MARK_XL } from '$lib/constants/iconSizes';
  import { ANDROID_RELEASES_URL, DOCS_SITE_URL } from '$lib/constants/publicUrls';

  const featureKeys = ['privacy', 'insights', 'selfhost', 'daily'] as const;
</script>

<div class="landing" data-testid="marketing-landing">
  <header class="landing__header">
    <div class="landing__brand">
      <CorrelCoreLogo size={BRAND_MARK_XL} title={$_('app.name')} />
      <span class="landing__brand-name">{$_('app.name')}</span>
    </div>
    <ThemeToggle testId="landing-theme-toggle" />
  </header>

  <section class="landing__hero">
    <CorrelCoreLogo size={BRAND_MARK_HERO} title={$_('app.name')} />
    <span class="landing__badge" data-testid="landing-badge">{$_('landing.badge')}</span>
    <h1 class="landing__title">{$_('landing.hero_title')}</h1>
    <p class="landing__subtitle">{$_('landing.hero_subtitle')}</p>
    <div class="landing__cta">
      <Button href="/auth/login" variant="primary" size="lg" data-testid="landing-cta-login">
        {$_('landing.cta_login')}
      </Button>
      <Button
        href={ANDROID_RELEASES_URL}
        variant="secondary"
        size="lg"
        target="_blank"
        rel="noopener noreferrer"
        data-testid="landing-cta-apk"
      >
        {$_('landing.cta_apk')}
      </Button>
      <Button href="/auth/register" variant="ghost" size="lg" data-testid="landing-cta-register">
        {$_('landing.cta_register')}
      </Button>
    </div>
    <a
      class="landing__docs-link"
      href={DOCS_SITE_URL}
      target="_blank"
      rel="noopener noreferrer"
      data-testid="landing-docs-link"
    >
      {$_('landing.cta_docs')} →
    </a>
  </section>

  <section class="landing__features" aria-labelledby="landing-features-heading">
    <h2 id="landing-features-heading" class="landing__features-heading">
      {$_('landing.features_heading')}
    </h2>
    <ul class="landing__feature-grid">
      {#each featureKeys as key}
        <li class="landing__feature-card" data-testid={`landing-feature-${key}`}>
          <h3>{$_(`landing.features.${key}.title`)}</h3>
          <p>{$_(`landing.features.${key}.body`)}</p>
        </li>
      {/each}
    </ul>
  </section>

  <LegalFooter />
</div>

<style>
  .landing {
    display: flex;
    flex-direction: column;
    min-height: 100%;
    gap: var(--space-8);
    padding-bottom: var(--space-4);
  }

  .landing__header {
    display: flex;
    align-items: center;
    justify-content: space-between;
    padding: var(--space-4) 0;
  }

  .landing__brand {
    display: inline-flex;
    align-items: center;
    gap: var(--space-2);
  }

  .landing__brand-name {
    font-size: var(--text-lg);
    font-weight: 600;
  }

  .landing__hero {
    display: flex;
    flex-direction: column;
    align-items: center;
    gap: var(--space-4);
    text-align: center;
    padding: var(--space-4) 0 var(--space-6);
  }

  .landing__badge {
    display: inline-block;
    padding: var(--space-1) var(--space-3);
    border-radius: var(--radius-full, 999px);
    background: color-mix(in srgb, var(--color-primary) 12%, transparent);
    color: var(--color-primary);
    font-size: var(--text-xs);
    font-weight: 600;
    letter-spacing: 0.02em;
  }

  .landing__title {
    margin: 0;
    font-size: clamp(1.75rem, 5vw, 2.25rem);
    line-height: 1.15;
    max-width: 20ch;
  }

  .landing__subtitle {
    margin: 0;
    max-width: 36rem;
    color: var(--color-text-muted);
    font-size: var(--text-base);
    line-height: 1.6;
  }

  .landing__cta {
    display: flex;
    flex-wrap: wrap;
    justify-content: center;
    gap: var(--space-3);
    margin-top: var(--space-2);
  }

  .landing__docs-link {
    font-size: var(--text-sm);
    color: var(--color-text-muted);
    text-decoration: none;
  }

  .landing__docs-link:hover {
    color: var(--color-primary);
    text-decoration: underline;
  }

  .landing__features {
    display: flex;
    flex-direction: column;
    gap: var(--space-4);
  }

  .landing__features-heading {
    margin: 0;
    text-align: center;
    font-size: var(--text-lg);
  }

  .landing__feature-grid {
    display: grid;
    grid-template-columns: repeat(auto-fit, minmax(14rem, 1fr));
    gap: var(--space-4);
    list-style: none;
    margin: 0;
    padding: 0;
  }

  .landing__feature-card {
    padding: var(--space-4);
    border: 1px solid var(--color-border);
    border-radius: var(--radius-md);
    background: color-mix(in srgb, var(--color-surface) 92%, transparent);
  }

  .landing__feature-card h3 {
    margin: 0 0 var(--space-2);
    font-size: var(--text-base);
  }

  .landing__feature-card p {
    margin: 0;
    color: var(--color-text-muted);
    font-size: var(--text-sm);
    line-height: 1.55;
  }
</style>
