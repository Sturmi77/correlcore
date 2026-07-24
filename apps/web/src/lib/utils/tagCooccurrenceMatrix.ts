import type {
  TagClustersResponse,
  TagCooccurrencePair,
  TagCooccurrenceTagRef,
} from '$lib/api/insights';
import { orderAxisIds, type CooccurrenceSortMode } from '$lib/utils/cooccurrenceClusterOrder';

export interface TagClusterMeta {
  /** tag signal id → cluster_id */
  byTagId: Map<string, number>;
  /** cluster_id → label, in cluster order, for the focus chips */
  labels: { cluster_id: number; label: string }[];
}

/**
 * Build the tag→cluster lookup for the co-occurrence heatmap (#489).
 *
 * Only `kind === 'tag'` members map to axes (the heatmap is tag×tag); symptom
 * members are ignored here. Returns empty maps unless the clusters are `ok`, so
 * `insufficient_data` transparently falls back to hierarchical ordering.
 */
export function buildTagClusterMeta(
  clusters: TagClustersResponse | null | undefined
): TagClusterMeta {
  const byTagId = new Map<string, number>();
  const labels: { cluster_id: number; label: string }[] = [];
  if (!clusters || clusters.status !== 'ok') return { byTagId, labels };

  for (const cluster of clusters.clusters) {
    let hasTag = false;
    const members = cluster.members.length
      ? cluster.members.filter((member) => member.kind === 'tag')
      : cluster.tags.map((tag) => ({ signal_id: tag.tag_id }));
    for (const member of members) {
      byTagId.set(member.signal_id, cluster.cluster_id);
      hasTag = true;
    }
    if (hasTag) labels.push({ cluster_id: cluster.cluster_id, label: cluster.label });
  }
  return { byTagId, labels };
}

export interface TagCooccurrenceAxisTag {
  tag_id: string;
  slug: string;
  name: string;
}

export interface TagCooccurrenceMatrix {
  tags: TagCooccurrenceAxisTag[];
  /** Symmetric counts; diagonal is always 0. */
  counts: number[][];
}

function tagKey(tag: TagCooccurrenceTagRef): string {
  return tag.tag_id;
}

function pairKey(tagAId: string, tagBId: string): string {
  return tagAId < tagBId ? `${tagAId}:${tagBId}` : `${tagBId}:${tagAId}`;
}

export function buildTagCooccurrenceMatrix(
  pairs: readonly TagCooccurrencePair[]
): TagCooccurrenceMatrix {
  const tagById = new Map<string, TagCooccurrenceAxisTag>();

  for (const pair of pairs) {
    tagById.set(tagKey(pair.tag_a), {
      tag_id: pair.tag_a.tag_id,
      slug: pair.tag_a.slug,
      name: pair.tag_a.name,
    });
    tagById.set(tagKey(pair.tag_b), {
      tag_id: pair.tag_b.tag_id,
      slug: pair.tag_b.slug,
      name: pair.tag_b.name,
    });
  }

  const tags = [...tagById.values()].sort((left, right) =>
    left.name.localeCompare(right.name, undefined, { sensitivity: 'base' })
  );
  const countsByPair = new Map<string, number>(
    pairs.map((pair) => [pairKey(pair.tag_a.tag_id, pair.tag_b.tag_id), pair.count])
  );

  const counts = tags.map((rowTag, rowIndex) =>
    tags.map((colTag, colIndex) => {
      if (rowIndex === colIndex) return 0;
      return countsByPair.get(pairKey(rowTag.tag_id, colTag.tag_id)) ?? 0;
    })
  );

  return { tags, counts };
}

export function tagCooccurrenceProfiles(matrix: TagCooccurrenceMatrix): Map<string, number[]> {
  return new Map(
    matrix.tags.map((tag, rowIndex) => [
      tag.tag_id,
      matrix.counts[rowIndex].map((value, colIndex) => (rowIndex === colIndex ? 0 : value)),
    ])
  );
}

