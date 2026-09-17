import { describe, expect, it } from 'vitest';
import type {
  InsightResponse,
  SymptomTagCooccurrenceCell,
  TagCooccurrencePair,
} from '$lib/api/insights';
import type { SymptomHeatmapResponse, TagHeatmapResponse } from '$lib/api/stats';
import {
  MAX_ESM_PARTNERS,
  candidatesFromSymptomTagCooccurrence,
  candidatesFromTagCooccurrence,
  clampActivePartners,
  clampPartnerCandidates,
  countWindowsWithPartner,
  isPartnerPresentOnDate,
  partnerDatesInWindow,
  pickDefaultPartner,
  presenceDatesForPartner,
  resolveEsmAlignSubject,
  type EsmAlignSubject,
  type EsmPartner,
} from './esmPartner';

function insight(partial: Partial<InsightResponse>): InsightResponse {
  return {
    id: 'i1',
    user_id: 'u1',
    insight_type: 'pointbiserial',
    tier: 'preliminary',
    metric: 'mood',
    subject_type: 'tag',
    subject_id: 't-sport',
    subject_label: 'Sport',
    effect_size: 0.4,
    confidence: 0.8,
    sample_n: 20,
    statement: null,
    flags: {},
    payload: {},
    generated_for_date: '2026-05-01',
    generated_at: '2026-05-01T00:00:00Z',
    created_at: '2026-05-01T00:00:00Z',
    updated_at: '2026-05-01T00:00:00Z',
    ...partial,
  };
}

const tag = (
  tag_id: string,
  name: string,
  slug = name.toLowerCase()
): TagCooccurrencePair['tag_a'] => ({
  tag_id,
  slug,
  name,
  category: 'sport',
  color: null,
});

describe('resolveEsmAlignSubject', () => {
  it('uses the insight subject for co-occurrence insights', () => {
    expect(resolveEsmAlignSubject(insight({}))).toEqual({
      id: 't-sport',
      slug: null,
      label: 'Sport',
      kind: 'tag',
    });
  });

  it('preserves payload slug for copy-on-write tag overrides', () => {
    expect(
      resolveEsmAlignSubject(
        insight({
          subject_id: 't-sport-copy',
          payload: { tag_slug: 'sport' },
        })
      )
    ).toEqual({
      id: 't-sport-copy',
      slug: 'sport',
      label: 'Sport',
      kind: 'tag',
    });
  });

  it('preserves payload symptom_slug for symptom insights', () => {
    expect(
      resolveEsmAlignSubject(
        insight({
          subject_type: 'symptom',
          subject_id: 's-head-copy',
          subject_label: 'Headache',
          payload: { symptom_slug: 'headache' },
        })
      )
    ).toEqual({
      id: 's-head-copy',
      slug: 'headache',
      label: 'Headache',
      kind: 'symptom',
    });
  });

  it('uses the lag feature for lag insights', () => {
    const lag = insight({
      subject_type: 'metric',
      subject_id: 'mood',
      subject_label: 'Mood',
      payload: {
        method: 'lag',
        feature: { kind: 'tag', slug: 'cycling', name: 'Cycling' },
      },
    });
    expect(resolveEsmAlignSubject(lag)).toEqual({
      id: null,
      slug: 'cycling',
      label: 'Cycling',
      kind: 'tag',
    });
  });

  it('returns null for unsupported subjects', () => {
    expect(
      resolveEsmAlignSubject(insight({ subject_type: 'metric', subject_id: 'mood' }))
    ).toBeNull();
  });
});

describe('candidatesFromTagCooccurrence', () => {
  const subject: EsmAlignSubject = {
    id: 't-sport',
    slug: 'sport',
    label: 'Sport',
    kind: 'tag',
  };
  const pairs: TagCooccurrencePair[] = [
    {
      tag_a: tag('t-sport', 'Sport'),
      tag_b: tag('t-sleep', 'Sleep'),
      count: 4,
      pct_of_a: 0.4,
      pct_of_b: 0.5,
    },
    {
      tag_a: tag('t-coffee', 'Coffee'),
      tag_b: tag('t-sport', 'Sport'),
      count: 9,
      pct_of_a: 0.3,
      pct_of_b: 0.6,
    },
    { tag_a: tag('t-a', 'A'), tag_b: tag('t-b', 'B'), count: 99, pct_of_a: 1, pct_of_b: 1 },
  ];

  it('ranks partners by count and excludes self/unrelated pairs', () => {
    const candidates = candidatesFromTagCooccurrence(subject, pairs);
    expect(candidates.map((row) => row.id)).toEqual(['t-coffee', 't-sleep']);
    expect(candidates[0]?.score).toBe(9);
  });

  it('returns empty when the subject is a symptom', () => {
    expect(candidatesFromTagCooccurrence({ ...subject, kind: 'symptom' }, pairs)).toEqual([]);
  });

  it('matches partners by stable slug when subject id changed', () => {
    const copiedSubject: EsmAlignSubject = {
      id: 't-sport-copy',
      slug: 'sport',
      label: 'Sport',
      kind: 'tag',
    };
    const candidates = candidatesFromTagCooccurrence(copiedSubject, pairs);
    expect(candidates.map((row) => row.id)).toEqual(['t-coffee', 't-sleep']);
  });
});

