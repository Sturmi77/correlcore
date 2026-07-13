import { render, screen } from '@testing-library/svelte';
import { describe, expect, it, vi } from 'vitest';
import TagGroupsSection from './TagGroupsSection.svelte';

vi.mock('svelte-i18n', async () => {
  const { readable } = await import('svelte/store');
  return {
    _: readable((key: string, options?: { values?: Record<string, unknown> }) => {
      if (options?.values) return `${key}:${JSON.stringify(options.values)}`;
      return key;
    }),
  };
});

describe('TagGroupsSection', () => {
  it('renders tag groups when status is ok', () => {
    render(TagGroupsSection, {
      props: {
        data: {
          status: 'ok',
          entry_count: 100,
          active_tag_count: 6,
          active_signal_count: 6,
          window_days: 90,
          k: 3,
          reason: null,
          cluster_kind: 'tags_only',
          cluster_maturity: 'robust',
          cluster_mode: 'kmeans',
          entries_until_robust: null,
          clusters: [
            {
              cluster_id: 1,
              label: 'Movement',
              cluster_kind: 'tags_only',
              strength: 0.72,
              members: [
                {
                  kind: 'tag',
                  signal_id: '1',
                  slug: 'sport',
                  name: 'Sport',
                  category: 'sport',
                  color: null,
                },
              ],
              tags: [{ tag_id: '1', slug: 'sport', name: 'Sport', category: 'sport', color: null }],
            },
          ],
        },
      },
    });

    expect(screen.getByText('insights.tag_groups.heading')).toBeTruthy();
    expect(screen.getByText('Movement')).toBeTruthy();
    expect(screen.getByText('Sport')).toBeTruthy();
    expect(screen.queryByTestId('tag-groups-maturity-badge')).toBeNull();
  });

  it('shows provisional maturity badge for 67-day profile', () => {
    render(TagGroupsSection, {
      props: {
        data: {
          status: 'ok',
          entry_count: 67,
          active_tag_count: 6,
          active_signal_count: 6,
          window_days: 67,
          k: 3,
          reason: null,
          cluster_kind: 'tags_only',
          cluster_maturity: 'provisional',
          cluster_mode: 'kmeans',
          entries_until_robust: 23,
          silhouette_score: 0.115,
          clusters: [
            {
              cluster_id: 1,
              label: 'Tag group 1',
              cluster_kind: 'tags_only',
              strength: 0.72,
              members: [],
              tags: [{ tag_id: '1', slug: 'sport', name: 'Sport', category: 'sport', color: null }],
            },
          ],
        },
      },
    });

    const badge = screen.getByTestId('tag-groups-maturity-badge');
    expect(badge.getAttribute('data-maturity')).toBe('provisional');
    expect(badge.textContent).toContain('insights.tag_groups.badge.provisional');
    expect(screen.getByText('insights.tag_groups.subtitle_kmeans_provisional')).toBeTruthy();
  });

  it('shows pair subtitle for early cluster mode', () => {
    render(TagGroupsSection, {
      props: {
        data: {
          status: 'ok',
          entry_count: 35,
          active_tag_count: 6,
          active_signal_count: 6,
          window_days: 35,
          k: null,
          reason: null,
          cluster_kind: 'tags_only',
          cluster_maturity: 'early',
          cluster_mode: 'pair',
          entries_until_robust: 55,
          clusters: [
            {
              cluster_id: 1,
              label: 'Tag group 1',
              cluster_kind: 'tags_only',
              strength: 0.6,
              members: [],
              tags: [{ tag_id: '1', slug: 'sport', name: 'Sport', category: 'sport', color: null }],
            },
          ],
        },
      },
    });

    expect(screen.getByText('insights.tag_groups.subtitle_pair')).toBeTruthy();
    expect(screen.getByTestId('tag-groups-maturity-badge').getAttribute('data-maturity')).toBe(
      'early'
    );
  });

  it('shows progress copy for 25-day insufficient state', () => {
    render(TagGroupsSection, {
      props: {
        data: {
          status: 'insufficient_data',
          entry_count: 25,
          active_tag_count: 4,
          active_signal_count: 4,
          window_days: 25,
          k: null,
          reason: 'entry_count_below_30',
          cluster_kind: 'tags_only',
          entries_until_robust: 65,
          clusters: [],
        },
      },
    });

    expect(
      screen.getByText(
        'insights.tag_groups.insufficient_below_pair:{"entries":25,"remaining":5,"target":30,"tags":4}'
      )
    ).toBeTruthy();
  });
});
