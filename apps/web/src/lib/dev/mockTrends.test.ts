import { describe, expect, it } from 'vitest';
import { mockSymptomTagCooccurrenceByRange, mockTagCooccurrenceByRange } from '$lib/dev/mockTrends';

describe('mock M7 trend data', () => {
  it('provides visibly different tag co-occurrence data per range', () => {
    expect(mockTagCooccurrenceByRange['30d'].range).toBe('30d');
    expect(mockTagCooccurrenceByRange['90d'].range).toBe('90d');
    expect(mockTagCooccurrenceByRange['1y'].range).toBe('1y');
    expect(mockTagCooccurrenceByRange['30d'].pairs[0]?.count).not.toBe(
      mockTagCooccurrenceByRange['1y'].pairs[0]?.count
    );
  });

  it('provides visibly different symptom co-occurrence data per range', () => {
    expect(mockSymptomTagCooccurrenceByRange['30d'].range).toBe('30d');
    expect(mockSymptomTagCooccurrenceByRange['90d'].range).toBe('90d');
    expect(mockSymptomTagCooccurrenceByRange['1y'].range).toBe('1y');
    expect(mockSymptomTagCooccurrenceByRange['30d'].cells[0]?.co_count).not.toBe(
      mockSymptomTagCooccurrenceByRange['1y'].cells[0]?.co_count
    );
  });
});
