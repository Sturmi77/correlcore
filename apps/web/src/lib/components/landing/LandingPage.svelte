<script lang="ts">
  import { _, locale } from 'svelte-i18n';
  import Button from '$lib/components/common/Button.svelte';
  import CorrelCoreLogo from '$lib/components/common/CorrelCoreLogo.svelte';
  import LegalFooter from '$lib/components/common/LegalFooter.svelte';
  import ThemeToggle from '$lib/components/common/ThemeToggle.svelte';
  import MetricCard from '$lib/components/home/MetricCard.svelte';
  import TagGroupsSection from '$lib/components/insights/TagGroupsSection.svelte';
  import InsightMatrix from '$lib/components/insights/InsightMatrix.svelte';
  import InsightCard from '$lib/components/insights/InsightCard.svelte';
  import TagCooccurrenceHeatmap from '$lib/components/insights/TagCooccurrenceHeatmap.svelte';
  import MetricTimeseries from '$lib/components/trends/MetricTimeseries.svelte';
  import BrowserFrameMock from '$lib/components/landing/BrowserFrameMock.svelte';
  import { buildTagClusterMeta } from '$lib/utils/tagCooccurrenceMatrix';
  import {
    landingTagClusters,
    landingTimeseriesPoints,
    landingInsights,
    landingFeaturedInsight,
    landingMaturity,
    landingCooccurrence,
  } from '$lib/components/landing/landingDemoData';

  const landingClusterMeta = buildTagClusterMeta(landingTagClusters);
  import { BRAND_MARK_MD } from '$lib/constants/iconSizes';
  import {
    ANDROID_RELEASES_URL,
    OBTAINIUM_URL,
    DOCS_SITE_URL,
    REPO_URL,
  } from '$lib/constants/publicUrls';
  import { setAppLocale, type AppLocale } from '$lib/i18n';

  const faqKeys = ['1', '2', '3', '4'] as const;

  $: activeLocale = (($locale ?? 'de').split('-')[0] === 'en' ? 'en' : 'de') as AppLocale;
  $: nextLocale = (activeLocale === 'de' ? 'en' : 'de') as AppLocale;

  function toggleLocale(): void {
    setAppLocale(nextLocale);
  }
</script>

