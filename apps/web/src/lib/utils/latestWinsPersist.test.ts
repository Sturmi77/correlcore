import { describe, expect, it } from 'vitest';
import { createLatestWinsGate } from './latestWinsPersist';

describe('createLatestWinsGate', () => {
  it('skips a queued write that was superseded before it started', async () => {
    const writes: string[] = [];
    const gate = createLatestWinsGate();
    let value = 'A';

    async function persist(next: string): Promise<void> {
      const seq = gate.begin();
      value = next;
      await gate.enqueue(async () => {
        if (!gate.isCurrent(seq)) return;
        writes.push(value);
      });
    }

    await Promise.all([persist('B'), persist('C')]);
    expect(writes).toEqual(['C']);
  });

  it('lets the in-flight write finish, then persists the latest snapshot', async () => {
    const writes: string[] = [];
    let releaseFirst: (() => void) | undefined;
    const firstHold = new Promise<void>((resolve) => {
      releaseFirst = resolve;
    });
    const gate = createLatestWinsGate();
    let value = 'A';
    let started = 0;

    async function persist(next: string): Promise<void> {
      const seq = gate.begin();
      value = next;
      await gate.enqueue(async () => {
        if (!gate.isCurrent(seq)) return;
        started += 1;
        const snapshot = value;
        if (started === 1) await firstHold;
        writes.push(snapshot);
      });
    }

    const first = persist('B');
    await Promise.resolve();
    expect(started).toBe(1);

    const second = persist('C');
    await Promise.resolve();
    expect(writes).toEqual([]);

    releaseFirst?.();
    await Promise.all([first, second]);
    expect(writes).toEqual(['B', 'C']);
  });
});
