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
  import LagCorrelationHeatmap from '$lib/components/insights/LagCorrelationHeatmap.svelte';
  import HomeWeekdayOverview from '$lib/components/home/HomeWeekdayOverview.svelte';
  import MetricTimeseries from '$lib/components/trends/MetricTimeseries.svelte';
  import BrowserFrameMock from '$lib/components/landing/BrowserFrameMock.svelte';
  import { tweened } from 'svelte/motion';
  import { cubicOut } from 'svelte/easing';
  import { fade } from 'svelte/transition';
  import { buildTagClusterMeta } from '$lib/utils/tagCooccurrenceMatrix';
  import { buildLandingDemo } from '$lib/components/landing/landingDemoData';

  // B4 (#734): product-shot data follows the active locale. Rebuilt reactively
  // from `$_`, so switching DE/EN re-localizes the demo tags/statements too.
  $: demo = buildLandingDemo($_);
  $: landingClusterMeta = buildTagClusterMeta(demo.tagClusters);
  import { BRAND_MARK_MD } from '$lib/constants/iconSizes';
  import {
    ANDROID_RELEASES_URL,
    OBTAINIUM_URL,
    DOCS_SITE_URL,
    REPO_URL,
  } from '$lib/constants/publicUrls';
  import { setAppLocale, type AppLocale } from '$lib/i18n';
  import { instanceConfig } from '$lib/stores/instanceConfig';

  const faqKeys = ['1', '2', '3', '4'] as const;

  // B2 (#734/#735) — hosted vs. self-host is a RUNTIME fact from the backend
  // (GET /api/v1/instance), not a build flag, so one bundle serves both the
  // managed SaaS and any self-hosted instance. Primary CTA is account signup
  // whenever registration is available here — the hosted SaaS, or a self-host
  // instance with open registration; otherwise it's "self-host it" (→ docs)
  // for the marketing/promo / locked-down case. Login stays in every mode
  // (the login page links to register). Until the descriptor resolves (or if
  // it never does — e.g. no backend), we fall back to the self-host CTA.
  $: showRegisterCta = $instanceConfig
    ? $instanceConfig.mode === 'hosted' || $instanceConfig.registration_enabled
    : false;
  // B3: prefer the real running version from the backend; fall back to the
  // bundled app.version string. The badge wording follows the mode so a hosted
  // deployment doesn't claim to be self-hosted.
  $: badgeVersion = $instanceConfig?.version ?? $_('app.version');
  $: badgeText =
    $instanceConfig?.mode === 'hosted'
      ? $_('landing.badge_hosted', { values: { version: badgeVersion } })
      : $_('landing.badge', { values: { version: badgeVersion } });

  // Trust row (D2): four value props, each tied to a token-tinted marker.
  const trustItems = [
    { key: 'privacy', tone: 'mood' },
    { key: 'selfhost', tone: 'energy' },
    { key: 'offline', tone: 'sleep' },
    // B5 (#734): not 'stress' — a red marker reads as an error/warning on a
    // positive trust badge. Gold is distinct from the other three and neutral.
    { key: 'license', tone: 'gold' },
  ] as const;

  // Maturity journey (A2 + C4): the three insight tiers, each carrying its
  // token colour and an increasing glow — the "evidence grows with your data,
  // no gamification" story told visually. Labels/ranges reuse the app's own
  // maturity vocabulary so the marketing copy can't drift from the product.
  const journeyStages = [
    {
      key: 'early',
      tier: 'early',
      label: 'maturity.early_patterns.label',
      range: 'maturity.early_patterns.range',
    },
    {
      key: 'provisional',
      tier: 'provisional',
      label: 'maturity.provisional.label',
      range: 'maturity.provisional.range',
    },
    {
      key: 'robust',
      tier: 'robust',
      label: 'maturity.robust.label',
      range: 'maturity.robust.range',
    },
  ] as const;

  // D1 — scroll reveal. Fades/slides a section in when it enters the viewport.
  // Honours prefers-reduced-motion (and any missing IntersectionObserver) by
  // showing the content immediately, so nothing is ever hidden without JS-driven
  // motion to bring it back.
  function reveal(node: HTMLElement, delay = 0) {
    const prefersReduced =
      typeof window !== 'undefined' &&
      typeof window.matchMedia === 'function' &&
      window.matchMedia('(prefers-reduced-motion: reduce)').matches;

    if (prefersReduced || typeof IntersectionObserver === 'undefined') {
      node.classList.add('is-visible');
      return {};
    }

    if (delay) node.style.transitionDelay = `${delay}ms`;
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

  function prefersReducedMotion(): boolean {
    return (
      typeof window !== 'undefined' &&
      typeof window.matchMedia === 'function' &&
      window.matchMedia('(prefers-reduced-motion: reduce)').matches
    );
  }

  // A5 — insight ticker: crossfades through a few example statements. Holds the
  // first line under reduced-motion (no auto-advance).
  const tickerKeys = ['1', '2', '3', '4'] as const;
  let tickerIndex = 0;
  function ticker(_node: HTMLElement) {
    if (prefersReducedMotion()) return {};
    const id = setInterval(() => {
      tickerIndex = (tickerIndex + 1) % tickerKeys.length;
    }, 3600);
    return {
      destroy() {
        clearInterval(id);
      },
    };
  }

  // D5 — count-up for the bento metric tiles. Values tween from 0 to target the
  // first time the feature grid scrolls into view (instant for reduced-motion).
  // Order + decimals match the six MetricCards rendered below.
  const metricTargets = [3.8, 3.4, 2.3, 86, 3.8, 3.5];
  const metricDecimals = [1, 1, 1, 0, 1, 1];
  const counts = tweened(
    metricTargets.map(() => 0),
    { duration: 900, easing: cubicOut }
  );
  let countsStarted = false;
  function startCounts(): void {
    if (countsStarted) return;
    countsStarted = true;
    void counts.set(metricTargets, { duration: prefersReducedMotion() ? 0 : 900 });
  }
  $: countValues = $counts.map((value, index) => value.toFixed(metricDecimals[index]));

  // Fire a callback the first time a node enters the viewport (immediately when
  // IntersectionObserver is unavailable or motion is reduced) — drives count-up.
  function whenVisible(node: HTMLElement, callback: () => void) {
    if (typeof IntersectionObserver === 'undefined' || prefersReducedMotion()) {
      callback();
      return {};
    }
    const observer = new IntersectionObserver(
      (entries) => {
        for (const entry of entries) {
          if (entry.isIntersecting) {
            callback();
            observer.disconnect();
          }
        }
      },
      { threshold: 0.25 }
    );
    observer.observe(node);
    return {
      destroy() {
        observer.disconnect();
      },
    };
  }

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
        className="landing__header-apk"
        data-testid="landing-cta-apk"
      >
        {$_('landing.cta_apk')}
      </Button>
      <Button href="/auth/login" variant="ghost" size="sm" data-testid="landing-cta-login">
        {$_('landing.cta_login')}
      </Button>
      {#if showRegisterCta}
        <Button
          href="/auth/register"
          variant="primary"
          size="sm"
          className="landing__cta-primary"
          data-testid="landing-cta-register"
        >
          {$_('landing.cta_register')}
        </Button>
      {:else}
        <Button
          href={DOCS_SITE_URL}
          variant="primary"
          size="sm"
          target="_blank"
          rel="noopener noreferrer"
          className="landing__cta-primary"
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
      <ul class="landing__trust" data-testid="landing-trust">
        {#each trustItems as item (item.key)}
          <li class="landing__trust-item" data-tone={item.tone}>
            <span class="landing__trust-dot" aria-hidden="true"></span>
            {$_(`landing.trust.${item.key}`)}
          </li>
        {/each}
      </ul>
    </div>
    <div class="landing__hero-visual">
      <span class="landing__hero-glow" aria-hidden="true"></span>
      <BrowserFrameMock>
        <TagGroupsSection data={demo.tagClusters} plainClusterTitles />
      </BrowserFrameMock>
    </div>
  </section>

  <div class="landing__ticker" data-testid="landing-ticker" use:ticker>
    <span class="landing__ticker-label">{$_('landing.ticker_label')}</span>
    <span class="landing__ticker-viewport">
      {#key tickerIndex}
        <span class="landing__ticker-line" in:fade={{ duration: 380 }}>
          {$_(`landing.ticker.${tickerKeys[tickerIndex]}`)}
        </span>
      {/key}
    </span>
  </div>

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
          <!-- Product shots only: inert removes the mock's controls from tab
               order and pointer events, aria-hidden hides the duplicated app
               UI from screen readers; the figcaption carries the description. -->
          <div class="landing__shot" inert aria-hidden="true">
            <InsightMatrix insights={demo.insights} preview />
          </div>
        </BrowserFrameMock>
        <figcaption>{$_('landing.preview_matrix')}</figcaption>
      </figure>
      <figure class="landing__preview">
        <BrowserFrameMock address="app.correlcore.example/insights">
          <div class="landing__shot" inert aria-hidden="true">
            <InsightCard insight={demo.featuredInsight} maturity={demo.maturity} featured />
          </div>
        </BrowserFrameMock>
        <figcaption>{$_('landing.preview_card')}</figcaption>
      </figure>
      <figure class="landing__preview">
        <BrowserFrameMock address="app.correlcore.example/insights">
          <div class="landing__shot" inert aria-hidden="true">
            <TagCooccurrenceHeatmap
              data={demo.cooccurrence}
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
      <figure class="landing__preview">
        <BrowserFrameMock address="app.correlcore.example/insights">
          <div class="landing__shot" inert aria-hidden="true">
            <LagCorrelationHeatmap insights={demo.lagInsights} />
          </div>
        </BrowserFrameMock>
        <figcaption>{$_('landing.preview_lag')}</figcaption>
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
      <figcaption>{$_('landing.weekday_caption')}</figcaption>
    </figure>
  </section>

  <section
    class="landing__bento landing__reveal"
    use:reveal
    use:whenVisible={startCounts}
    aria-labelledby="landing-features-heading"
  >
    <h2 id="landing-features-heading" class="landing__section-heading">
      {$_('landing.features_heading')}
    </h2>
    <div class="landing__bento-grid">
      <article class="landing__tile" data-tone="mood" data-testid="landing-feature-1">
        <h3>{$_('landing.features.1.title')}</h3>
        <p>{$_('landing.features.1.body')}</p>
        <div class="landing__metric-row" aria-hidden="true">
          <MetricCard
            metric="mood_score"
            label={$_('landing.metric_mood')}
            value={countValues[0]}
            unit="/5"
          />
          <MetricCard
            metric="energy"
            label={$_('landing.metric_energy')}
            value={countValues[1]}
            unit="/5"
          />
          <MetricCard
            metric="stress"
            label={$_('landing.metric_stress')}
            value={countValues[2]}
            unit="/5"
          />
        </div>
        <div class="landing__viz-note">{$_('landing.viz_correlations')}</div>
      </article>
      <article class="landing__tile" data-tone="energy" data-testid="landing-feature-2">
        <h3>{$_('landing.features.2.title')}</h3>
        <p>{$_('landing.features.2.body')}</p>
        <div class="landing__metric-row" aria-hidden="true">
          <MetricCard
            metric="tracking_consistency"
            label={$_('landing.metric_consistency')}
            value={countValues[3]}
            unit="%"
          />
          <MetricCard
            metric="mood_score"
            label={$_('landing.metric_mood')}
            value={countValues[4]}
            unit="/5"
          />
          <MetricCard
            metric="energy"
            label={$_('landing.metric_energy')}
            value={countValues[5]}
            unit="/5"
          />
        </div>
        <div class="landing__timeseries" aria-hidden="true">
          <MetricTimeseries points={demo.timeseriesPoints} range="week" enableCursor={false} />
        </div>
      </article>
    </div>
  </section>

  <section
    class="landing__journey"
    use:reveal
    aria-labelledby="landing-journey-heading"
    data-testid="landing-journey"
  >
    <h2 id="landing-journey-heading" class="landing__section-heading">
      {$_('landing.journey_heading')}
    </h2>
    <p class="landing__journey-lead">{$_('landing.journey_body')}</p>
    <div class="landing__journey-bar" aria-hidden="true"></div>
    <ol class="landing__journey-track">
      {#each journeyStages as stage (stage.key)}
        <li class="landing__journey-stage" data-tier={stage.tier}>
          <span class="landing__journey-node" aria-hidden="true"></span>
          <span class="landing__journey-range">{$_(stage.range)}</span>
          <span class="landing__journey-label">{$_(stage.label)}</span>
        </li>
      {/each}
    </ol>
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

  <section
    class="landing__selfhost landing__reveal"
    use:reveal
    aria-labelledby="landing-selfhost-heading"
  >
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

  <section class="landing__faq landing__reveal" use:reveal aria-labelledby="landing-faq-heading">
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

  /* D3 — sticky header. Stays readable over scrolling content via a tinted
     wash; the blur is layered on for desktop only (matches app.css policy,
     mobile Firefox repaints it as an opaque block). */
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
    min-width: 0;
  }

  /* B1 (#734) — on narrow screens the five header actions overflow and wrap
     messily into the hero. The APK button is redundant with the Android
     section below, so drop it from the header on mobile; the remaining actions
     (theme, lang, login, primary) fit or wrap cleanly. */
  @media (max-width: 767px) {
    /* Scope under the (scoped) header so specificity (0,2,0) beats Button's own
       `.ui-button { display: inline-flex }` regardless of stylesheet order. */
    .landing__header :global(.landing__header-apk) {
      display: none;
    }
  }

  .landing__hero {
    position: relative;
    display: grid;
    grid-template-columns: 1fr;
    gap: var(--space-8);
    align-items: center;
    padding: var(--space-8) 0 var(--space-6);
    /* Clip the aurora's horizontal bleed so its box never causes sideways
       page scroll on narrow viewports (PR #736 review). `clip` keeps the
       header's position:sticky intact (unlike `hidden`). */
    overflow: clip;
  }

  /* B1 — Aurora field behind the hero. Token-only, low opacity, static (no
     animation, so nothing to gate on prefers-reduced-motion). Blends the
     brand primary with the energy + sleep metric hues for a warm/cool wash
     that reads in both themes without overpowering the copy. */
  .landing__hero-aurora {
    position: absolute;
    inset: -12% -8% -20%;
    z-index: 0;
    pointer-events: none;
    background:
      radial-gradient(
        42% 55% at 18% 22%,
        color-mix(in oklch, var(--color-primary) 30%, transparent) 0%,
        transparent 70%
      ),
      radial-gradient(
        40% 50% at 82% 8%,
        color-mix(in oklch, var(--color-metric-sleep) 24%, transparent) 0%,
        transparent 72%
      ),
      radial-gradient(
        46% 60% at 68% 92%,
        color-mix(in oklch, var(--color-metric-energy) 20%, transparent) 0%,
        transparent 74%
      );
    filter: blur(52px);
    opacity: 0.75;
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

  /* D4 — sharper hero hierarchy: larger, tighter headline; higher-contrast,
     slightly larger sub. */
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
    font-size: var(--text-xs);
    letter-spacing: 0.01em;
    opacity: 0.85;
  }

  .landing__hero-visual {
    position: relative;
    min-width: 0;
  }

  /* C1 — Glow that lifts the product shot off the flat background. Larger and
     softer than the brand-mark glow; sits behind the browser frame. */
  .landing__hero-glow {
    position: absolute;
    inset: -8%;
    z-index: 0;
    pointer-events: none;
    border-radius: var(--radius-xl);
    background: radial-gradient(
      circle at 50% 40%,
      color-mix(in oklch, var(--color-primary) 34%, transparent) 0%,
      transparent 68%
    );
    filter: blur(32px);
  }

  .landing__hero-visual :global(.cc-frame) {
    position: relative;
    z-index: 1;
  }

  /* D2 — Trust row: token-tinted value props under the hero copy. */
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
    color: var(--color-text-muted);
  }

  .landing__trust-dot {
    width: 0.5rem;
    height: 0.5rem;
    border-radius: var(--radius-full);
    background: var(--tone, var(--color-primary));
    box-shadow: 0 0 8px color-mix(in oklch, var(--tone, var(--color-primary)) 60%, transparent);
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

  /* C3 — Primary CTA glow. Rests with a soft halo, brightens on hover/focus. */
  :global(.landing__cta-primary) {
    box-shadow:
      0 0 0 1px color-mix(in oklch, var(--color-primary) 40%, transparent),
      0 4px 18px color-mix(in oklch, var(--color-primary) 30%, transparent);
    transition:
      box-shadow var(--transition-interactive),
      transform var(--transition-interactive);
  }

  :global(.landing__cta-primary:hover),
  :global(.landing__cta-primary:focus-visible) {
    box-shadow:
      0 0 0 1px color-mix(in oklch, var(--color-primary) 55%, transparent),
      0 6px 26px color-mix(in oklch, var(--color-primary) 46%, transparent);
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

  /* Grid finish — four previews balance as a 2×2 (was 3+1 orphan). */
  @media (min-width: 768px) {
    .landing__preview-grid {
      grid-template-columns: repeat(2, 1fr);
      align-items: start;
    }
  }

  /* A5 — insight ticker pill under the hero. */
  .landing__ticker {
    display: flex;
    align-items: center;
    justify-content: center;
    flex-wrap: wrap;
    gap: var(--space-2) var(--space-3);
    width: fit-content;
    max-width: 100%;
    margin: calc(var(--space-4) * -1) auto 0;
    padding: var(--space-2) var(--space-4);
    border: 1px solid color-mix(in srgb, var(--color-primary) 24%, var(--color-border));
    border-radius: var(--radius-full);
    background: color-mix(in srgb, var(--color-primary) 6%, var(--color-surface));
  }

  .landing__ticker-label {
    font-size: var(--text-2xs);
    font-weight: 600;
    letter-spacing: 0.04em;
    text-transform: uppercase;
    color: var(--color-text-faint);
  }

  .landing__ticker-viewport {
    display: inline-grid;
    align-items: center;
    min-height: 1.4em;
    min-width: 0;
  }

  .landing__ticker-line {
    grid-area: 1 / 1;
    font-family: ui-monospace, SFMono-Regular, Menlo, Monaco, Consolas, monospace;
    font-size: var(--text-xs);
    font-weight: 600;
    color: var(--color-primary);
    /* Wrap on narrow viewports — long localized strings must never force
       horizontal scroll (PR #736 review). */
    white-space: normal;
    overflow-wrap: anywhere;
    text-align: center;
  }

  /* A3 — weekday overview product shot, centred like the other showcases. */
  .landing__weekday-figure {
    margin: 0 auto;
    max-width: 46rem;
    display: flex;
    flex-direction: column;
    gap: var(--space-2);
  }

  .landing__weekday-figure figcaption {
    font-size: var(--text-sm);
    color: var(--color-text-muted);
    text-align: center;
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
    position: relative;
    display: flex;
    flex-direction: column;
    gap: var(--space-3);
    padding: var(--space-5);
    border: 1px solid var(--color-border);
    border-top: 2px solid
      color-mix(in oklch, var(--tone, var(--color-primary)) 55%, var(--color-border));
    border-radius: var(--radius-md);
    background:
      linear-gradient(
        180deg,
        color-mix(in oklch, var(--tone, var(--color-primary)) 7%, transparent) 0%,
        transparent 40%
      ),
      color-mix(in srgb, var(--color-surface) 92%, transparent);
  }

  /* B4 — each tile carries its lead metric's hue on the top edge. */
  .landing__tile[data-tone='mood'] {
    --tone: var(--color-metric-mood);
  }
  .landing__tile[data-tone='energy'] {
    --tone: var(--color-metric-energy);
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

  /* D1 — scroll reveal. Sections start slightly lowered + transparent; the
     `reveal` action adds `is-visible` when they scroll into view. The action
     itself short-circuits under prefers-reduced-motion, and the media query
     below is a belt-and-braces guard for the CSS. */
  .landing__reveal {
    opacity: 0;
    transform: translateY(18px);
    transition:
      opacity 560ms cubic-bezier(0.16, 1, 0.3, 1),
      transform 560ms cubic-bezier(0.16, 1, 0.3, 1);
    will-change: opacity, transform;
  }

  .landing__reveal:global(.is-visible) {
    opacity: 1;
    transform: none;
  }

  /* Visible-by-default without scripting: if JS is disabled the `reveal` action
     never runs, so never leave a section stuck transparent (PR #736 review). */
  @media (scripting: none) {
    .landing__reveal {
      opacity: 1;
      transform: none;
    }
  }

  /* B3 — dot grid behind the feature bento, giving a quiet "data" texture. */
  .landing__bento {
    position: relative;
    padding: var(--space-6) var(--space-5);
    border-radius: var(--radius-lg);
    background-image: radial-gradient(
      color-mix(in oklch, var(--color-primary) 24%, transparent) 1px,
      transparent 1px
    );
    background-size: 22px 22px;
    background-position: -1px -1px;
  }

  .landing__bento > .landing__section-heading,
  .landing__bento > .landing__bento-grid {
    position: relative;
    z-index: 1;
  }

  /* Fade the dot field toward the edges so it never reads as a hard rectangle. */
  .landing__bento::after {
    content: '';
    position: absolute;
    inset: 0;
    z-index: 0;
    pointer-events: none;
    border-radius: inherit;
    background: radial-gradient(120% 120% at 50% 0%, transparent 55%, var(--color-bg) 100%);
  }

  /* B2 — the maturity journey sits on a tinted panel to break the flat run of
     sections, mirroring the self-host block's treatment. */
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

  /* A2/C4 — progression bar tinted early → provisional → robust with a glow. */
  .landing__journey-bar {
    height: 4px;
    max-width: 40rem;
    margin: 0 auto var(--space-6);
    border-radius: var(--radius-full);
    background: linear-gradient(
      90deg,
      var(--color-insight-early) 0%,
      var(--color-insight-provisional) 50%,
      var(--color-insight-robust) 100%
    );
    box-shadow: 0 0 16px color-mix(in oklch, var(--color-insight-robust) 45%, transparent);
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
      color-mix(in srgb, var(--tier-color, var(--color-primary)) 32%, var(--color-border));
    border-radius: var(--radius-md);
    background: color-mix(in srgb, var(--color-surface) 88%, transparent);
    /* Staggered reveal, keyed on the section becoming visible. */
    opacity: 0;
    transform: translateY(14px);
    transition:
      opacity 480ms cubic-bezier(0.16, 1, 0.3, 1),
      transform 480ms cubic-bezier(0.16, 1, 0.3, 1);
  }

  /* `is-visible` is added at runtime by the reveal action, so the scoped
     compiler can't see it statically — mark it :global so Svelte keeps the
     rule instead of pruning it as unused. */
  .landing__journey:global(.is-visible) .landing__journey-stage {
    opacity: 1;
    transform: none;
  }
  .landing__journey:global(.is-visible) .landing__journey-stage:nth-child(2) {
    transition-delay: 130ms;
  }
  .landing__journey:global(.is-visible) .landing__journey-stage:nth-child(3) {
    transition-delay: 260ms;
  }

  .landing__journey-stage[data-tier='early'] {
    --tier-color: var(--color-insight-early);
    --tier-glow: 6px;
  }
  .landing__journey-stage[data-tier='provisional'] {
    --tier-color: var(--color-insight-provisional);
    --tier-glow: 13px;
  }
  .landing__journey-stage[data-tier='robust'] {
    --tier-color: var(--color-insight-robust);
    --tier-glow: 22px;
  }

  /* C4 — node glow deepens as the tier matures. */
  .landing__journey-node {
    width: 0.85rem;
    height: 0.85rem;
    border-radius: var(--radius-full);
    background: var(--tier-color, var(--color-primary));
    box-shadow: 0 0 var(--tier-glow, 8px)
      color-mix(in oklch, var(--tier-color, var(--color-primary)) 70%, transparent);
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

  /* Belt-and-braces: never animate translate/opacity for reduced-motion users. */
  @media (prefers-reduced-motion: reduce) {
    .landing__reveal,
    .landing__journey-stage {
      opacity: 1;
      transform: none;
      transition: none;
    }
  }

  @media (max-width: 480px) {
    .landing__metric-row {
      grid-template-columns: 1fr;
    }
  }

  @media (min-width: 768px) {
    .landing__journey-track {
      grid-template-columns: repeat(3, 1fr);
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