describe('candidatesFromSymptomTagCooccurrence', () => {
  const subject: EsmAlignSubject = {
    id: 's-head',
    slug: 'headache',
    label: 'Headache',
    kind: 'symptom',
  };
  const cells: SymptomTagCooccurrenceCell[] = [
    {
      symptom: { symptom_id: 's-head', slug: 'headache', name: 'Headache', icon: null },
      tag: tag('t-coffee', 'Coffee'),
      phi: 0.2,
      jaccard: 0.1,
      lift: 2.5,
      co_count: 5,
      symptom_count: 10,
      tag_count: 20,
      total_count: 100,
      p_value_corrected: 0.01,
      confounder: null,
    },
    {
      symptom: { symptom_id: 's-head', slug: 'headache', name: 'Headache', icon: null },
      tag: tag('t-sleep', 'Sleep'),
      phi: 0.1,
      jaccard: 0.05,
      lift: 1.2,
      co_count: 3,
      symptom_count: 10,
      tag_count: 15,
      total_count: 100,
      p_value_corrected: 0.2,
      confounder: null,
    },
  ];

  it('ranks by |lift − 1|', () => {
    const candidates = candidatesFromSymptomTagCooccurrence(subject, cells);
    expect(candidates.map((row) => row.id)).toEqual(['t-coffee', 't-sleep']);
    expect(candidates[0]?.score).toBeCloseTo(1.5);
  });
});

describe('pick / clamp helpers', () => {
  const ranked = [
    { id: 'a', label: 'A', kind: 'tag' as const, score: 3 },
    { id: 'b', label: 'B', kind: 'tag' as const, score: 2 },
    { id: 'c', label: 'C', kind: 'tag' as const, score: 1 },
  ];

  it('picks the top candidate as default and returns null when empty', () => {
    expect(pickDefaultPartner(ranked)).toEqual({ id: 'a', label: 'A', kind: 'tag' });
    expect(pickDefaultPartner([])).toBeNull();
  });

  it('enforces MAX_ESM_PARTNERS = 1', () => {
    expect(MAX_ESM_PARTNERS).toBe(1);
    const partners: EsmPartner[] = [
      { id: 'a', label: 'A', kind: 'tag' },
      { id: 'b', label: 'B', kind: 'tag' },
    ];
    expect(clampActivePartners(partners)).toEqual([{ id: 'a', label: 'A', kind: 'tag' }]);
    expect(clampPartnerCandidates(ranked, 2).map((row) => row.id)).toEqual(['a', 'b']);
  });
});

describe('presence + window helpers', () => {
  const tagHeatmap: TagHeatmapResponse = {
    start_date: '2026-05-01',
    end_date: '2026-05-14',
    tags: [
      {
        tag_id: 't-coffee',
        name: 'Coffee',
        slug: 'coffee',
        category: 'consumption',
        color: null,
        days: [
          { date: '2026-05-10', count: 1 },
          { date: '2026-05-12', count: 0 },
          { date: '2026-05-13', count: 2 },
        ],
      },
    ],
  };
  const symptomHeatmap: SymptomHeatmapResponse = {
    start_date: '2026-05-01',
    end_date: '2026-05-14',
    symptoms: [],
  };

  it('reads partner presence from heatmaps', () => {
    const partner: EsmPartner = { id: 't-coffee', label: 'Coffee', kind: 'tag' };
    expect(presenceDatesForPartner(partner, tagHeatmap, symptomHeatmap)).toEqual([
      '2026-05-10',
      '2026-05-13',
    ]);
    expect(presenceDatesForPartner(null, tagHeatmap, symptomHeatmap)).toEqual([]);
  });

  it('lists partner hits inside an aligned window', () => {
    const hits = partnerDatesInWindow('2026-05-10', ['2026-05-10', '2026-05-13', '2026-06-01'], 7);
    expect(hits).toEqual(['2026-05-10', '2026-05-13']);
    expect(isPartnerPresentOnDate('2026-05-10', hits)).toBe(true);
    expect(isPartnerPresentOnDate('2026-05-11', hits)).toBe(false);
  });
});

describe('countWindowsWithPartner (#918)', () => {
  const onsets = ['2026-05-10', '2026-06-20'];

  it('counts windows, not days', () => {
    expect(countWindowsWithPartner(onsets, ['2026-05-09', '2026-05-12'], 7)).toEqual({
      hits: 1,
      windows: 2,
    });
  });

  it('counts a window once per partner appearance run', () => {
    expect(countWindowsWithPartner(onsets, ['2026-05-09', '2026-05-10', '2026-06-21'], 7)).toEqual({
      hits: 2,
      windows: 2,
    });
  });

  it('reports zero hits without hiding the denominator', () => {
    expect(countWindowsWithPartner(onsets, ['2026-08-01'], 7)).toEqual({ hits: 0, windows: 2 });
  });

  it('accepts a presence set as well as an array', () => {
    expect(countWindowsWithPartner(onsets, new Set(['2026-06-20']), 7)).toEqual({
      hits: 1,
      windows: 2,
    });
  });
});
