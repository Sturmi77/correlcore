<script lang="ts">
  import { onMount } from 'svelte';
  import { _ } from 'svelte-i18n';
  import { auth } from '$lib/stores/auth';
  import { listLatestInsights, type InsightResponse } from '$lib/api/insights';
  import ThemeToggle from '$lib/components/common/ThemeToggle.svelte';
  import InsightMatrix from '$lib/components/insights/InsightMatrix.svelte';

  let insights: InsightResponse[] = [];
  let loading = false;
  let error = '';

  function confidence(value: number | null): string {
    if (value === null) return $_('home.insight.confidence_unknown');
    return `${Math.round(value * 100)}%`;
  }

  async function loadInsights(): Promise<void> {
    if ($auth.status !== 'authenticated') return;
    loading = true;
    error = '';
    try {
      const response = await listLatestInsights({ limit: 50 });
      insights = response.insights;
    } catch (err) {
      error = err instanceof Error ? err.message : $_('error.generic');
      insights = [];
    } finally {
      loading = false;
    }
  }

  onMount(() => {
    void loadInsights();
  });
</script>

<svelte:head>
  <title>{$_('insights.page.title')} - {$_('app.name')}</title>
</svelte:head>

<main class="insights-page">
  <header class="insights-page__top">
    <a class="btn btn-sm variant-ghost-surface" href="/">{$_('nav.home')}</a>
    <ThemeToggle testId="insights-theme-toggle" />
  </header>

  <section class="insights-page__intro">
    <div>
      <h1>{$_('insights.page.title')}</h1>
      <p>{$_('insights.page.subtitle')}</p>
    </div>
    <a class="btn btn-sm variant-soft-primary" href="/trends">{$_('trends.title')}</a>
  </section>

  {#if $auth.status !== 'authenticated'}
    <section class="insights-page__panel">
      <p>{$_('insights.page.auth_required')}</p>
      <a class="btn btn-sm variant-filled-primary" href="/auth/login">{$_('auth.login.submit')}</a>
    </section>
  {:else if loading}
    <section class="insights-page__panel">
      <p>{$_('insights.page.loading')}</p>
    </section>
  {:else if error}
    <section class="insights-page__panel">
      <p>{error}</p>
      <button class="btn btn-sm variant-soft-primary" type="button" on:click={loadInsights}>
        {$_('entry.autosave.retry')}
      </button>
    </section>
  {:else}
    <InsightMatrix {insights} />

    <section class="insights-page__list" aria-label={$_('insights.page.list_heading')}>
      <h2>{$_('insights.page.list_heading')}</h2>
      {#if insights.length}
        {#each insights as insight}
          <article class="insights-page__item">
            <header>
              <span>{$_(`home.insight.tier.${insight.tier}`)}</span>
              <time datetime={insight.generated_for_date}>{insight.generated_for_date}</time>
            </header>
            <p>{insight.statement ?? $_('home.insight.empty_statement')}</p>
            <dl>
              <div>
                <dt>{$_('home.insight.confidence')}</dt>
                <dd>{confidence(insight.confidence)}</dd>
              </div>
              <div>
                <dt>{$_('home.insight.sample_size')}</dt>
                <dd>{insight.sample_n}</dd>
              </div>
            </dl>
          </article>
        {/each}
      {:else}
        <p class="insights-page__empty">{$_('insights.page.empty')}</p>
      {/if}
    </section>
  {/if}
</main>

<style>
  .insights-page {
    display: flex;
    flex-direction: column;
    gap: 1.25rem;
    padding: 1rem 0 2rem;
  }

  .insights-page__top,
  .insights-page__intro,
  .insights-page__item header,
  .insights-page__item dl {
    display: flex;
    align-items: center;
    justify-content: space-between;
    gap: 1rem;
  }

  .insights-page__intro {
    align-items: flex-start;
  }

  .insights-page__intro h1,
  .insights-page__intro p,
  .insights-page__item p,
  .insights-page__empty {
    margin: 0;
  }

  .insights-page__intro h1 {
    font-size: var(--text-xl, 1.35rem);
  }

  .insights-page__intro p,
  .insights-page__empty {
    color: var(--color-text-muted);
  }

  .insights-page__panel {
    display: flex;
    flex-direction: column;
    gap: 0.75rem;
    padding: 1rem;
    border: 1px solid rgb(var(--color-surface-300, 209 213 219) / 0.55);
    border-radius: 0.45rem;
  }

  .insights-page__list {
    display: flex;
    flex-direction: column;
    gap: 0.75rem;
  }

  .insights-page__list h2 {
    margin: 0;
    font-size: var(--text-lg, 1.1rem);
  }

  .insights-page__item {
    display: flex;
    flex-direction: column;
    gap: 0.6rem;
    padding: 0.85rem;
    border: 1px solid rgb(var(--color-surface-300, 209 213 219) / 0.5);
    border-radius: 0.45rem;
    background: rgb(var(--color-surface-100, 243 244 246) / 0.35);
  }

  .insights-page__item header {
    font-size: 0.78rem;
    color: var(--color-text-muted);
  }

  .insights-page__item dl {
    justify-content: flex-start;
    margin: 0;
  }

  .insights-page__item dt,
  .insights-page__item dd {
    margin: 0;
    font-size: 0.75rem;
  }

  .insights-page__item dt {
    color: var(--color-text-muted);
  }

  .insights-page__item dd {
    font-weight: 700;
  }

  @media (max-width: 520px) {
    .insights-page__intro,
    .insights-page__item header {
      flex-direction: column;
      align-items: flex-start;
    }
  }
</style>
