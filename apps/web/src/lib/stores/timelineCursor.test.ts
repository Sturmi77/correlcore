import { get } from 'svelte/store';
import { beforeEach, describe, expect, it } from 'vitest';

import { timelineCursor, timelineCursorDate } from './timelineCursor';

const AXIS_7D = ['2026-05-24', '2026-05-25', '2026-05-26', '2026-05-27', '2026-05-28', '2026-05-29', '2026-05-30'];

describe('timelineCursor store (M3.8 Sprint 1 — ADR-0035)', () => {
  beforeEach(() => {
    timelineCursor.reset();
  });

  it('starts cleared', () => {
    expect(get(timelineCursor)).toEqual({ date: null, source: null, axisDates: [] });
    expect(get(timelineCursorDate)).toBeNull();
  });

  it('publishes the canonical axis without changing the cursor date', () => {
    timelineCursor.setAxis(AXIS_7D);
    expect(get(timelineCursor).axisDates).toEqual(AXIS_7D);
    expect(get(timelineCursor).date).toBeNull();
  });

  it('records hover with source "hover"', () => {
    timelineCursor.setAxis(AXIS_7D);
    timelineCursor.hover('2026-05-28');
    expect(get(timelineCursor).date).toBe('2026-05-28');
    expect(get(timelineCursor).source).toBe('hover');
  });

  it('focus wins over later hover changes', () => {
    timelineCursor.setAxis(AXIS_7D);
    timelineCursor.focus('2026-05-26');
    timelineCursor.hover('2026-05-28');
    // hover is suppressed while focus owns the cursor
    expect(get(timelineCursor).date).toBe('2026-05-26');
    expect(get(timelineCursor).source).toBe('focus');
  });

  it('hover(null) does not clear a focus cursor', () => {
    timelineCursor.setAxis(AXIS_7D);
    timelineCursor.focus('2026-05-26');
    timelineCursor.hover(null);
    expect(get(timelineCursor).date).toBe('2026-05-26');
  });

  it('move() advances the cursor by one day from current date', () => {
    timelineCursor.setAxis(AXIS_7D);
    timelineCursor.setDate('2026-05-26', 'keyboard');
    const next = timelineCursor.move(1);
    expect(next).toBe('2026-05-27');
    expect(get(timelineCursor).date).toBe('2026-05-27');
    expect(get(timelineCursor).source).toBe('keyboard');
  });

  it('move() with no current date starts from end of axis', () => {
    timelineCursor.setAxis(AXIS_7D);
    timelineCursor.move(-1);
    // ends at the last entry, then steps back by one
    expect(get(timelineCursor).date).toBe('2026-05-29');
  });

  it('move() clamps to axis bounds (no underflow)', () => {
    timelineCursor.setAxis(AXIS_7D);
    timelineCursor.setDate('2026-05-24', 'keyboard');
    timelineCursor.move(-5);
    expect(get(timelineCursor).date).toBe('2026-05-24');
  });

  it('move() clamps to axis bounds (no overflow)', () => {
    timelineCursor.setAxis(AXIS_7D);
    timelineCursor.setDate('2026-05-30', 'keyboard');
    timelineCursor.move(10);
    expect(get(timelineCursor).date).toBe('2026-05-30');
  });

  it('move() supports week jumps (Shift+Arrow semantics)', () => {
    const longAxis = Array.from({ length: 30 }, (_, i) => {
      const d = new Date('2026-05-01T12:00:00');
      d.setDate(d.getDate() + i);
      return d.toISOString().slice(0, 10);
    });
    timelineCursor.setAxis(longAxis);
    timelineCursor.setDate('2026-05-15', 'keyboard');
    timelineCursor.move(7);
    expect(get(timelineCursor).date).toBe('2026-05-22');
    timelineCursor.move(-7);
    expect(get(timelineCursor).date).toBe('2026-05-15');
  });

  it('move() returns null when axis is empty', () => {
    timelineCursor.setAxis([]);
    expect(timelineCursor.move(1)).toBeNull();
  });

  it('clear() removes the cursor regardless of source', () => {
    timelineCursor.setAxis(AXIS_7D);
    timelineCursor.focus('2026-05-26');
    timelineCursor.clear();
    expect(get(timelineCursor).date).toBeNull();
    expect(get(timelineCursor).source).toBeNull();
    // axis is preserved through clear
    expect(get(timelineCursor).axisDates).toEqual(AXIS_7D);
  });

  it('derived store mirrors the active date', () => {
    timelineCursor.setAxis(AXIS_7D);
    timelineCursor.focus('2026-05-28');
    expect(get(timelineCursorDate)).toBe('2026-05-28');
    timelineCursor.clear();
    expect(get(timelineCursorDate)).toBeNull();
  });
});
