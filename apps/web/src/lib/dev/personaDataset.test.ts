import { describe, expect, it } from 'vitest';
import { daysToEntries, generateOfficeSportDays, tagPairsFromDays } from './personaDataset';

describe('office-sport persona dataset', () => {
  const today = '2026-08-25';

  it('is deterministic for a fixed calendar', () => {
    const first = generateOfficeSportDays(today, 42);
    const second = generateOfficeSportDays(today, 42);
    expect(first).toEqual(second);
    expect(first).toHaveLength(42);
    expect(first[0]?.date).toBe(today);
  });

  it('avoids modulo-looking scores and attaches real context', () => {
    const days = generateOfficeSportDays(today, 42);
    const moods = days.map((day) => day.mood);
    const uniqueMoods = new Set(moods);
    expect(uniqueMoods.size).toBeGreaterThanOrEqual(3);
    const sawtooth = days.every((day, idx) => day.mood === 3 + ((idx + 1) % 3));
    expect(sawtooth).toBe(false);

    const withTags = days.filter((day) => day.tags.length > 0);
    expect(withTags.length).toBeGreaterThan(30);
    expect(days.every((day) => day.tags.length <= 5)).toBe(true);
    expect(days.some((day) => day.note)).toBe(true);
    expect(days.every((day) => !day.note?.toLowerCase().includes('mock'))).toBe(true);
    expect(days.every((day) => day.sleepMinutes > 0 && day.sleepQuality >= 1)).toBe(true);
  });

  it('maps onto entry DTOs with sleep fields', () => {
    const days = generateOfficeSportDays(today, 9);
    const entries = daysToEntries(days, 'mock-user');
    expect(entries).toHaveLength(9);
    expect(entries[0]?.sleep_minutes).toBeGreaterThan(0);
    expect(entries[0]?.cycle_day).toBeNull();
  });

  it('produces enough co-occurrence pairs for robust fixtures', () => {
    const days = generateOfficeSportDays(today, 42);
    const pairs = tagPairsFromDays(days, -89);
    expect(pairs.length).toBeGreaterThanOrEqual(5);
    expect(pairs[0]?.count).toBeGreaterThanOrEqual(2);
  });
});
