import { readFileSync } from 'node:fs';
import { resolve } from 'node:path';
import { describe, expect, it } from 'vitest';

const source = readFileSync(
  resolve('src/lib/components/onboarding/MaturityExpectationSheet.svelte'),
  'utf8'
);

describe('MaturityExpectationSheet contract', () => {
  it('uses BottomSheet with phase thumbs and dismiss CTA', () => {
    expect(source).toContain('testId="maturity-expectation-sheet"');
    expect(source).toContain('data-testid="maturity-expectation-cta"');
    expect(source).toContain('MATURITY_INTRO_THUMBS');
    expect(source).toContain('onboarding.maturity_intro');
    expect(source).toContain('maturity-intro-tag-hint');
    expect(source).toContain("dispatch('dismiss')");
  });
});
