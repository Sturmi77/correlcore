/**
 * Phase-gate tests for the Event-Aligned Small Multiples sheet.
 *
 * The sheet is only safe to render once the insight has reached the
 * provisional or robust phase (ADR-0021). The helper exported from the
 * sheet module is the single source of truth used by both the component
 * and the calling Insight card; both call sites must stay aligned.
 */

import { describe, expect, it } from 'vitest';
import { isSmallMultiplesUnlocked, SMALL_MULTIPLES_RADIUS } from './smallMultiplesGate';

describe('isSmallMultiplesUnlocked (ADR-0021 phase gate)', () => {
  it('blocks the collecting phase', () => {
    expect(isSmallMultiplesUnlocked('collecting')).toBe(false);
  });

  it('blocks the early_patterns phase', () => {
    expect(isSmallMultiplesUnlocked('early_patterns')).toBe(false);
  });

  it('unlocks at provisional', () => {
    expect(isSmallMultiplesUnlocked('provisional')).toBe(true);
  });

  it('unlocks at robust', () => {
    expect(isSmallMultiplesUnlocked('robust')).toBe(true);
  });

  it('blocks when phase is null or undefined', () => {
    expect(isSmallMultiplesUnlocked(null)).toBe(false);
    expect(isSmallMultiplesUnlocked(undefined)).toBe(false);
  });

  it('keeps the window radius at 7 days', () => {
    // The compare panel and any other call site must keep this in sync
    // — it is part of the visual contract documented in ADR-0035 §6.
    expect(SMALL_MULTIPLES_RADIUS).toBe(7);
  });
});
