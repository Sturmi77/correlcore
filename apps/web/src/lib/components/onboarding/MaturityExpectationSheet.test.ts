import { readFileSync } from 'node:fs';
import { resolve } from 'node:path';
import { describe, expect, it } from 'vitest';

const sheetSource = readFileSync(
  resolve('src/lib/components/onboarding/MaturityExpectationSheet.svelte'),
  'utf8'
);
const contentSource = readFileSync(
  resolve('src/lib/components/onboarding/MaturityExpectationContent.svelte'),
  'utf8'
);

describe('MaturityExpectationSheet contract', () => {
  it('wraps the shared maturity content in a BottomSheet with dismiss CTA', () => {
    expect(sheetSource).toContain('testId="maturity-expectation-sheet"');
    expect(sheetSource).toContain('data-testid="maturity-expectation-cta"');
    expect(sheetSource).toContain('MaturityExpectationContent');
    expect(sheetSource).toContain("dispatch('dismiss')");
  });

  it('renders phase thumbs and the tag hint in the shared content', () => {
    expect(contentSource).toContain('MATURITY_INTRO_THUMBS');
    expect(contentSource).toContain('onboarding.maturity_intro');
    expect(contentSource).toContain('maturity-intro-tag-hint');
  });
});
