import { describe, expect, it } from 'vitest';
import { RequestGeneration } from './requestGeneration';

describe('RequestGeneration', () => {
  it('rejects an old A response after A → B → A', () => {
    const scope = new RequestGeneration();
    const firstA = scope.begin('user-1:14');
    const b = scope.begin('user-1:28');
    const secondA = scope.begin('user-1:14');

    expect(firstA.signal.aborted).toBe(true);
    expect(b.signal.aborted).toBe(true);
    expect(firstA.isCurrent()).toBe(false);
    expect(secondA.isCurrent()).toBe(true);
  });

  it('invalidates a user request on session change', () => {
    const scope = new RequestGeneration();
    const previousUser = scope.begin('user-1:90');
    scope.cancel();
    const currentUser = scope.begin('user-2:90');

    expect(previousUser.isCurrent()).toBe(false);
    expect(currentUser.isCurrent()).toBe(true);
  });
});