<div class="landing" data-testid="marketing-landing">
  <header class="landing__header">
    <div class="landing__brand">
      <span class="landing__brand-glow" aria-hidden="true"></span>
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
      <Button
        href={ANDROID_RELEASES_URL}
        variant="ghost"
        size="sm"
        target="_blank"
        rel="noopener noreferrer"
        data-testid="landing-cta-apk"
      >
        {$_('landing.cta_apk')}
      </Button>
      <Button href="/auth/login" variant="ghost" size="sm" data-testid="landing-cta-login">
        {$_('landing.cta_login')}
      </Button>
      <Button href="/auth/register" variant="primary" size="sm" data-testid="landing-cta-register">
        {$_('landing.cta_register')}
      </Button>
    </div>
  </header>

  <section class="landing__hero">
    <div class="landing__hero-copy">
      <span class="landing__badge" data-testid="landing-badge">{$_('landing.badge')}</span>
      <h1 class="landing__title">{$_('landing.hero_title')}</h1>
      <p class="landing__subtitle">{$_('landing.hero_subtitle')}</p>
    </div>
    <div class="landing__hero-visual">
      <BrowserFrameMock>
        <TagGroupsSection data={landingTagClusters} />
      </BrowserFrameMock>
    </div>
  </section>

  <section class="landing__previews" aria-labelledby="landing-previews-heading">
    <h2 id="landing-previews-heading" class="landing__section-heading">
      {$_('landing.previews_heading')}
    </h2>
    <div class="landing__preview-grid">
      <figure class="landing__preview">
        <BrowserFrameMock address="app.correlcore.example/insights">
          <!-- Product shots only: inert removes the mock's controls from tab
               order and pointer events, aria-hidden hides the duplicated app
               UI from screen readers; the figcaption carries the description. -->
          <div class="landing__shot" inert aria-hidden="true">
            <InsightMatrix insights={landingInsights} preview />
          </div>
        </BrowserFrameMock>
        <figcaption>{$_('landing.preview_matrix')}</figcaption>
      </figure>
      <figure class="landing__preview">
        <BrowserFrameMock address="app.correlcore.example/insights">
          <div class="landing__shot" inert aria-hidden="true">
            <InsightCard insight={landingFeaturedInsight} maturity={landingMaturity} featured />
          </div>
        </BrowserFrameMock>
        <figcaption>{$_('landing.preview_card')}</figcaption>
      </figure>
      <figure class="landing__preview">
        <BrowserFrameMock address="app.correlcore.example/insights">
          <div class="landing__shot" inert aria-hidden="true">
            <TagCooccurrenceHeatmap
              data={landingCooccurrence}
              sortMode="clustered"
              enableClusterSort
              clusterMeta={landingClusterMeta}
              showRangeSelector={false}
              minPairsForDisplay={1}
              preview
            />
          </div>
        </BrowserFrameMock>
        <figcaption>{$_('landing.preview_heatmap')}</figcaption>
      </figure>
    </div>
  </section>

  <section class="landing__bento" aria-labelledby="landing-features-heading">
    <h2 id="landing-features-heading" class="landing__section-heading">
      {$_('landing.features_heading')}
    </h2>
    <div class="landing__bento-grid">
      <article class="landing__tile" data-testid="landing-feature-1">
        <h3>{$_('landing.features.1.title')}</h3>
        <p>{$_('landing.features.1.body')}</p>
        <div class="landing__metric-row" aria-hidden="true">
          <MetricCard metric="mood_score" label={$_('landing.metric_mood')} value="3.8" unit="/5" />
          <MetricCard metric="energy" label={$_('landing.metric_energy')} value="3.4" unit="/5" />
          <MetricCard metric="stress" label={$_('landing.metric_stress')} value="2.3" unit="/5" />
        </div>
        <div class="landing__viz-note">{$_('landing.viz_correlations')}</div>
      </article>
      <article class="landing__tile" data-testid="landing-feature-2">
        <h3>{$_('landing.features.2.title')}</h3>
        <p>{$_('landing.features.2.body')}</p>
        <div class="landing__metric-row" aria-hidden="true">
          <MetricCard
            metric="tracking_consistency"
            label={$_('landing.metric_consistency')}
            value="86"
            unit="%"
          />
          <MetricCard metric="mood_score" label={$_('landing.metric_mood')} value="3.8" unit="/5" />
          <MetricCard metric="energy" label={$_('landing.metric_energy')} value="3.5" unit="/5" />
        </div>
        <div class="landing__timeseries" aria-hidden="true">
          <MetricTimeseries points={landingTimeseriesPoints} range="week" enableCursor={false} />
        </div>
      </article>
    </div>
  </section>

  <section class="landing__android" aria-labelledby="landing-android-heading">
    <h2 id="landing-android-heading" class="landing__section-heading">
      {$_('landing.android_heading')}
    </h2>
    <p class="landing__android-body">{$_('landing.android_body')}</p>
    <div class="landing__android-actions">
      <Button
        href={ANDROID_RELEASES_URL}
        variant="primary"
        target="_blank"
        rel="noopener noreferrer"
        data-testid="landing-android-download"
      >
        {$_('landing.android_download')}
      </Button>
      <Button
        href={OBTAINIUM_URL}
        variant="secondary"
        target="_blank"
        rel="noopener noreferrer"
        data-testid="landing-android-obtainium"
      >
        {$_('landing.android_obtainium')}
      </Button>
    </div>
    <p class="landing__android-note">{$_('landing.android_sha256')}</p>
  </section>

  <section class="landing__selfhost" aria-labelledby="landing-selfhost-heading">
    <div>
      <h2 id="landing-selfhost-heading">{$_('landing.selfhost_title')}</h2>
      <p>{$_('landing.selfhost_body')}</p>
      <pre class="landing__docker" data-testid="landing-docker-cmd">{$_(
          'landing.docker_label'
        )}</pre>
      <Button
        href={REPO_URL}
        variant="secondary"
        target="_blank"
        rel="noopener noreferrer"
        data-testid="landing-github-link"
      >
        {$_('landing.tech_github')}
      </Button>
    </div>
    <div>
      <h2>{$_('landing.tech_title')}</h2>
      <p>{$_('landing.tech_body')}</p>
      <p class="landing__no-game">{$_('landing.features.3.body')}</p>
    </div>
  </section>

  <section class="landing__faq" aria-labelledby="landing-faq-heading">
    <h2 id="landing-faq-heading" class="landing__section-heading">{$_('landing.faq_heading')}</h2>
    <div class="landing__faq-list">
      {#each faqKeys as key}
        <details class="landing__faq-item" data-testid={`landing-faq-${key}`}>
          <summary>{$_(`landing.faq.${key}.q`)}</summary>
          <p>{$_(`landing.faq.${key}.a`)}</p>
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
    display: flex;
    align-items: center;
    justify-content: space-between;
    gap: var(--space-3);
    flex-wrap: wrap;
    padding: var(--space-4) 0;
    border-bottom: 1px solid var(--color-border);
  }

  .landing__brand {
    position: relative;
    display: inline-flex;
    align-items: center;
    gap: var(--space-2);
  }

  .landing__brand-glow {
    position: absolute;
    inset: -0.75rem;
    border-radius: var(--radius-full);
    background: radial-gradient(
      circle,
      color-mix(in srgb, var(--color-primary) 40%, transparent) 0%,
      transparent 72%
    );
    filter: blur(14px);
    pointer-events: none;
    z-index: 0;
  }

  .landing__brand :global(svg),
  .landing__brand-name {
    position: relative;
    z-index: 1;
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
  }

  .landing__hero {
    display: grid;
    grid-template-columns: 1fr;
    gap: var(--space-8);
    align-items: center;
    padding: var(--space-8) 0 var(--space-6);
  }

  .landing__hero-copy {
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
    font-size: clamp(1.9rem, 3.4vw, 2.6rem);
    line-height: 1.15;
    max-width: 18ch;
  }

  .landing__subtitle {
    margin: 0;
    max-width: 36rem;
    color: var(--color-text-muted);
    font-size: var(--text-base);
    line-height: 1.6;
  }

  .landing__hero-visual {
    min-width: 0;
  }

  .landing__section-heading {
    margin: 0 0 var(--space-6);
    text-align: center;
    font-size: var(--text-lg);
  }

  .landing__previews {
    margin-top: var(--space-8);
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

  .landing__preview figcaption {
    font-size: var(--text-sm);
    color: var(--color-text-muted);
    text-align: center;
  }

  /* Pure product shot: never interactive on the anonymous landing. The preview
     variants of the components are already compact (no header/toolbar), so the
     diagram itself is the hero — no hard crop that would clip the chart (#546). */
  .landing__shot {
    pointer-events: none;
    user-select: none;
  }

  @media (min-width: 768px) {
    .landing__preview-grid {
      grid-template-columns: repeat(3, 1fr);
      align-items: start;
    }
  }

  .landing__android {
    margin-top: var(--space-8);
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

  .landing__bento-grid {
    display: grid;
    grid-template-columns: 1fr;
    gap: var(--space-4);
  }

  .landing__tile {
    display: flex;
    flex-direction: column;
    gap: var(--space-3);
    padding: var(--space-5);
    border: 1px solid var(--color-border);
    border-radius: var(--radius-md);
    background: color-mix(in srgb, var(--color-surface) 92%, transparent);
  }

  .landing__tile h3 {
    margin: 0;
    font-size: var(--text-base);
  }

  .landing__tile > p {
    margin: 0;
    color: var(--color-text-muted);
    font-size: var(--text-sm);
    line-height: 1.55;
  }

  .landing__metric-row {
    display: grid;
    grid-template-columns: repeat(3, minmax(0, 1fr));
    gap: var(--space-2);
  }

  .landing__viz-note {
    padding: var(--space-4);
    border: 1px dashed var(--color-border);
    border-radius: var(--radius-sm);
    color: var(--color-text-faint);
    font-size: var(--text-xs);
    text-align: center;
  }

  .landing__timeseries {
    min-width: 0;
    overflow: hidden;
  }

  .landing__selfhost {
    display: grid;
    grid-template-columns: 1fr;
    gap: var(--space-8);
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

  .landing__docker {
    margin: 0 0 var(--space-3);
    width: fit-content;
    max-width: 100%;
    padding: var(--space-3);
    border-radius: var(--radius-sm);
    border: 1px solid var(--color-border);
    background: var(--color-bg);
    font-family: ui-monospace, SFMono-Regular, Menlo, Monaco, Consolas, monospace;
    font-size: var(--text-sm);
    color: var(--color-primary);
    overflow-x: auto;
  }

  .landing__no-game {
    font-weight: 600;
    color: var(--color-text) !important;
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

  @media (max-width: 480px) {
    .landing__metric-row {
      grid-template-columns: 1fr;
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

    .landing__bento-grid {
      grid-template-columns: 1fr 1fr;
    }

    .landing__selfhost {
      grid-template-columns: 1fr 1fr;
      padding: var(--space-8);
      gap: var(--space-12);
    }
  }
</style>
