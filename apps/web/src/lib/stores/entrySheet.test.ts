import { get } from 'svelte/store';
import { describe, expect, it } from 'vitest';
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

  it('closes and emits save signals', () => {
    resetEntrySheetStore();
    openEntrySheet('2026-06-02');
    closeEntrySheet();
    expect(get(entrySheetStore).open).toBe(false);
    notifyEntrySheetSaved();
    expect(get(entrySheetSaveSignal)).toBe(1);
  });
});
