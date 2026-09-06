/**
 * Single-flight latest-wins gate for optimistic preference saves.
 *
 * #849 kept Home/Insights reorder controls enabled during PATCH, but
 * `update_user_preferences` last-writes JSONB with no If-Match. Overlapping
 * requests can therefore commit out of order: the slower earlier PATCH
 * overwrites the later one on the server while persistSeq hides that on
 * the client.
 *
 * Apply optimistic local state after `begin()`, then `enqueue` a task that
 * checks `isCurrent(seq)` before writing. Only one task runs at a time;
 * superseded queued tasks no-op so the trailing write persists the latest
 * snapshot.
 */
export function createLatestWinsGate(): LatestWinsGate {
  let persistSeq = 0;
  let persistGate: Promise<void> = Promise.resolve();

  return {
    begin(): number {
      return ++persistSeq;
    },
    isCurrent(seq: number): boolean {
      return seq === persistSeq;
    },
    enqueue(task: () => Promise<void>): Promise<void> {
      persistGate = persistGate.then(task, task);
      return persistGate;
    },
  };
}

export interface LatestWinsGate {
  /** Bump the generation before applying optimistic local state. */
  begin(): number;
  isCurrent(seq: number): boolean;
  enqueue(task: () => Promise<void>): Promise<void>;
}
