import { readFileSync } from 'node:fs';
import { resolve } from 'node:path';
import { describe, expect, it } from 'vitest';
import { NAV_ITEMS } from '$lib/navigation/appNav';
import { DESKTOP_SHELL_BREAKPOINT_PX, PRIMARY_SURFACES } from '$lib/ui/surfaceContract';

describe('responsive shell contract', () => {
  it('keeps CSS and TypeScript on the same desktop breakpoint', () => {
    const css = readFileSync(resolve('src/app.css'), 'utf8');

    expect(css).toContain(`@media (min-width: ${DESKTOP_SHELL_BREAKPOINT_PX}px)`);
  });

  it('maps the four navigable product surfaces to AppNav exactly once', () => {
    const navigableRoutes = PRIMARY_SURFACES.filter((surface) => surface.navigation).map(
      (surface) => surface.route
    );

    expect(NAV_ITEMS.map((item) => item.href)).toEqual(navigableRoutes);
  });

  it('keeps the shared layout as the only primary navigation owner', () => {
    const layout = readFileSync(resolve('src/routes/+layout.svelte'), 'utf8');

    expect(layout).toContain("import AppNav from '$lib/components/common/AppNav.svelte'");
    expect(layout).toContain('<AppNav />');
    expect(layout).toContain('app-frame--with-nav');
  });
});
