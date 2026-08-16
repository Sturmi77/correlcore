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
    expect(screen.getByText('insights.tag_groups.card_title:{"name":"Movement"}')).toBeTruthy();
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

  it('renders a strength band as the primary read with the % as detail (#706)', () => {
    const { container } = render(TagGroupsSection, {
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
          strength_floor: 0.22,
          shown_cluster_count: 1,
          omitted_signal_count: 0,
          clusters: [
            {
              cluster_id: 1,
              label: 'Movement',
              cluster_kind: 'tags_only',
              strength: 0.72, // headroom (0.72-0.22)/0.78 = 0.64 -> strong
              members: [],
              tags: [{ tag_id: '1', slug: 'sport', name: 'Sport', category: 'sport', color: null }],
            },
          ],
        },
      },
    });

    const band = container.querySelector('[data-band]');
    expect(band?.getAttribute('data-band')).toBe('strong');
    expect(band?.textContent).toContain('insights.tag_groups.strength_band.strong');
    expect(band?.textContent).toContain('insights.tag_groups.strength_detail:{"value":72}');
    // omitted_signal_count 0 -> no hint
    expect(screen.queryByTestId('tag-groups-omitted')).toBeNull();
  });

  it('shows the omitted-tags hint when signals were left out (#706)', () => {
    render(TagGroupsSection, {
      props: {
        data: {
          status: 'ok',
          entry_count: 100,
          active_tag_count: 8,
          active_signal_count: 8,
          window_days: 90,
          k: 2,
          reason: null,
          cluster_kind: 'tags_only',
          cluster_maturity: 'robust',
          cluster_mode: 'kmeans',
          entries_until_robust: null,
          strength_floor: 0.22,
          shown_cluster_count: 2,
          omitted_signal_count: 3,
          clusters: [
            {
              cluster_id: 1,
              label: 'A',
              cluster_kind: 'tags_only',
              strength: 0.8,
              members: [],
              tags: [{ tag_id: '1', slug: 'a', name: 'A', category: 'sport', color: null }],
            },
            {
              cluster_id: 2,
              label: 'B',
              cluster_kind: 'tags_only',
              strength: 0.5,
              members: [],
              tags: [{ tag_id: '2', slug: 'b', name: 'B', category: 'work', color: null }],
            },
          ],
        },
      },
    });

    const hint = screen.getByTestId('tag-groups-omitted');
    expect(hint.textContent).toContain('insights.tag_groups.omitted');
    expect(hint.textContent).toContain('"omitted":3');
    expect(hint.textContent).toContain('"shown":2');
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
