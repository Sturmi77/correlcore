/**
 * Average-linkage hierarchical clustering for co-occurrence heatmap axis reorder (#150).
 */

export type CooccurrenceSortMode = 'alphabetical' | 'clustered';

function euclideanDistance(a: number[], b: number[]): number {
  const length = Math.max(a.length, b.length);
  let sum = 0;
  for (let index = 0; index < length; index += 1) {
    const delta = (a[index] ?? 0) - (b[index] ?? 0);
    sum += delta * delta;
  }
  return Math.sqrt(sum);
}

function averageLinkageDistance(
  left: string[],
  right: string[],
  distance: (a: string, b: string) => number
): number {
  if (left.length === 0 || right.length === 0) return Number.POSITIVE_INFINITY;
  let total = 0;
  for (const a of left) {
    for (const b of right) {
      total += distance(a, b);
    }
  }
  return total / (left.length * right.length);
}

interface ClusterNode {
  id: number;
  members: string[];
  left?: ClusterNode;
  right?: ClusterNode;
}

function leafOrder(node: ClusterNode): string[] {
  if (!node.left || !node.right) return [...node.members];
  return [...leafOrder(node.left), ...leafOrder(node.right)];
}

/** Reorder ids with average-linkage hierarchical clustering on a distance function. */
export function hierarchicalClusterOrder(
  ids: readonly string[],
  distance: (a: string, b: string) => number
): string[] {
  if (ids.length <= 2) return [...ids];

  let nextId = ids.length;
  let clusters: ClusterNode[] = ids.map((id, index) => ({ id: index, members: [id] }));

  while (clusters.length > 1) {
    let bestDistance = Number.POSITIVE_INFINITY;
    let bestPair: [number, number] | null = null;

    for (let leftIndex = 0; leftIndex < clusters.length; leftIndex += 1) {
      for (let rightIndex = leftIndex + 1; rightIndex < clusters.length; rightIndex += 1) {
        const candidate = averageLinkageDistance(
          clusters[leftIndex].members,
          clusters[rightIndex].members,
          distance
        );
        if (candidate < bestDistance) {
          bestDistance = candidate;
          bestPair = [leftIndex, rightIndex];
        }
      }
    }

    if (!bestPair) break;

    const [leftIndex, rightIndex] = bestPair;
    const left = clusters[leftIndex];
    const right = clusters[rightIndex];
    const [first, second] =
      left.members.length >= right.members.length ? [left, right] : [right, left];
    const merged: ClusterNode = {
      id: nextId,
      members: [...first.members, ...second.members],
      left: first,
      right: second,
    };
    nextId += 1;
    clusters = clusters.filter((_, index) => index !== leftIndex && index !== rightIndex);
    clusters.push(merged);
  }

  return leafOrder(clusters[0]);
}

/** Build Jaccard-profile distance for symptom rows or tag columns. */
export function buildProfileDistance(
  profiles: Map<string, number[]>,
  ids: readonly string[]
): (a: string, b: string) => number {
  const maxLength = ids.reduce((max, id) => Math.max(max, profiles.get(id)?.length ?? 0), 0);
  const normalized = new Map<string, number[]>();
  for (const id of ids) {
    const profile = profiles.get(id) ?? [];
    if (maxLength === 0) {
      normalized.set(id, []);
      continue;
    }
    const values = Array.from({ length: maxLength }, (_, index) => profile[index] ?? 0);
    const norm = Math.sqrt(values.reduce((sum, value) => sum + value * value, 0)) || 1;
    normalized.set(
      id,
      values.map((value) => value / norm)
    );
  }

  return (a: string, b: string) => {
    const left = normalized.get(a) ?? [];
    const right = normalized.get(b) ?? [];
    if (left.length === 0 && right.length === 0) return 0;
    return euclideanDistance(left, right);
  };
}

export function orderAxisIds(
  ids: readonly string[],
  profiles: Map<string, number[]>,
  sortMode: CooccurrenceSortMode,
  labelFor: (id: string) => string
): string[] {
  const unique = [...new Set(ids)];
  if (sortMode === 'clustered' && unique.length > 2) {
    const distance = buildProfileDistance(profiles, unique);
    return hierarchicalClusterOrder(unique, distance);
  }
  return [...unique].sort((a, b) => labelFor(a).localeCompare(labelFor(b)));
}
