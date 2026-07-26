import { readFileSync } from 'node:fs';
import { resolve } from 'node:path';
import { describe, expect, it } from 'vitest';

import de from '$lib/i18n/locales/de.json';
import en from '$lib/i18n/locales/en.json';

const explainerSource = readFileSync(
  resolve('src/lib/components/onboarding/ConceptExplainer.svelte'),
  'utf8'
);
const onboardingTagsSource = readFileSync(
  resolve('src/lib/components/entries/OnboardingTagSuggestions.svelte'),
  'utf8'
);
const onboardingPageSource = readFileSync(resolve('src/routes/onboarding/+page.svelte'), 'utf8');
const tagSettingsSource = readFileSync(resolve('src/routes/settings/tags/+page.svelte'), 'utf8');

const concepts = ['tag', 'habit', 'symptom', 'cycle'] as const;

describe('ConceptExplainer contract (#541)', () => {
  it('renders all four concept definitions', () => {
    expect(explainerSource).toContain('data-testid="concept-explainer"');
    for (const concept of concepts) {
      expect(explainerSource).toContain(`concept-${concept}`);
    }
    expect(explainerSource).toContain('onboarding.concepts.title');
  });

  it('is shown before the tag step in both onboarding surfaces (O1)', () => {
    expect(onboardingTagsSource).toContain('ConceptExplainer');
    expect(onboardingPageSource).toContain('ConceptExplainer');
  });

  it('is reachable in-app where tags are managed (O3)', () => {
    expect(tagSettingsSource).toContain('ConceptExplainer');
    expect(tagSettingsSource).toContain('data-testid="tag-settings-concepts-toggle"');
  });

  it('has non-empty DE and EN copy for every concept incl. cycle (O2)', () => {
    for (const locale of [de, en]) {
      const c = locale.onboarding.concepts as Record<string, string>;
      for (const concept of concepts) {
        expect(c[`${concept}_term`]?.length).toBeGreaterThan(0);
        expect(c[`${concept}_body`]?.length).toBeGreaterThan(0);
      }
    }
  });
});
