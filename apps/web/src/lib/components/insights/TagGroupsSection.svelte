<script lang="ts">
  import { _ } from 'svelte-i18n';
  import type { TagClusterMember, TagClustersResponse } from '$lib/api/insights';

  export let data: TagClustersResponse | null = null;
  export let loading = false;

  $: showSkeleton = loading && !data;
  $: clusters = data?.status === 'ok' ? data.clusters : [];
  $: mixedClusters = data?.cluster_kind === 'mixed';

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

<section class="tag-groups" data-loading={loading ? 'true' : 'false'}>
  <header class="tag-groups__header">
    <div>
      <h2>{$_('insights.tag_groups.heading')}</h2>
      <p>
        {mixedClusters
          ? $_('insights.tag_groups.subtitle_mixed')
          : $_('insights.tag_groups.subtitle')}
      </p>
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
        {$_('insights.tag_groups.insufficient', {
          values: {
            entries: data.entry_count,
            tags: data.active_signal_count || data.active_tag_count,
          },
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
  }

  .tag-groups__header h2,
  .tag-groups__header p,
  .tag-groups__card h3,
  .tag-groups__empty p {
    margin: 0;
  }

  .tag-groups__header h2 {
    font-size: var(--text-lg);
  }

  .tag-groups__header p,
  .tag-groups__empty {
    color: var(--color-text-muted);
    font-size: var(--text-sm);
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
    border-radius: 999px;
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
</style>
