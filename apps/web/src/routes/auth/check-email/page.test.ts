import { readFileSync } from 'node:fs';
import { resolve } from 'node:path';
import { describe, expect, it } from 'vitest';

const source = readFileSync(resolve('src/routes/auth/check-email/+page.svelte'), 'utf8');

describe('/auth/check-email mobile mail link', () => {
  it('exposes a mailto deep link on mobile viewports only', () => {
    expect(source).toContain('data-testid="check-email-open-mail"');
    expect(source).toContain('href="mailto:"');
    expect(source).toContain('DESKTOP_SHELL_BREAKPOINT_PX');
    expect(source).toContain('showMailAppLink');
  });
});
