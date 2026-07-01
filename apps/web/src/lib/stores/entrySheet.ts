import { get, writable } from 'svelte/store';
import { isoDate } from '$lib/utils/entryForm';

export interface EntrySheetState {
  open: boolean;
  date: string;
  onboardingTagsEnabled: boolean;
}

const _state = writable<EntrySheetState>({
  open: false,
  date: isoDate(new Date()),
  onboardingTagsEnabled: false,
});

/** Bumped after a successful sheet save so routes can refresh summaries. */
export const entrySheetSaveSignal = writable(0);

export const entrySheetStore = { subscribe: _state.subscribe };

export function openEntrySheet(
  date?: string,
  options?: { onboardingTags?: boolean }
): void {
  _state.update(() => ({
    open: true,
    date: date ?? isoDate(new Date()),
    onboardingTagsEnabled: options?.onboardingTags ?? false,
  }));
}

export function closeEntrySheet(): void {
  _state.update((state) => ({ ...state, open: false }));
}

export function setEntrySheetOpen(open: boolean): void {
  _state.update((state) => ({ ...state, open }));
}

export function notifyEntrySheetSaved(): void {
  entrySheetSaveSignal.update((count) => count + 1);
}

export function resetEntrySheetStore(): void {
  _state.set({
    open: false,
    date: isoDate(new Date()),
    onboardingTagsEnabled: false,
  });
  entrySheetSaveSignal.set(0);
}

export function entrySheetSnapshot(): EntrySheetState {
  return get(_state);
}
