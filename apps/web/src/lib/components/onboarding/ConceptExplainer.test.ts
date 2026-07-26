import { readFileSync } from 'node:fs';
import { resolve } from 'node:path';
import { render, screen } from '@testing-library/svelte';
import { describe, expect, it, vi } from 'vitest';

import de from '$lib/i18n/locales/de.json';
import en from '$lib/i18n/locales/en.json';
import ConceptExplainer from './ConceptExplainer.svelte';

vi.mock('svelte-i18n', async () => {
  const { readable } = await import('svelte/store');
  return { _: readable((key: string) => key) };
});

const concepts = ['tag', 'habit', 'symptom', 'cycle'] as const;

const onboardingTagsSource = readFileSync(
  resolve('src/lib/components/entries/OnboardingTagSuggestions.svelte'),
  'utf8'
);
const onboardingPageSource = readFileSync(resolve('src/routes/onboarding/+page.svelte'), 'utf8');
const tagSettingsSource = readFileSync(resolve('src/routes/settings/tags/+page.svelte'), 'utf8');

describe('ConceptExplainer contract (#541)', () => {
  it('renders all four concept definitions', () => {
    render(ConceptExplainer);
    expect(screen.getByTestId('concept-explainer')).toBeTruthy();
    for (const concept of concepts) {
      expect(screen.getByTestId(`concept-${concept}`)).toBeTruthy();
    }
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
