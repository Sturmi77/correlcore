/**
 * Frontend API contract constants.
 *
 * These values mirror the FastAPI/Pydantic contract and are covered by
 * backend/tests/test_api_contract.py. Until an OpenAPI TypeScript generator is
 * introduced, this file is the frontend's central source for schema-sensitive
 * enum and range values.
 */

export const ENTRY_CONTRACT = {
  entrySlots: ['day', 'morning', 'noon', 'evening'],
  entrySources: ['direct', 'retrospective', 'import', 'wearable'],
  workContexts: ['homeoffice', 'office', 'vacation', 'sick', 'weekend', 'travel'],
  metrics: {
    mood_score: { min: 1, max: 5, invert: false },
    energy: { min: 1, max: 5, invert: false },
    stress: { min: 1, max: 5, invert: true },
    sleep_quality: { min: 1, max: 5, invert: false },
    cycle_day: { min: 1, max: 35, invert: false },
  },
  noteMaxLength: 4000,
  backdateDaysLimit: 7,
} as const;

export type EntrySlot = (typeof ENTRY_CONTRACT.entrySlots)[number];
export type EntrySource = (typeof ENTRY_CONTRACT.entrySources)[number];
export type WorkContext = (typeof ENTRY_CONTRACT.workContexts)[number];
export type EntryMetricField = keyof typeof ENTRY_CONTRACT.metrics;
