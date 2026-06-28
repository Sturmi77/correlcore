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
  });

  it('shows insufficient data copy', () => {
    render(TagGroupsSection, {
      props: {
        data: {
          status: 'insufficient_data',
          entry_count: 12,
          active_tag_count: 2,
          active_signal_count: 2,
          window_days: 90,
          k: null,
          reason: 'entries',
          cluster_kind: 'tags_only',
          clusters: [],
        },
      },
    });

    expect(screen.getByText(/insights.tag_groups.insufficient/)).toBeTruthy();
  });
});
