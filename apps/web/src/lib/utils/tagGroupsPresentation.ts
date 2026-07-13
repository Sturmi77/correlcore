import type { TagClustersResponse } from '$lib/api/insights';

export const TAG_CLUSTER_MIN_PAIR_ENTRIES = 30;
export const TAG_CLUSTER_MIN_PROVISIONAL_ENTRIES = 45;
export const TAG_CLUSTER_MIN_ROBUST_ENTRIES = 90;
export const TAG_CLUSTER_MIN_ACTIVE_SIGNALS = 5;

export type TagGroupsSubtitleKey =
  | 'insights.tag_groups.subtitle'
  | 'insights.tag_groups.subtitle_mixed'
  | 'insights.tag_groups.subtitle_pair'
  | 'insights.tag_groups.subtitle_kmeans_provisional';

export type TagGroupsInsufficientKey =
  | 'insights.tag_groups.insufficient_below_pair'
  | 'insights.tag_groups.insufficient_below_provisional'
  | 'insights.tag_groups.insufficient_below_robust'
  | 'insights.tag_groups.insufficient_tags'
  | 'insights.tag_groups.insufficient_generic';

export function showTagClusterMaturityBadge(
  data: TagClustersResponse | null | undefined
): data is TagClustersResponse & {
  cluster_maturity: 'early' | 'provisional';
} {
  return (
    data?.status === 'ok' &&
    (data.cluster_maturity === 'early' || data.cluster_maturity === 'provisional')
  );
}

export function getTagGroupsSubtitleKey(data: TagClustersResponse | null): TagGroupsSubtitleKey {
  if (!data || data.status !== 'ok') {
    return data?.cluster_kind === 'mixed'
      ? 'insights.tag_groups.subtitle_mixed'
      : 'insights.tag_groups.subtitle';
  }

  if (data.cluster_kind === 'mixed' && data.cluster_maturity === 'robust') {
    return 'insights.tag_groups.subtitle_mixed';
  }

  if (data.cluster_mode === 'pair') {
    return 'insights.tag_groups.subtitle_pair';
  }

  if (data.cluster_maturity === 'provisional') {
    return 'insights.tag_groups.subtitle_kmeans_provisional';
  }

  return data.cluster_kind === 'mixed'
    ? 'insights.tag_groups.subtitle_mixed'
    : 'insights.tag_groups.subtitle';
}

export function getTagGroupsInsufficientKey(data: TagClustersResponse): TagGroupsInsufficientKey {
  const activeSignals = data.active_signal_count || data.active_tag_count;

  if (
    activeSignals < TAG_CLUSTER_MIN_ACTIVE_SIGNALS &&
    data.entry_count >= TAG_CLUSTER_MIN_PAIR_ENTRIES
  ) {
    return 'insights.tag_groups.insufficient_tags';
  }

  if (data.entry_count < TAG_CLUSTER_MIN_PAIR_ENTRIES) {
    return 'insights.tag_groups.insufficient_below_pair';
  }

  if (data.entry_count < TAG_CLUSTER_MIN_PROVISIONAL_ENTRIES) {
    return 'insights.tag_groups.insufficient_below_provisional';
  }

  if (data.entry_count < TAG_CLUSTER_MIN_ROBUST_ENTRIES) {
    return 'insights.tag_groups.insufficient_below_robust';
  }

  return 'insights.tag_groups.insufficient_generic';
}

export function getTagGroupsInsufficientValues(data: TagClustersResponse): Record<string, number> {
  const activeSignals = data.active_signal_count || data.active_tag_count;
  const entriesUntilRobust =
    data.entries_until_robust ?? Math.max(0, TAG_CLUSTER_MIN_ROBUST_ENTRIES - data.entry_count);

  if (data.entry_count < TAG_CLUSTER_MIN_PAIR_ENTRIES) {
    return {
      entries: data.entry_count,
      remaining: TAG_CLUSTER_MIN_PAIR_ENTRIES - data.entry_count,
      target: TAG_CLUSTER_MIN_PAIR_ENTRIES,
      tags: activeSignals,
    };
  }

  if (activeSignals < TAG_CLUSTER_MIN_ACTIVE_SIGNALS) {
    return {
      entries: data.entry_count,
      tags: activeSignals,
      target: TAG_CLUSTER_MIN_ACTIVE_SIGNALS,
    };
  }

  if (data.entry_count < TAG_CLUSTER_MIN_PROVISIONAL_ENTRIES) {
    return {
      entries: data.entry_count,
      remaining: TAG_CLUSTER_MIN_PROVISIONAL_ENTRIES - data.entry_count,
      target: TAG_CLUSTER_MIN_PROVISIONAL_ENTRIES,
      tags: activeSignals,
    };
  }

  return {
    entries: data.entry_count,
    remaining: entriesUntilRobust,
    target: TAG_CLUSTER_MIN_ROBUST_ENTRIES,
    tags: activeSignals,
  };
}
