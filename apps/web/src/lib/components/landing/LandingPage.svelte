<script lang="ts">
  import { _, locale } from 'svelte-i18n';
  import Button from '$lib/components/common/Button.svelte';
  import CorrelCoreLogo from '$lib/components/common/CorrelCoreLogo.svelte';
  import LegalFooter from '$lib/components/common/LegalFooter.svelte';
  import ThemeToggle from '$lib/components/common/ThemeToggle.svelte';
  import InsightCard from '$lib/components/insights/InsightCard.svelte';
  import LagCorrelationHeatmap from '$lib/components/insights/LagCorrelationHeatmap.svelte';
  import HomeWeekdayOverview from '$lib/components/home/HomeWeekdayOverview.svelte';
  import BrowserFrameMock from '$lib/components/landing/BrowserFrameMock.svelte';
  import LandingCheckinMock from '$lib/components/landing/LandingCheckinMock.svelte';
  import { buildLandingDemo } from '$lib/components/landing/landingDemoData';
  import { BRAND_MARK_MD } from '$lib/constants/iconSizes';
  import {
    ANDROID_RELEASES_URL,
    OBTAINIUM_URL,
    DOCS_SITE_URL,
    INSTALL_DOCS_URL,
    USER_GUIDE_URL,
    REPO_URL,
    LICENSE_URL,
    SECURITY_URL,
  } from '$lib/constants/publicUrls';
  import { setAppLocale, type AppLocale } from '$lib/i18n';
  import { instanceConfig } from '$lib/stores/instanceConfig';
  import {
    MATURITY_INTRO_PHASES,
    MATURITY_INTRO_THUMBS,
  } from '$lib/utils/maturityExpectationIntro';

  const faqKeys = ['1', '2', '3', '4'] as const;
  const opsKeys = ['runtime', 'data', 'edge', 'hardware', 'updates'] as const;

  $: demo = buildLandingDemo($_);

  // Hosted vs self-host is a runtime fact (GET /api/v1/instance). Primary CTA
  // is account signup when this instance accepts it; otherwise the self-host
  // install guide. Login stays in every mode.
  $: showRegisterCta = $instanceConfig
    ? $instanceConfig.mode === 'hosted' || $instanceConfig.registration_enabled
    : false;
  $: hostedMode = $instanceConfig?.mode === 'hosted';
  $: badgeVersion = $instanceConfig?.version ?? $_('app.version');
  $: badgeText = hostedMode
    ? $_('landing.badge_hosted', { values: { version: badgeVersion } })
    : $_('landing.badge', { values: { version: badgeVersion } });

  // I5: each trust claim links to the document that backs it.
  const trustItems = [
    { key: 'privacy', href: '/privacy', tone: 'mood', external: false },
    { key: 'notelemetry', href: SECURITY_URL, tone: 'energy', external: true },
    { key: 'offline', href: USER_GUIDE_URL, tone: 'sleep', external: true },
    { key: 'license', href: LICENSE_URL, tone: 'gold', external: true },
  ] as const;

  // Four maturity phases — same thumbs as onboarding expectation intro.
  const journeyStages = MATURITY_INTRO_PHASES.map((phase, index) => ({
    key: phase,
    tier: phase === 'early_patterns' ? 'early' : phase,
    phase,
    index,
  }));

  function reveal(node: HTMLElement) {
    const prefersReduced =
      typeof window !== 'undefined' &&
      typeof window.matchMedia === 'function' &&
      window.matchMedia('(prefers-reduced-motion: reduce)').matches;

    if (prefersReduced || typeof IntersectionObserver === 'undefined') {
      node.classList.add('is-visible');
      return {};
    }

    const observer = new IntersectionObserver(
      (entries) => {
        for (const entry of entries) {
          if (entry.isIntersecting) {
            node.classList.add('is-visible');
            observer.unobserve(node);
          }
        }
      },
      { threshold: 0.12, rootMargin: '0px 0px -8% 0px' }
    );
    observer.observe(node);
    return {
      destroy() {
        observer.disconnect();
      },
    };
  }

  $: nextLocale = (($locale ?? 'de').split('-')[0] === 'en' ? 'de' : 'en') as AppLocale;

  function toggleLocale(): void {
    setAppLocale(nextLocale);
  }
</script>

