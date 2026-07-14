<script lang="ts">
  import { _ } from 'svelte-i18n';
  import type { TagClusterMember, TagClustersResponse } from '$lib/api/insights';
  import {
    getTagGroupsInsufficientKey,
    getTagGroupsInsufficientValues,
    getTagGroupsSubtitleKey,
    showTagClusterMaturityBadge,
  } from '$lib/utils/tagGroupsPresentation';

  export let data: TagClustersResponse | null = null;
  export let loading = false;

  $: showSkeleton = loading && !data;
  $: clusters = data?.status === 'ok' ? data.clusters : [];
  $: subtitleKey = getTagGroupsSubtitleKey(data);
  $: maturityBadgeData = showTagClusterMaturityBadge(data) ? data : null;
  $: maturityBadgeKey = maturityBadgeData
    ? `insights.tag_groups.badge.${maturityBadgeData.cluster_maturity}`
    : null;
  $: maturityTooltipKey = maturityBadgeData
    ? `insights.tag_groups.badge.${maturityBadgeData.cluster_maturity}_tooltip`
    : null;

  function memberLabel(member: TagClusterMember): string {
    if (member.kind === 'symptom' && member.icon) {
      return `${member.icon} ${member.name}`;
    }
    return member.name;
  }

  function clusterMembers(cluster: (typeof clusters)[number]): TagClusterMember[] {
    if (cluster.members.length > 0) return cluster.members;
    return cluster.tags.map((tag) => ({
      kind: 'tag' as const,
      signal_id: tag.tag_id,
      slug: tag.slug,
      name: tag.name,
      category: tag.category,
      color: tag.color,
    }));
  }
</script>

<section class="tag-groups" data-loading={loading ? 'true' : 'false'} data-layout="responsive">
  <header class="tag-groups__header">
    <div class="tag-groups__title-row">
      <div>
        <h2>{$_('insights.tag_groups.heading')}</h2>
        <p>{$_(subtitleKey)}</p>
      </div>
      {#if maturityBadgeData && maturityBadgeKey}
        <span
          class="tag-groups__badge tag-groups__badge--uncertain"
          data-testid="tag-groups-maturity-badge"
          data-maturity={maturityBadgeData.cluster_maturity}
          title={maturityTooltipKey ? $_(maturityTooltipKey) : undefined}
          aria-label={maturityTooltipKey ? $_(maturityTooltipKey) : undefined}
        >
          <span aria-hidden="true">!</span>
          {$_(maturityBadgeKey, { values: { entries: maturityBadgeData.entry_count } })}
        </span>
      {/if}
    </div>
  </header>

  {#if showSkeleton}
    <div class="tag-groups__skeleton" role="status" aria-label={$_('insights.tag_groups.loading')}>
      <span></span>
      <span></span>
      <span></span>
    </div>
  {:else if data?.status === 'insufficient_data'}
    <div class="tag-groups__empty">
      <p>
        {$_(getTagGroupsInsufficientKey(data), {
          values: getTagGroupsInsufficientValues(data),
        })}
      </p>
    </div>
  {:else if clusters.length > 0}
    <div class="tag-groups__grid">
      {#each clusters as cluster}
        <article class="tag-groups__card">
          <div class="tag-groups__card-head">
            <h3>{cluster.label}</h3>
            <span
              >{$_('insights.tag_groups.strength', {
                values: { value: Math.round(cluster.strength * 100) },
              })}</span
            >
          </div>
          <ul class="tag-groups__chips" aria-label={cluster.label}>
            {#each clusterMembers(cluster) as member (member.signal_id)}
              <li
                class:tag-groups__chip--symptom={member.kind === 'symptom'}
                style={member.color ? `--chip-color: ${member.color}` : undefined}
              >
                {memberLabel(member)}
              </li>
            {/each}
          </ul>
        </article>
      {/each}
    </div>
  {:else if !loading}
    <div class="tag-groups__empty">
      <p>{$_('insights.tag_groups.empty')}</p>
    </div>
  {/if}
</section>

<style>
  .tag-groups {
    display: flex;
    flex-direction: column;
    gap: var(--space-3);
    padding: var(--space-4);
    border-radius: var(--radius-md);
    border: 1px solid var(--color-border-chart);
    background: var(--color-surface-chart-bg);
    min-width: 0;
    max-width: 100%;
    box-sizing: border-box;
  }

  .tag-groups__header h2,
  .tag-groups__header p,
  .tag-groups__card h3,
  .tag-groups__empty p {
    margin: 0;
  }

  .tag-groups__title-row {
    display: flex;
    justify-content: space-between;
    align-items: flex-start;
    gap: var(--space-3);
  }

  .tag-groups__header h2 {
    font-size: var(--text-lg);
  }

  .tag-groups__header p,
  .tag-groups__empty {
    color: var(--color-text-muted);
    font-size: var(--text-sm);
  }

  .tag-groups__badge {
    display: inline-flex;
    align-items: center;
    gap: var(--space-1);
    flex-shrink: 0;
    padding: var(--space-1) var(--space-2);
    border-radius: var(--radius-full);
    background: var(--color-primary-highlight);
    color: var(--color-primary);
    font-size: var(--text-xs);
    font-weight: 700;
    white-space: nowrap;
  }

  .tag-groups__badge--uncertain {
    background: color-mix(in srgb, var(--color-warning) 18%, var(--color-surface));
    color: var(--color-text);
    border: 1px solid color-mix(in srgb, var(--color-warning) 35%, transparent);
  }

  .tag-groups__grid {
    display: grid;
    gap: var(--space-3);
    grid-template-columns: repeat(auto-fit, minmax(13rem, 1fr));
  }

  .tag-groups__card {
    display: grid;
    gap: var(--space-3);
    padding: var(--space-3);
    border: 1px solid var(--color-border);
    border-radius: var(--radius-md);
    background: var(--color-surface);
  }

  .tag-groups__card-head {
    display: flex;
    justify-content: space-between;
    gap: var(--space-2);
    align-items: baseline;
  }

  .tag-groups__card-head h3 {
    font-size: var(--text-base);
  }

  .tag-groups__card-head span {
    color: var(--color-text-muted);
    font-size: var(--text-xs);
    font-weight: 700;
  }

  .tag-groups__chips {
    display: flex;
    flex-wrap: wrap;
    gap: var(--space-2);
    padding: 0;
    margin: 0;
    list-style: none;
  }

  .tag-groups__chips li {
    padding: var(--space-1) var(--space-2);
    border-radius: var(--radius-full);
    background: var(--color-primary-highlight);
    color: var(--color-primary);
    font-size: var(--text-xs);
    font-weight: 700;
  }

  .tag-groups__chip--symptom {
    background: color-mix(in srgb, var(--color-warning) 18%, var(--color-surface));
    color: var(--color-text);
    border: 1px dashed var(--color-border);
  }

  .tag-groups__skeleton {
    display: grid;
    gap: var(--space-2);
  }

  .tag-groups__skeleton span {
    min-height: 2rem;
    border-radius: var(--radius-sm);
    background: var(--color-surface-dynamic);
  }

  @media (max-width: 480px) {
    .tag-groups__title-row {
      flex-direction: column;
      align-items: stretch;
    }

    .tag-groups__grid {
      grid-template-columns: 1fr;
    }

    .tag-groups__card-head {
      flex-direction: column;
      align-items: flex-start;
    }

    .tag-groups__chips {
      flex-direction: column;
      flex-wrap: nowrap;
      align-items: stretch;
    }

    .tag-groups__chips li {
      width: 100%;
      box-sizing: border-box;
      text-align: left;
    }
  }
</style>
