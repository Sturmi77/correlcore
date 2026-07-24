import { get } from 'svelte/store';
import { describe, expect, it } from 'vitest';
import { isoDate } from '$lib/utils/entryForm';
import {
  closeEntrySheet,
  entrySheetSaveSignal,
  entrySheetStore,
  notifyEntrySheetSaved,
  openEntrySheet,
  resetEntrySheetStore,
} from './entrySheet';

describe('entrySheet store', () => {
  it('opens with the requested date and onboarding flag', () => {
    resetEntrySheetStore();
    openEntrySheet('2026-06-01', { onboardingTags: true });
    expect(get(entrySheetStore)).toEqual({
      open: true,
      date: '2026-06-01',
      onboardingTagsEnabled: true,
    });
  });

  it('defaults to the local calendar day when no date is passed', () => {
    // Widget deep link → /?openEntry=1 with no date; must match Home "+"
    // (local day), not UTC, or an Americas evening write lands on tomorrow.
    resetEntrySheetStore();
    openEntrySheet();
    expect(get(entrySheetStore).date).toBe(isoDate(new Date()));
  });

  it('closes and emits save signals', () => {
    resetEntrySheetStore();
    openEntrySheet('2026-06-02');
    closeEntrySheet();
    expect(get(entrySheetStore).open).toBe(false);
    notifyEntrySheetSaved();
    expect(get(entrySheetSaveSignal)).toBe(1);
  });
});
