/**
 * Static demo fixtures for the anonymous marketing landing.
 * No auth/API — representative product shots only.
 */
import type { TagClustersResponse } from '$lib/api/insights';
import type { TimeseriesPoint } from '$lib/api/stats';

export const landingTagClusters: TagClustersResponse = {
  status: 'ok',
  entry_count: 60,
  active_tag_count: 6,
  active_signal_count: 7,
  window_days: 90,
  k: 2,
  reason: null,
  cluster_kind: 'mixed',
  cluster_maturity: 'provisional',
  cluster_mode: 'kmeans',
  entries_until_robust: 30,
  silhouette_score: 0.18,
  clusters: [
    {
      cluster_id: 1,
      label: 'Poor-sleep cluster',
      cluster_kind: 'mixed',
      strength: 0.74,
      tags: [
        {
          tag_id: 'demo-poor-sleep',
          slug: 'poor-sleep',
          name: 'Poor sleep',
          category: 'sleep',
          color: null,
        },
        {
          tag_id: 'demo-low-energy',
          slug: 'low-energy',
          name: 'Low energy',
          category: 'energy',
          color: null,
        },
      ],
      members: [
        {
          kind: 'tag',
          signal_id: 'demo-poor-sleep',
          slug: 'poor-sleep',
          name: 'Poor sleep',
          category: 'sleep',
          color: null,
        },
        {
          kind: 'symptom',
          signal_id: 'demo-headache',
          slug: 'headache',
          name: 'Headache',
          category: 'symptom',
          color: null,
          icon: '🤕',
        },
        {
          kind: 'tag',
          signal_id: 'demo-low-energy',
          slug: 'low-energy',
          name: 'Low energy',
          category: 'energy',
          color: null,
        },
      ],
    },
    {
      cluster_id: 2,
      label: 'Active days',
      cluster_kind: 'tags_only',
      strength: 0.68,
      tags: [
        {
          tag_id: 'demo-exercise',
          slug: 'exercise',
          name: 'Exercise',
          category: 'activity',
          color: null,
        },
        {
          tag_id: 'demo-good-mood',
          slug: 'good-mood',
          name: 'Good mood',
          category: 'mood',
          color: null,
        },
      ],
      members: [
        {
          kind: 'tag',
          signal_id: 'demo-exercise',
          slug: 'exercise',
          name: 'Exercise',
          category: 'activity',
          color: null,
        },
        {
          kind: 'tag',
          signal_id: 'demo-good-mood',
          slug: 'good-mood',
          name: 'Good mood',
          category: 'mood',
          color: null,
        },
      ],
    },
  ],
};

export const landingTimeseriesPoints: TimeseriesPoint[] = [
  {
    period_start: '2026-07-13',
    period_end: '2026-07-13',
    entry_count: 1,
    mood_avg: 3.2,
    energy_avg: 3.0,
    stress_avg: 2.8,
  },
  {
    period_start: '2026-07-14',
    period_end: '2026-07-14',
    entry_count: 1,
    mood_avg: 3.6,
    energy_avg: 3.4,
    stress_avg: 2.5,
  },
  {
    period_start: '2026-07-15',
    period_end: '2026-07-15',
    entry_count: 1,
    mood_avg: 3.1,
    energy_avg: 2.9,
    stress_avg: 3.2,
  },
  {
    period_start: '2026-07-16',
    period_end: '2026-07-16',
    entry_count: 1,
    mood_avg: 3.9,
    energy_avg: 3.7,
    stress_avg: 2.2,
  },
  {
    period_start: '2026-07-17',
    period_end: '2026-07-17',
    entry_count: 1,
    mood_avg: 4.1,
    energy_avg: 3.8,
    stress_avg: 2.0,
  },
  {
    period_start: '2026-07-18',
    period_end: '2026-07-18',
    entry_count: 1,
    mood_avg: 3.7,
    energy_avg: 3.5,
    stress_avg: 2.4,
  },
  {
    period_start: '2026-07-19',
    period_end: '2026-07-19',
    entry_count: 1,
    mood_avg: 3.8,
    energy_avg: 3.6,
    stress_avg: 2.3,
  },
];
