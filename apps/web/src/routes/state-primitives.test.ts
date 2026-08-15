import { describe, expect, it } from 'vitest';
import { readFileSync } from 'node:fs';
import { resolve } from 'node:path';

const src = (...parts: string[]) => readFileSync(resolve(process.cwd(), 'src', ...parts), 'utf8');

describe('state primitive adoption', () => {
  it('keeps InsightFeed on shared alert and empty-state primitives', () => {
    const source = src('lib', 'components', 'insights', 'InsightFeed.svelte');

    expect(source).toContain('InlineAlert');
    expect(source).toContain('EmptyState');
    expect(source).not.toContain('if-error');
    expect(source).not.toContain('if-empty');
  });

  it('uses shared panel/state primitives on top-level analysis routes', () => {
    const routes = [
      src('routes', 'insights', '+page.svelte'),
      src('routes', 'trends', '+page.svelte'),
      src('routes', 'settings', '+page.svelte'),
      src('routes', 'settings', 'tags', '+page.svelte'),
      // #694: the settings hub is now a lean index; the forms (with their
      // InlineAlert states) live on the category sub-pages.
      src('routes', 'settings', 'privacy', '+page.svelte'),
      src('routes', 'settings', 'data', '+page.svelte'),
    ];

    expect(routes.every((source) => source.includes('Panel'))).toBe(true);
    expect(routes.some((source) => source.includes('DataState'))).toBe(true);
    expect(routes.filter((source) => source.includes('InlineAlert')).length).toBeGreaterThanOrEqual(
      3
    );
  });
});
