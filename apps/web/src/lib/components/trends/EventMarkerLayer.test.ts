import { describe, expect, it } from 'vitest';
import { dedupeEventMarkers, type EventMarker } from './EventMarkerLayer.svelte';

describe('dedupeEventMarkers', () => {
  it('keeps the first marker per date/end/kind key', () => {
    const markers: EventMarker[] = [
      { date: '2026-05-01', label: 'A', kind: 'generic' },
      { date: '2026-05-01', label: 'B', kind: 'generic' },
      { date: '2026-05-01', endDate: '2026-05-03', label: 'C', kind: 'generic' },
      { date: '2026-05-02', label: 'D', kind: 'symptom_onset' },
    ];
    const deduped = dedupeEventMarkers(markers);
    expect(deduped).toHaveLength(3);
    expect(deduped.map((marker) => marker.label)).toEqual(['A', 'C', 'D']);
  });

  it('keeps coincidence bands and lag1 lines on the same date (#910)', () => {
    const markers: EventMarker[] = [
      { date: '2026-05-01', endDate: '2026-05-01', label: 'A∩B', kind: 'generic' },
      { date: '2026-05-01', label: 'A→B', kind: 'compare_lag1' },
    ];
    expect(dedupeEventMarkers(markers)).toHaveLength(2);
  });
});
