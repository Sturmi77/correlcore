import { describe, expect, it } from 'vitest';
import type { TagHeatmapResponse, TagHeatmapTag } from '$lib/api/stats';
import { rankRecentTagIds } from './recentTags';

function tag(partial: Partial<TagHeatmapTag> & { tag_id: string; slug: string }): TagHeatmapTag {
  return {
    name: partial.slug,
    category: 'other',
    color: null,
    days: [],
    ...partial,
  };
}

function heatmap(tags: TagHeatmapTag[]): TagHeatmapResponse {
  return { start_date: '2026-01-01', end_date: '2026-01-14', tags };
}

describe('rankRecentTagIds', () => {
  it('returns [] for a null heatmap or non-positive limit', () => {
    expect(rankRecentTagIds(null, 5)).toEqual([]);
    expect(rankRecentTagIds(heatmap([tag({ tag_id: 'a', slug: 'a' })]), 0)).toEqual([]);
  });

  it('orders by total usage count, then most recent day, then slug', () => {
    const result = rankRecentTagIds(
      heatmap([
        tag({
          tag_id: 'sport',
          slug: 'sport',
          days: [
            { date: '2026-01-10', count: 1 },
            { date: '2026-01-12', count: 2 },
          ],
        }),
        tag({ tag_id: 'work', slug: 'work', days: [{ date: '2026-01-14', count: 1 }] }),
        tag({ tag_id: 'read', slug: 'read', days: [{ date: '2026-01-09', count: 1 }] }),
      ]),
      5
    );
    // sport=3, then work vs read both 1 → work used more recently (01-14 > 01-09).
    expect(result).toEqual(['sport', 'work', 'read']);
  });

  it('breaks count+recency ties by slug for stable ordering', () => {
    const result = rankRecentTagIds(
      heatmap([
        tag({ tag_id: 'beta-id', slug: 'beta', days: [{ date: '2026-01-14', count: 1 }] }),
        tag({ tag_id: 'alpha-id', slug: 'alpha', days: [{ date: '2026-01-14', count: 1 }] }),
      ]),
      5
    );
    expect(result).toEqual(['alpha-id', 'beta-id']);
  });

  it('drops zero-count tags and caps at the limit', () => {
    const result = rankRecentTagIds(
      heatmap([
        tag({ tag_id: 'a', slug: 'a', days: [{ date: '2026-01-10', count: 5 }] }),
        tag({ tag_id: 'b', slug: 'b', days: [{ date: '2026-01-11', count: 4 }] }),
        tag({ tag_id: 'c', slug: 'c', days: [{ date: '2026-01-12', count: 3 }] }),
        tag({ tag_id: 'empty', slug: 'empty', days: [] }),
      ]),
      2
    );
    expect(result).toEqual(['a', 'b']);
  });
});
