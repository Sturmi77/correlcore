import type { TagCooccurrencePair, TagCooccurrenceTagRef } from '$lib/api/insights';
import { orderAxisIds, type CooccurrenceSortMode } from '$lib/utils/cooccurrenceClusterOrder';

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

export function orderTagCooccurrenceMatrix(
  matrix: TagCooccurrenceMatrix,
  sortMode: CooccurrenceSortMode
): TagCooccurrenceMatrix {
  const profiles = tagCooccurrenceProfiles(matrix);
  const orderedIds = orderAxisIds(
    matrix.tags.map((tag) => tag.tag_id),
    profiles,
    sortMode,
    (id) => matrix.tags.find((tag) => tag.tag_id === id)?.name ?? id
  );
  const indexById = new Map(matrix.tags.map((tag, index) => [tag.tag_id, index]));
  const order = orderedIds
    .map((id) => indexById.get(id))
    .filter((index): index is number => index !== undefined);

  return {
    tags: order.map((index) => matrix.tags[index]),
    counts: order.map((row) => order.map((col) => matrix.counts[row][col])),
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