<div class="landing" data-testid="marketing-landing">
  <header class="landing__header">
    <div class="landing__brand">
      <CorrelCoreLogo size={BRAND_MARK_MD} title={$_('app.name')} />
      <span class="landing__brand-name">
        correl<span class="landing__brand-accent">core</span>
      </span>
    </div>
    <div class="landing__header-actions">
      <ThemeToggle withLabel={false} testId="landing-theme-toggle" />
      <button
        type="button"
        class="btn btn-sm variant-ghost-surface"
        data-testid="landing-lang-toggle"
        aria-label={$_('landing.lang_toggle', { values: { locale: nextLocale.toUpperCase() } })}
        on:click={toggleLocale}
      >
        {nextLocale.toUpperCase()}
      </button>
      <Button href="/auth/login" variant="ghost" size="sm" data-testid="landing-cta-login">
        {$_('landing.cta_login')}
      </Button>
      {#if showRegisterCta}
        <Button
          href="/auth/register"
          variant="primary"
          size="sm"
          data-testid="landing-cta-register"
        >
          {$_('landing.cta_register')}
        </Button>
      {:else}
        <Button
          href={INSTALL_DOCS_URL}
          variant="primary"
          size="sm"
          target="_blank"
          rel="noopener noreferrer"
          data-testid="landing-cta-selfhost"
        >
          {$_('landing.cta_selfhost')}
        </Button>
      {/if}
    </div>
  </header>

  <section class="landing__hero">
    <span class="landing__hero-aurora" aria-hidden="true"></span>
    <div class="landing__hero-copy">
      <span class="landing__badge" data-testid="landing-badge">
        {badgeText}
      </span>
      <h1 class="landing__title">{$_('landing.hero_title')}</h1>
      <p class="landing__subtitle">{$_('landing.hero_subtitle')}</p>
      <p class="landing__hero-micro">{$_('landing.hero_micro')}</p>
      <div class="landing__hero-actions">
        {#if showRegisterCta}
          <Button href="/auth/register" variant="primary" data-testid="landing-hero-register">
            {$_('landing.cta_register')}
          </Button>
        {:else}
          <Button
            href={INSTALL_DOCS_URL}
            variant="primary"
            target="_blank"
            rel="noopener noreferrer"
            data-testid="landing-hero-selfhost"
          >
            {$_('landing.cta_selfhost')}
          </Button>
        {/if}
        <Button href="/auth/login" variant="secondary" data-testid="landing-hero-login">
          {$_('landing.cta_login')}
        </Button>
      </div>
      <ul class="landing__trust" data-testid="landing-trust">
        {#each trustItems as item (item.key)}
          <li class="landing__trust-item" data-tone={item.tone}>
            <span class="landing__trust-dot" aria-hidden="true"></span>
            <a
              href={item.href}
              class="landing__trust-link"
              data-testid={`landing-trust-${item.key}`}
              {...item.external ? { target: '_blank', rel: 'noopener noreferrer' } : {}}
            >
              {$_(`landing.trust.${item.key}`)}
            </a>
          </li>
        {/each}
      </ul>
    </div>
    <div class="landing__hero-visual">
      <BrowserFrameMock address="app.correlcore.example/entries/today">
        <div class="landing__shot" inert aria-hidden="true">
          <LandingCheckinMock />
        </div>
      </BrowserFrameMock>
      <p class="landing__shot-caption">
        <span class="landing__example">{$_('landing.example_data')}</span>
        {$_('landing.checkin.caption')}
      </p>
    </div>
  </section>

  <section
    class="landing__paths landing__reveal"
    use:reveal
    aria-labelledby="landing-paths-heading"
    data-testid="landing-paths"
  >
    <h2 id="landing-paths-heading" class="landing__section-heading">
      {$_('landing.paths_heading')}
    </h2>
    <div class="landing__path-grid">
      <article
        class="landing__path"
        class:is-primary={showRegisterCta}
        data-testid="landing-path-try"
      >
        <h3>{$_('landing.paths.try.title')}</h3>
        <p>
          {showRegisterCta ? $_('landing.paths.try.body') : $_('landing.paths.try_closed.body')}
        </p>
        {#if showRegisterCta}
          <Button href="/auth/register" variant="primary" size="sm">
            {$_('landing.paths.try.cta')}
          </Button>
        {:else}
          <Button href="/auth/login" variant="secondary" size="sm">
            {$_('landing.paths.try_closed.cta')}
          </Button>
        {/if}
      </article>
      <article
        class="landing__path"
        class:is-primary={!showRegisterCta}
        data-testid="landing-path-host"
      >
        <h3>{$_('landing.paths.host.title')}</h3>
        <p>{$_('landing.paths.host.body')}</p>
        <Button
          href={INSTALL_DOCS_URL}
          variant={showRegisterCta ? 'secondary' : 'primary'}
          size="sm"
          target="_blank"
          rel="noopener noreferrer"
        >
          {$_('landing.paths.host.cta')}
        </Button>
      </article>
    </div>
  </section>

  <section
    class="landing__journey landing__reveal"
    use:reveal
    aria-labelledby="landing-journey-heading"
    data-testid="landing-journey"
  >
    <h2 id="landing-journey-heading" class="landing__section-heading">
      {$_('landing.journey_heading')}
    </h2>
    <p class="landing__journey-lead">{$_('landing.journey_body')}</p>
    <ol class="landing__journey-track">
      {#each journeyStages as stage (stage.key)}
        <li class="landing__journey-stage" data-tier={stage.tier} data-phase={stage.phase}>
          <img
            class="landing__journey-thumb"
            src={MATURITY_INTRO_THUMBS[stage.phase]}
            alt={$_('onboarding.maturity_intro.thumb_alt', { values: { n: stage.index + 1 } })}
            width="96"
            height="96"
            loading="lazy"
            decoding="async"
          />
          <span class="landing__journey-range">{$_(`maturity.${stage.phase}.range`)}</span>
          <span class="landing__journey-label">{$_(`maturity.${stage.phase}.label`)}</span>
          <p class="landing__journey-expectation">
            {$_(`onboarding.maturity_intro.${stage.phase}.expectation`)}
          </p>
          <p class="landing__journey-not-yet">
            {$_(`onboarding.maturity_intro.${stage.phase}.not_yet`)}
          </p>
        </li>
      {/each}
    </ol>
  </section>

  <section
    class="landing__previews landing__reveal"
    use:reveal
    aria-labelledby="landing-previews-heading"
  >
    <h2 id="landing-previews-heading" class="landing__section-heading">
      {$_('landing.previews_heading')}
    </h2>
    <div class="landing__preview-grid">
      <figure class="landing__preview">
        <BrowserFrameMock address="app.correlcore.example/insights">
          <div class="landing__shot" inert aria-hidden="true">
            <InsightCard insight={demo.featuredInsight} maturity={demo.maturity} featured />
          </div>
        </BrowserFrameMock>
        <figcaption>
          <span class="landing__example">{$_('landing.example_data')}</span>
          {$_('landing.preview_card')}
        </figcaption>
      </figure>
      <figure class="landing__preview">
        <BrowserFrameMock address="app.correlcore.example/insights">
          <div class="landing__shot" inert aria-hidden="true">
            <LagCorrelationHeatmap insights={demo.lagInsights} />
          </div>
        </BrowserFrameMock>
        <figcaption>
          <span class="landing__example">{$_('landing.example_data')}</span>
          {$_('landing.preview_lag')}
        </figcaption>
      </figure>
    </div>
  </section>

  <section
    class="landing__weekday landing__reveal"
    use:reveal
    aria-labelledby="landing-weekday-heading"
    data-testid="landing-weekday"
  >
    <h2 id="landing-weekday-heading" class="landing__section-heading">
      {$_('landing.weekday_heading')}
    </h2>
    <figure class="landing__weekday-figure">
      <BrowserFrameMock address="app.correlcore.example/home">
        <div class="landing__shot" inert aria-hidden="true">
          <HomeWeekdayOverview
            insights={[demo.weekdayInsight]}
            weekdayInsight={demo.weekdayInsight}
            weekdaySummary={demo.weekdaySummary}
          />
        </div>
      </BrowserFrameMock>
      <figcaption>
        <span class="landing__example">{$_('landing.example_data')}</span>
        {$_('landing.weekday_caption')}
        <ul class="landing__weekday-legend" data-testid="landing-weekday-legend">
          <li data-tone="best">{$_('landing.weekday_legend_best')}</li>
          <li data-tone="worst">{$_('landing.weekday_legend_worst')}</li>
        </ul>
      </figcaption>
    </figure>
  </section>

  <section
    class="landing__android landing__reveal"
    use:reveal
    aria-labelledby="landing-android-heading"
  >
    <h2 id="landing-android-heading" class="landing__section-heading">
      {$_('landing.android_heading')}
    </h2>
    <p class="landing__android-body">{$_('landing.android_body')}</p>
    <div class="landing__android-actions">
      <Button
        href={ANDROID_RELEASES_URL}
        variant="secondary"
        target="_blank"
        rel="noopener noreferrer"
        data-testid="landing-android-download"
      >
        {$_('landing.android_download')}
      </Button>
      <Button
        href={OBTAINIUM_URL}
        variant="ghost"
        target="_blank"
        rel="noopener noreferrer"
        data-testid="landing-android-obtainium"
      >
        {$_('landing.android_obtainium')}
      </Button>
    </div>
    <p class="landing__android-note">{$_('landing.android_sha256')}</p>
  </section>

  <section
    class="landing__selfhost landing__reveal"
    use:reveal
    aria-labelledby="landing-selfhost-heading"
  >
    <div>
      <h2 id="landing-selfhost-heading">{$_('landing.selfhost_title')}</h2>
      <p>{$_('landing.selfhost_body')}</p>
      <ul class="landing__ops" data-testid="landing-ops">
        {#each opsKeys as key}
          <li>{$_(`landing.selfhost_ops.${key}`)}</li>
        {/each}
      </ul>
      <pre class="landing__docker" data-testid="landing-docker-cmd">{$_(
          'landing.docker_label'
        )}</pre>
      <div class="landing__selfhost-actions">
        <Button
          href={INSTALL_DOCS_URL}
          variant="primary"
          size="sm"
          target="_blank"
          rel="noopener noreferrer"
          data-testid="landing-install-link"
        >
          {$_('landing.paths.host.cta')}
        </Button>
        <Button
          href={REPO_URL}
          variant="secondary"
          size="sm"
          target="_blank"
          rel="noopener noreferrer"
          data-testid="landing-github-link"
        >
          {$_('landing.tech_github')}
        </Button>
      </div>
    </div>
  </section>

  <section class="landing__faq landing__reveal" use:reveal aria-labelledby="landing-faq-heading">
    <h2 id="landing-faq-heading" class="landing__section-heading">{$_('landing.faq_heading')}</h2>
    <div class="landing__faq-list">
      {#each faqKeys as key}
        <details class="landing__faq-item" data-testid={`landing-faq-${key}`}>
          <summary>{$_(`landing.faq.${key}.q`)}</summary>
          <p>
            {#if key === '2'}
              {hostedMode ? $_('landing.faq.2.a_hosted') : $_('landing.faq.2.a_selfhost')}
            {:else}
              {$_(`landing.faq.${key}.a`)}
            {/if}
          </p>
        </details>
      {/each}
    </div>
  </section>

  <p class="landing__docs-row">
    <a
      class="landing__docs-link"
      href={DOCS_SITE_URL}
      target="_blank"
      rel="noopener noreferrer"
      data-testid="landing-docs-link"
    >
      {$_('landing.cta_docs')} →
    </a>
  </p>

  <LegalFooter />
</div>

<style>
  .landing {
    display: flex;
    flex-direction: column;
    min-height: 100%;
    gap: var(--space-8);
    padding-bottom: var(--space-4);
    width: 100%;
    max-width: 70rem;
    margin-inline: auto;
  }

  .landing__header {
    position: sticky;
    top: 0;
    z-index: 20;
    display: flex;
    align-items: center;
    justify-content: space-between;
    gap: var(--space-3);
    flex-wrap: wrap;
    padding: var(--space-4) 0;
    border-bottom: 1px solid var(--color-border);
    background: color-mix(in srgb, var(--color-bg) 86%, transparent);
  }

  @supports (backdrop-filter: blur(8px)) {
    @media (min-width: 768px) {
      .landing__header {
        background: color-mix(in srgb, var(--color-bg) 68%, transparent);
        backdrop-filter: blur(12px);
      }
    }
  }

  .landing__brand {
    display: inline-flex;
    align-items: center;
    gap: var(--space-2);
  }

  .landing__brand-name {
    font-size: var(--text-lg);
    font-weight: 600;
    letter-spacing: -0.02em;
  }

  .landing__brand-accent {
    color: var(--color-primary);
  }

  .landing__header-actions {
    display: flex;
    flex-wrap: wrap;
    align-items: center;
    justify-content: flex-end;
    gap: var(--space-2);
    min-width: 0;
  }

  .landing__hero {
    position: relative;
    display: grid;
    grid-template-columns: 1fr;
    gap: var(--space-8);
    align-items: center;
    padding: var(--space-8) 0 var(--space-6);
    overflow: clip;
  }

  .landing__hero-aurora {
    position: absolute;
    inset: -10% -6% -16%;
    z-index: 0;
    pointer-events: none;
    background:
      radial-gradient(
        42% 55% at 18% 22%,
        color-mix(in oklch, var(--color-primary) 22%, transparent) 0%,
        transparent 70%
      ),
      radial-gradient(
        40% 50% at 82% 8%,
        color-mix(in oklch, var(--color-metric-sleep) 16%, transparent) 0%,
        transparent 72%
      );
    filter: blur(52px);
    opacity: 0.55;
  }

  .landing__hero-copy {
    position: relative;
    z-index: 1;
    display: flex;
    flex-direction: column;
    align-items: flex-start;
    gap: var(--space-4);
    text-align: left;
  }

  .landing__badge {
    display: inline-block;
    padding: var(--space-1) var(--space-3);
    border-radius: var(--radius-full);
    background: color-mix(in srgb, var(--color-primary) 12%, transparent);
    color: var(--color-primary);
    font-size: var(--text-xs);
    font-weight: 600;
    letter-spacing: 0.02em;
  }

  .landing__title {
    margin: 0;
    font-size: clamp(2.1rem, 3.9vw, 3rem);
    font-weight: 700;
    line-height: 1.12;
    letter-spacing: -0.02em;
    max-width: 18ch;
  }

  .landing__subtitle {
    margin: 0;
    max-width: 38rem;
    color: var(--color-text);
    font-size: clamp(1rem, 1.4vw, 1.12rem);
    line-height: 1.6;
  }

  .landing__hero-micro {
    margin: 0;
    max-width: 36rem;
    color: var(--color-text-muted);
    font-size: var(--text-sm);
    line-height: 1.5;
  }

  .landing__hero-actions {
    display: flex;
    flex-wrap: wrap;
    gap: var(--space-2);
  }

  .landing__hero-visual {
    position: relative;
    z-index: 1;
    min-width: 0;
  }

  .landing__trust {
    list-style: none;
    display: flex;
    flex-wrap: wrap;
    gap: var(--space-2) var(--space-4);
    margin: var(--space-1) 0 0;
    padding: 0;
  }

  .landing__trust-item {
    display: inline-flex;
    align-items: center;
    gap: var(--space-2);
    font-size: var(--text-xs);
    font-weight: 600;
    letter-spacing: 0.01em;
  }

  .landing__trust-dot {
    width: 0.5rem;
    height: 0.5rem;
    border-radius: var(--radius-full);
    background: var(--tone, var(--color-primary));
  }

  .landing__trust-link {
    color: var(--color-text-muted);
    text-decoration: none;
  }

  .landing__trust-link:hover,
  .landing__trust-link:focus-visible {
    color: var(--color-primary);
    text-decoration: underline;
  }

  .landing__trust-item[data-tone='mood'] {
    --tone: var(--color-metric-mood);
  }
  .landing__trust-item[data-tone='energy'] {
    --tone: var(--color-metric-energy);
  }
  .landing__trust-item[data-tone='sleep'] {
    --tone: var(--color-metric-sleep);
  }
  .landing__trust-item[data-tone='gold'] {
    --tone: var(--color-gold);
  }

  .landing__section-heading {
    margin: 0 0 var(--space-6);
    text-align: center;
    font-size: var(--text-lg);
  }

  .landing__path-grid {
    display: grid;
    grid-template-columns: 1fr;
    gap: var(--space-4);
  }

  .landing__path {
    display: flex;
    flex-direction: column;
    align-items: flex-start;
    gap: var(--space-3);
    padding: var(--space-5);
    border: 1px solid var(--color-border);
    border-radius: var(--radius-md);
    background: var(--color-surface);
  }

  .landing__path.is-primary {
    border-color: color-mix(in srgb, var(--color-primary) 40%, var(--color-border));
  }

  .landing__path h3 {
    margin: 0;
    font-size: var(--text-base);
  }

  .landing__path p {
    margin: 0;
    color: var(--color-text-muted);
    font-size: var(--text-sm);
    line-height: 1.55;
  }

  .landing__shot {
    pointer-events: none;
    user-select: none;
  }

  .landing__shot-caption,
  .landing__preview figcaption,
  .landing__weekday-figure figcaption {
    margin: var(--space-2) 0 0;
    font-size: var(--text-sm);
    color: var(--color-text-muted);
    text-align: center;
    line-height: 1.5;
  }

  .landing__example {
    display: inline-block;
    margin-right: var(--space-2);
    padding: 0.05rem 0.4rem;
    border-radius: var(--radius-full);
    background: var(--color-surface-2);
    font-size: var(--text-2xs);
    font-weight: 600;
    letter-spacing: 0.02em;
    text-transform: uppercase;
    color: var(--color-text-faint);
  }

  .landing__preview-grid {
    display: grid;
    grid-template-columns: 1fr;
    gap: var(--space-6);
  }

  .landing__preview {
    margin: 0;
    display: flex;
    flex-direction: column;
    gap: var(--space-2);
    min-width: 0;
  }

  .landing__weekday-figure {
    margin: 0 auto;
    max-width: 46rem;
    display: flex;
    flex-direction: column;
    gap: var(--space-2);
  }

  .landing__weekday-legend {
    list-style: none;
    display: flex;
    flex-wrap: wrap;
    justify-content: center;
    gap: var(--space-3) var(--space-5);
    margin: 0;
    padding: 0;
    font-size: var(--text-xs);
    color: var(--color-text-muted);
  }

  .landing__weekday-legend li {
    display: inline-flex;
    align-items: center;
    gap: var(--space-2);
  }

  .landing__weekday-legend li::before {
    content: '';
    width: 0.7rem;
    height: 0.7rem;
    border-radius: var(--radius-sm);
    background: var(--color-success);
  }

  .landing__weekday-legend li[data-tone='worst']::before {
    background: var(--color-warning);
  }

  .landing__android {
    text-align: center;
  }

  .landing__android-body {
    margin: 0 auto var(--space-4);
    max-width: 40rem;
    color: var(--color-text-muted);
  }

  .landing__android-actions {
    display: flex;
    flex-wrap: wrap;
    justify-content: center;
    gap: var(--space-3);
  }

  .landing__android-note {
    margin: var(--space-3) 0 0;
    font-size: var(--text-xs);
    color: var(--color-text-muted);
  }

  .landing__selfhost {
    display: grid;
    grid-template-columns: 1fr;
    gap: var(--space-6);
    padding: var(--space-8) var(--space-5);
    border-radius: var(--radius-md);
    background: var(--color-surface-2);
  }

  .landing__selfhost h2 {
    margin: 0 0 var(--space-2);
    font-size: var(--text-lg);
  }

  .landing__selfhost p {
    margin: 0 0 var(--space-3);
    color: var(--color-text-muted);
    font-size: var(--text-sm);
    line-height: 1.6;
  }

  .landing__ops {
    margin: 0 0 var(--space-4);
    padding-left: 1.15rem;
    color: var(--color-text);
    font-size: var(--text-sm);
    line-height: 1.65;
  }

  .landing__selfhost-actions {
    display: flex;
    flex-wrap: wrap;
    gap: var(--space-2);
  }

  .landing__docker {
    margin: 0 0 var(--space-3);
    width: fit-content;
    max-width: 100%;
    padding: var(--space-3);
    border-radius: var(--radius-sm);
    border: 1px solid var(--color-border);
    background: var(--color-bg);
    font-family: ui-monospace, SFMono-Regular, Menlo, Monaco, Consolas, monospace;
    font-size: var(--text-xs);
    color: var(--color-primary);
    overflow-x: auto;
  }

  .landing__faq {
    max-width: 48rem;
    margin: 0 auto;
    width: 100%;
  }

  .landing__faq-list {
    display: flex;
    flex-direction: column;
  }

  .landing__faq-item {
    border-bottom: 1px solid var(--color-border);
    padding: var(--space-4) 0;
  }

  .landing__faq-item summary {
    cursor: pointer;
    font-size: var(--text-sm);
    font-weight: 600;
    min-height: var(--tap-target);
    display: flex;
    align-items: center;
    transition: color var(--transition-interactive);
  }

  .landing__faq-item summary:hover {
    color: var(--color-primary);
  }

  .landing__faq-item p {
    margin: var(--space-2) 0 0;
    color: var(--color-text-muted);
    font-size: var(--text-sm);
    line-height: 1.6;
  }

  .landing__docs-row {
    margin: 0;
    text-align: center;
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

  .landing__reveal {
    opacity: 0;
    transform: translateY(12px);
    transition:
      opacity 480ms cubic-bezier(0.16, 1, 0.3, 1),
      transform 480ms cubic-bezier(0.16, 1, 0.3, 1);
  }

  .landing__reveal:global(.is-visible) {
    opacity: 1;
    transform: none;
  }

  @media (scripting: none) {
    .landing__reveal {
      opacity: 1;
      transform: none;
    }
  }

  .landing__journey {
    padding: var(--space-8) var(--space-5);
    border-radius: var(--radius-lg);
    border: 1px solid color-mix(in srgb, var(--color-border) 70%, transparent);
    background: color-mix(in srgb, var(--color-surface-2) 60%, transparent);
    text-align: center;
  }

  .landing__journey-lead {
    margin: 0 auto var(--space-6);
    max-width: 44rem;
    color: var(--color-text-muted);
    font-size: var(--text-sm);
    line-height: 1.6;
  }

  .landing__journey-track {
    list-style: none;
    margin: 0;
    padding: 0;
    display: grid;
    grid-template-columns: 1fr;
    gap: var(--space-4);
  }

  .landing__journey-stage {
    display: flex;
    flex-direction: column;
    align-items: center;
    gap: var(--space-1);
    padding: var(--space-4) var(--space-3);
    border: 1px solid
      color-mix(in srgb, var(--tier-color, var(--color-primary)) 28%, var(--color-border));
    border-radius: var(--radius-md);
    background: color-mix(in srgb, var(--color-surface) 88%, transparent);
    text-align: center;
  }

  .landing__journey-stage[data-tier='collecting'] {
    --tier-color: var(--color-text-faint);
  }
  .landing__journey-stage[data-tier='early'] {
    --tier-color: var(--color-insight-early);
  }
  .landing__journey-stage[data-tier='provisional'] {
    --tier-color: var(--color-insight-provisional);
  }
  .landing__journey-stage[data-tier='robust'] {
    --tier-color: var(--color-insight-robust);
  }

  .landing__journey-thumb {
    width: 6rem;
    height: 6rem;
    object-fit: cover;
    border-radius: var(--radius-md);
    border: 1px solid
      color-mix(in srgb, var(--tier-color, var(--color-border)) 40%, var(--color-border));
    background: var(--color-surface-offset);
    margin-bottom: var(--space-2);
  }

  .landing__journey-range {
    font-size: var(--text-xs);
    color: var(--color-text-faint);
  }

  .landing__journey-label {
    font-size: var(--text-sm);
    font-weight: 600;
    color: var(--color-text);
  }

  .landing__journey-expectation {
    margin: var(--space-2) 0 0;
    font-size: var(--text-xs);
    line-height: 1.45;
    color: var(--color-text-muted);
    max-width: 16rem;
  }

  .landing__journey-not-yet {
    margin: var(--space-1) 0 0;
    font-size: var(--text-xs);
    line-height: 1.4;
    color: var(--color-text-faint);
    max-width: 16rem;
  }

  @media (prefers-reduced-motion: reduce) {
    .landing__reveal {
      opacity: 1;
      transform: none;
      transition: none;
    }
  }

  @media (min-width: 768px) {
    .landing__path-grid,
    .landing__preview-grid {
      grid-template-columns: repeat(2, 1fr);
    }

    .landing__journey-track {
      grid-template-columns: repeat(2, 1fr);
    }
  }

  @media (min-width: 1024px) {
    .landing {
      padding-inline: var(--space-8);
    }

    .landing__hero {
      grid-template-columns: 1fr 1fr;
      gap: var(--space-12);
      padding: var(--space-12) 0 var(--space-8);
    }

    .landing__journey-track {
      grid-template-columns: repeat(4, 1fr);
    }
  }
</style>