/**
 * Order axis ids by server cluster (#489): cluster_id ascending, then name.
 *
 * Tags with no cluster assignment sort last, alphabetically, so an ungrouped
 * tail stays readable. Pure — the caller passes the `tagId → cluster_id` map
 * derived from `GET /insights/tag-clusters`.
 */
export function orderTagIdsByCluster(
  tags: readonly TagCooccurrenceAxisTag[],
  clusterByTagId: ReadonlyMap<string, number>
): string[] {
  const UNGROUPED = Number.POSITIVE_INFINITY;
  return [...tags]
    .sort((left, right) => {
      const leftCluster = clusterByTagId.get(left.tag_id) ?? UNGROUPED;
      const rightCluster = clusterByTagId.get(right.tag_id) ?? UNGROUPED;
      if (leftCluster !== rightCluster) return leftCluster - rightCluster;
      return left.name.localeCompare(right.name, undefined, { sensitivity: 'base' });
    })
    .map((tag) => tag.tag_id);
}

function reorderMatrix(
  matrix: TagCooccurrenceMatrix,
  orderedIds: readonly string[]
): TagCooccurrenceMatrix {
  const indexById = new Map(matrix.tags.map((tag, index) => [tag.tag_id, index]));
  const order = orderedIds
    .map((id) => indexById.get(id))
    .filter((index): index is number => index !== undefined);
  return {
    tags: order.map((index) => matrix.tags[index]),
    counts: order.map((row) => order.map((col) => matrix.counts[row][col])),
  };
}

export function orderTagCooccurrenceMatrix(
  matrix: TagCooccurrenceMatrix,
  sortMode: CooccurrenceSortMode,
  clusterByTagId?: ReadonlyMap<string, number>
): TagCooccurrenceMatrix {
  // #489: in "clustered" mode prefer the server co-occurrence clusters when at
  // least one axis tag is assigned; fall back to client-side hierarchical order
  // (the pre-#489 behaviour) when clusters are absent or insufficient.
  if (
    sortMode === 'clustered' &&
    clusterByTagId &&
    matrix.tags.some((tag) => clusterByTagId.has(tag.tag_id))
  ) {
    return reorderMatrix(matrix, orderTagIdsByCluster(matrix.tags, clusterByTagId));
  }

  const profiles = tagCooccurrenceProfiles(matrix);
  const orderedIds = orderAxisIds(
    matrix.tags.map((tag) => tag.tag_id),
    profiles,
    sortMode,
    (id) => matrix.tags.find((tag) => tag.tag_id === id)?.name ?? id
  );
  return reorderMatrix(matrix, orderedIds);
}

/**
 * Restrict a matrix to one cluster's tags (Focus cluster, #489).
 *
 * Returns the matrix unchanged when the cluster has no axis tags present, so a
 * focus on an off-screen cluster degrades to "show everything" rather than an
 * empty grid.
 */
export function focusTagCooccurrenceMatrixOnCluster(
  matrix: TagCooccurrenceMatrix,
  clusterByTagId: ReadonlyMap<string, number>,
  clusterId: number
): TagCooccurrenceMatrix {
  const keepIndexes = matrix.tags
    .map((tag, index) => (clusterByTagId.get(tag.tag_id) === clusterId ? index : -1))
    .filter((index) => index >= 0);
  if (keepIndexes.length === 0) return matrix;
  return {
    tags: keepIndexes.map((index) => matrix.tags[index]),
    counts: keepIndexes.map((row) => keepIndexes.map((col) => matrix.counts[row][col])),
  };
}

export function cooccurrenceIntensityLevel(count: number, max: number): number {
  if (count <= 0 || max <= 0) return 0;
  const ratio = count / max;
  if (ratio <= 0.25) return 1;
  if (ratio <= 0.5) return 2;
  if (ratio <= 0.75) return 3;
  return 4;
}
