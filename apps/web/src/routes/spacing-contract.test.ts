import { readFileSync, readdirSync, statSync } from 'node:fs';
import { join, resolve } from 'node:path';
import { describe, expect, it } from 'vitest';

const ROUTES_DIR = resolve('src/routes');

const EXEMPT_ROUTE_PREFIXES = [
  '/auth/',
  '/onboarding',
  '/entries/new',
  '/entries/day/',
  '/dev',
  '/offline',
  '/status',
];

function collectPageFiles(dir: string, base = ''): string[] {
  const entries = readdirSync(dir);
  const files: string[] = [];
  for (const entry of entries) {
    const fullPath = join(dir, entry);
    const routePath = `${base}/${entry}`.replace(/\/+/g, '/');
    if (statSync(fullPath).isDirectory()) {
      files.push(...collectPageFiles(fullPath, routePath));
      continue;
    }
    if (entry === '+page.svelte') {
      files.push(fullPath);
    }
  }
  return files;
}

function routePathFromFile(filePath: string): string {
  const relative = filePath.replace(`${ROUTES_DIR}`, '').replace('/+page.svelte', '');
  if (!relative || relative === '') return '/';
  return relative;
}

function isExempt(routePath: string): boolean {
  return EXEMPT_ROUTE_PREFIXES.some(
    (prefix) => routePath === prefix || routePath.startsWith(prefix)
  );
}

function extractRootMainClass(source: string): string | null {
  const match = source.match(/<main[^>]*class="([^"]+)"/);
  return match?.[1] ?? null;
}

function extractRootStyleBlock(source: string, rootClass: string): string {
  const classSelector = `.${rootClass.split(/\s+/)[0]}`;
  const styleMatch = source.match(/<style>([\s\S]*)<\/style>/);
  if (!styleMatch) return '';
  const block = styleMatch[1];
  const ruleMatch = block.match(
    new RegExp(`${classSelector.replace('.', '\\.')}[^{]*\\{([^}]*)\\}`, 'm')
  );
  return ruleMatch?.[1] ?? '';
}

describe('spacing contract (O-35)', () => {
  const pageFiles = collectPageFiles(ROUTES_DIR);

  it('defines screen-header-gap token in app.css', () => {
    const appCss = readFileSync(resolve('src/app.css'), 'utf8');
    expect(appCss).toContain('--screen-header-gap');
    expect(appCss).toContain('--heatmap-cell-gap');
  });

  it('product routes use screen-stack on main without horizontal root padding', () => {
    const violations: string[] = [];

    for (const filePath of pageFiles) {
      const routePath = routePathFromFile(filePath);
      if (isExempt(routePath)) continue;

      const source = readFileSync(filePath, 'utf8');
      const rootClass = extractRootMainClass(source);
      if (!rootClass) continue;

      if (!rootClass.includes('screen-stack')) {
        violations.push(`${routePath}: main missing screen-stack (${rootClass})`);
      }

      const rootRules = extractRootStyleBlock(source, rootClass);
      if (/padding(-inline|-left|-right)?\s*:/.test(rootRules)) {
        violations.push(`${routePath}: root horizontal padding in .${rootClass.split(/\s+/)[0]}`);
      }
    }

    expect(violations).toEqual([]);
  });
});
