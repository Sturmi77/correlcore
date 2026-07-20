<script lang="ts">
  import { onMount } from 'svelte';
  import { _ } from 'svelte-i18n';
  import { goto } from '$app/navigation';
  import { auth } from '$lib/stores/auth';
  import { ApiError } from '$lib/api/client';
  import {
    fetchLatestInsightDigest,
    type InsightDigestResponse,
    type InsightResponse,
  } from '$lib/api/insights';
  import Button from '$lib/components/common/Button.svelte';
  import InlineAlert from '$lib/components/common/InlineAlert.svelte';
  import Panel from '$lib/components/common/Panel.svelte';
  import ScreenHeader from '$lib/components/common/ScreenHeader.svelte';
  import InsightCard from '$lib/components/insights/InsightCard.svelte';
  import { registerPageRefresh } from '$lib/stores/pageRefresh';

  let digest: InsightDigestResponse | null = null;
  let loading = true;
  let error = '';

  function toInsightResponse(item: InsightDigestResponse['insights'][number]): InsightResponse {
    return {
      id: item.id,
      user_id: '',
      insight_type: item.insight_type,
      tier: 'developing',
      metric: item.metric,
      subject_type: null,
      subject_id: null,
      subject_label: null,
      effect_size: item.effect_size,
      confidence: item.confidence,
      sample_n: 0,
      statement: item.statement,
      flags: { medical_disclaimer_required: true, causal_claim: false },
      payload: {},
      generated_for_date: digest?.week_end ?? '',
      generated_at: digest?.week_end ?? '',
      created_at: digest?.week_end ?? '',
      updated_at: digest?.week_end ?? '',
    };
  }

  async function loadDigest(): Promise<void> {
    loading = true;
    error = '';
    try {
      digest = await fetchLatestInsightDigest();
    } catch (err) {
      if (err instanceof ApiError && err.status === 404) {
        error = $_('insights.digest.empty');
      } else if (err instanceof ApiError && err.status === 403) {
        error = $_('insights.digest.disabled');
      } else {
        error = err instanceof Error ? err.message : $_('insights.digest.error');
      }
      digest = null;
    } finally {
      loading = false;
    }
  }

  onMount(() => {
    if ($auth.status !== 'authenticated') {
      void goto('/auth/login?next=/insights/digest');
      return;
    }
    void loadDigest();
    return registerPageRefresh(() => loadDigest());
  });
</script>

<svelte:head>
  <title>{$_('insights.digest.title')} - {$_('app.name')}</title>
</svelte:head>

<div class="digest-page">
  <p class="digest-page__back">
    <a href="/insights">{$_('nav.back')}</a>
  </p>
  <ScreenHeader title={$_('insights.digest.title')} subtitle={$_('insights.digest.subtitle')} />

  <Panel>
    {#if loading}
      <p class="digest-page__status">{$_('insights.digest.loading')}</p>
    {:else if error}
      <InlineAlert variant="info" message={error} />
      <div class="digest-page__actions">
        <Button variant="secondary" type="button" on:click={() => void goto('/settings')}>
          {$_('insights.digest.open_settings')}
        </Button>
      </div>
    {:else if digest}
      <p class="digest-page__range">
        {$_('insights.digest.range', {
          values: { start: digest.week_start, end: digest.week_end },
        })}
      </p>
      <ul class="digest-page__list">
        {#each digest.insights as item (item.id)}
          <li>
            <InsightCard
              insight={toInsightResponse(item)}
              showMaturityBadge={false}
              dismissable={false}
            />
          </li>
        {/each}
      </ul>
    {/if}
  </Panel>
</div>

<style>
  .digest-page {
    display: grid;
    gap: var(--space-4);
    padding: var(--space-4);
  }

  .digest-page__back {
    margin: 0;
  }

  .digest-page__status,
  .digest-page__range {
    margin: 0;
    color: var(--color-text-muted);
  }

  .digest-page__list {
    list-style: none;
    margin: var(--space-4) 0 0;
    padding: 0;
    display: grid;
    gap: var(--space-3);
  }

  .digest-page__actions {
    margin-top: var(--space-4);
  }
</style>
