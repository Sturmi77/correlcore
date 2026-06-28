import { describe, expect, it } from 'vitest';
import {
  buildProfileDistance,
  hierarchicalClusterOrder,
  orderAxisIds,
} from './cooccurrenceClusterOrder';

describe('cooccurrenceClusterOrder', () => {
  it('clusters similar profile ids together', () => {
    const order = hierarchicalClusterOrder(['a', 'b', 'c'], (left, right) => {
      const pairs: Record<string, number> = {
        'a:b': 0.1,
        'a:c': 1,
        'b:c': 1,
      };
      const key = [left, right].sort().join(':');
      return pairs[key] ?? 1;
    });

    expect(order.indexOf('a')).toBeLessThan(order.indexOf('c'));
    expect(order.indexOf('b')).toBeLessThan(order.indexOf('c'));
  });

  it('orders axes alphabetically by default', () => {
    const profiles = new Map<string, number[]>([
      ['b', [1, 0]],
      ['a', [0, 1]],
    ]);
    const order = orderAxisIds(['b', 'a'], profiles, 'alphabetical', (id) => id);
    expect(order).toEqual(['a', 'b']);
  });

  it('orders axes by clustered profiles when requested', () => {
    const profiles = new Map<string, number[]>([
      ['near-a', [1, 0, 0]],
      ['near-b', [0.9, 0.1, 0]],
      ['far', [0, 0, 1]],
    ]);
    const distance = buildProfileDistance(profiles, ['near-a', 'near-b', 'far']);
    const order = orderAxisIds(['far', 'near-b', 'near-a'], profiles, 'clustered', (id) => id);

    expect(Math.abs(order.indexOf('near-a') - order.indexOf('near-b'))).toBe(1);
    expect(order.indexOf('far')).toBeGreaterThan(order.indexOf('near-a'));
    expect(distance('near-a', 'near-b')).toBeLessThan(distance('near-a', 'far'));
  });
});
