import type { TagHeatmapResponse } from '$lib/api/stats';

/**
 * Rank tags by recent usage for the TagPicker "Recently used" cloud (#898).
 *
 * Source is the existing tag-frequency heatmap (`GET /entries/stats/tags`),
 * already scoped to a date window by the caller. Ranking is:
 *   1. total usage count in the window (desc),
 *   2. most recent day used (desc) — ties broken toward what was logged last,
 *   3. slug (asc) — a stable, locale-independent final tiebreak.
 *
 * Returns canonical tag IDs, most relevant first, capped at `limit`. Tags with
 * a zero count in the window are dropped.
 */
export function rankRecentTagIds(heatmap: TagHeatmapResponse | null, limit: number): string[] {
  if (!heatmap || limit <= 0) return [];

  const ranked = heatmap.tags
    .map((tag) => {
      let count = 0;
      let lastUsed = '';
      for (const day of tag.days) {
        count += day.count;
        if (day.date > lastUsed) lastUsed = day.date;
      }
      return { tagId: tag.tag_id, slug: tag.slug, count, lastUsed };
    })
    .filter((entry) => entry.count > 0);

  ranked.sort(
    (a, b) =>
      b.count - a.count || b.lastUsed.localeCompare(a.lastUsed) || a.slug.localeCompare(b.slug)
  );

  return ranked.slice(0, limit).map((entry) => entry.tagId);
}
