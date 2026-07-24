import { describe, expect, it } from 'vitest';
import type { TagCooccurrencePair } from '$lib/api/insights';
import {
  buildTagCooccurrenceMatrix,
  cooccurrenceIntensityLevel,
  orderTagIdsByCluster,
  orderTagCooccurrenceMatrix,
  focusTagCooccurrenceMatrixOnCluster,
  buildTagClusterMeta,
} from '$lib/utils/tagCooccurrenceMatrix';

const pairs: TagCooccurrencePair[] = [
  {
    tag_a: {
      tag_id: 'b-tag',
      slug: 'focus',
      name: 'Focus',
      category: 'work',
      color: null,
    },
    tag_b: {
      tag_id: 'a-tag',
      slug: 'walk',
      name: 'Walk',
      category: 'sport',
      color: null,
    },
    count: 4,
    pct_of_a: 80,
    pct_of_b: 66.7,
  },
  {
    tag_a: {
      tag_id: 'c-tag',
      slug: 'coffee',
      name: 'Coffee',
      category: 'consumption',
      color: null,
    },
    tag_b: {
      tag_id: 'a-tag',
      slug: 'walk',
      name: 'Walk',
      category: 'sport',
      color: null,
    },
    count: 2,
    pct_of_a: 50,
    pct_of_b: 33.3,
  },
];

describe('tagCooccurrenceMatrix', () => {
  it('builds a symmetric matrix sorted by tag name', () => {
    const matrix = buildTagCooccurrenceMatrix(pairs);

    expect(matrix.tags.map((tag) => tag.name)).toEqual(['Coffee', 'Focus', 'Walk']);
    expect(matrix.counts[0][1]).toBe(0);
    expect(matrix.counts[0][2]).toBe(2);
    expect(matrix.counts[1][2]).toBe(4);
    expect(matrix.counts[2][1]).toBe(4);
  });

  it('maps intensity levels from count ratio', () => {
    expect(cooccurrenceIntensityLevel(0, 8)).toBe(0);
    expect(cooccurrenceIntensityLevel(2, 8)).toBe(1);
    expect(cooccurrenceIntensityLevel(8, 8)).toBe(4);
  });
});

describe('cluster ordering and focus (#489)', () => {
  const axisTags = [
    { tag_id: 't1', slug: 'walk', name: 'Walk' },
    { tag_id: 't2', slug: 'coffee', name: 'Coffee' },
    { tag_id: 't3', slug: 'focus', name: 'Focus' },
    { tag_id: 't4', slug: 'loner', name: 'Loner' },
  ];
  const counts = [
    [0, 3, 1, 0],
    [3, 0, 2, 0],
    [1, 2, 0, 0],
    [0, 0, 0, 0],
  ];
  const matrix = { tags: axisTags, counts };
  // t2,t3 in cluster 1; t1 in cluster 2; t4 ungrouped.
  const clusterByTagId = new Map([
    ['t2', 1],
    ['t3', 1],
    ['t1', 2],
  ]);

  it('orders by cluster_id then name, ungrouped tags last', () => {
    const order = orderTagIdsByCluster(axisTags, clusterByTagId);
    // cluster 1: Coffee(t2), Focus(t3) by name; cluster 2: Walk(t1); then t4.
    expect(order).toEqual(['t2', 't3', 't1', 't4']);
  });

  it('clustered sort uses the cluster map when tags are assigned', () => {
    const ordered = orderTagCooccurrenceMatrix(matrix, 'clustered', clusterByTagId);
    expect(ordered.tags.map((t) => t.tag_id)).toEqual(['t2', 't3', 't1', 't4']);
  });

  it('falls back to hierarchical clustering when no tag is in a cluster', () => {
    const emptyMap = new Map<string, number>();
    const withMap = orderTagCooccurrenceMatrix(matrix, 'clustered', emptyMap);
    const withoutMap = orderTagCooccurrenceMatrix(matrix, 'clustered');
    // Same result: the empty map must not change behaviour vs. no map at all.
    expect(withMap.tags.map((t) => t.tag_id)).toEqual(withoutMap.tags.map((t) => t.tag_id));
  });

  it('focuses the matrix on a single cluster', () => {
    const focused = focusTagCooccurrenceMatrixOnCluster(matrix, clusterByTagId, 1);
    expect(focused.tags.map((t) => t.tag_id).sort()).toEqual(['t2', 't3']);
    expect(focused.counts).toEqual([
      [0, 2],
      [2, 0],
    ]);
  });

  it('returns the full matrix when the focused cluster has no axis tags', () => {
    const focused = focusTagCooccurrenceMatrixOnCluster(matrix, clusterByTagId, 99);
    expect(focused.tags.length).toBe(4);
  });
});

describe('buildTagClusterMeta (#489)', () => {
  const base = {
    entry_count: 120,
    active_tag_count: 5,
    active_signal_count: 5,
    window_days: 90,
    k: 2,
    reason: null,
    cluster_kind: 'tags_only' as const,
    cluster_maturity: 'robust' as const,
    cluster_mode: 'kmeans' as const,
    entries_until_robust: null,
    silhouette_score: 0.4,
  };

  it('maps tag members to cluster ids and collects labels', () => {
    const meta = buildTagClusterMeta({
      ...base,
      status: 'ok',
      clusters: [
        {
          cluster_id: 1,
          label: 'Morning',
          tags: [],
          members: [
            { kind: 'tag', signal_id: 't1', slug: 'walk', name: 'Walk' },
            { kind: 'symptom', signal_id: 's1', slug: 'ache', name: 'Ache' },
          ],
          cluster_kind: 'mixed',
          strength: 0.7,
        },
      ],
    } as never);
    expect(meta.byTagId.get('t1')).toBe(1);
    expect(meta.byTagId.has('s1')).toBe(false); // symptom member ignored
    expect(meta.labels).toEqual([{ cluster_id: 1, label: 'Morning' }]);
  });

  it('returns empty maps for insufficient_data', () => {
    const meta = buildTagClusterMeta({
      ...base,
      status: 'insufficient_data',
      clusters: [],
    } as never);
    expect(meta.byTagId.size).toBe(0);
    expect(meta.labels).toEqual([]);
  });
});
