import { describe, expect, it } from 'vitest';
import type { TagCooccurrencePair } from '$lib/api/insights';
import {
  buildTagCooccurrenceMatrix,
  cooccurrenceIntensityLevel,
} from '$lib/utils/tagCooccurrenceMatrix';

const pairs: TagCooccurrencePair[] = [
  {
    tag_a: {
      tag_id: 'b-tag',
      slug: 'focus',
      name: 'Focus',
      category: 'work',
      color: null,
    },
    tag_b: {
      tag_id: 'a-tag',
      slug: 'walk',
      name: 'Walk',
      category: 'sport',
      color: null,
    },
    count: 4,
    pct_of_a: 80,
    pct_of_b: 66.7,
  },
  {
    tag_a: {
      tag_id: 'c-tag',
      slug: 'coffee',
      name: 'Coffee',
      category: 'consumption',
      color: null,
    },
    tag_b: {
      tag_id: 'a-tag',
      slug: 'walk',
      name: 'Walk',
      category: 'sport',
      color: null,
    },
    count: 2,
    pct_of_a: 50,
    pct_of_b: 33.3,
  },
];

describe('tagCooccurrenceMatrix', () => {
  it('builds a symmetric matrix sorted by tag name', () => {
    const matrix = buildTagCooccurrenceMatrix(pairs);

    expect(matrix.tags.map((tag) => tag.name)).toEqual(['Coffee', 'Focus', 'Walk']);
    expect(matrix.counts[0][1]).toBe(0);
    expect(matrix.counts[0][2]).toBe(2);
    expect(matrix.counts[1][2]).toBe(4);
    expect(matrix.counts[2][1]).toBe(4);
  });

  it('maps intensity levels from count ratio', () => {
    expect(cooccurrenceIntensityLevel(0, 8)).toBe(0);
    expect(cooccurrenceIntensityLevel(2, 8)).toBe(1);
    expect(cooccurrenceIntensityLevel(8, 8)).toBe(4);
  });
});
