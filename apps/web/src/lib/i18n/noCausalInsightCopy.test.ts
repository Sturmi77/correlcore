import { describe, expect, it } from 'vitest';

import de from './locales/de.json';
import en from './locales/en.json';

/**
 * #928 D4 — CorrelCore computes correlations, never causes. The copy register
 * (docs/features/arbeitsmuster-vokabular.md) already settles the wording:
 * "Zusammenhänge / Assoziationen" — "associations / correlations". This lint
 * keeps the locales from drifting back, the way `insights.report.col_metric`
 * did ("wirkt auf" / "Affects").
 *
 * Negated disclaimers are the whole point of the surface, so a string that
 * carries one is allowed to name the thing it is denying.
 */
type LocaleString = { path: string; copy: string };

function collectStrings(value: unknown, path = ''): LocaleString[] {
  if (typeof value === 'string') return [{ path, copy: value }];
  if (Array.isArray(value)) {
    return value.flatMap((item, index) => collectStrings(item, `${path}[${index}]`));
  }
  if (value && typeof value === 'object') {
    return Object.entries(value).flatMap(([key, item]) =>
      collectStrings(item, path ? `${path}.${key}` : key)
    );
  }
  return [];
}

/** Affirmative causal verbs — the claim CorrelCore is not entitled to make. */
const CAUSAL =
  /\b(causes?|caused|causing|affects?|affected|affecting|leads? to|influences?|influenced|results? in|makes you)\b|\b(verursacht|verursachen|bewirkt|beeinflusst|beeinflussen|f(ü|ue)hrt zu|sorgt f(ü|ue)r|wirkt auf|wirkt sich)\b/i;

/**
 * Markers that make the sentence a denial rather than a claim. A string
 * containing one may use a causal verb — that is how you say "not a cause".
 */
const DISCLAIMED =
  /not a cause|not causes|does not mean|not a medical|no cause|bedeutet nicht|keine Ursache|nicht, dass|keine medizinische/i;

describe('no causal insight copy (#928 D4)', () => {
  it('states associations, not causes, in every locale string', () => {
    const offenders = [...collectStrings(en), ...collectStrings(de)]
      .filter(({ copy }) => CAUSAL.test(copy) && !DISCLAIMED.test(copy))
      .map(({ path, copy }) => `${path}: ${copy}`);

    expect(offenders).toEqual([]);
  });

  it('still allows the non-causal disclaimers that carry the product', () => {
    const disclaimers = [...collectStrings(en), ...collectStrings(de)].filter(
      ({ copy }) => CAUSAL.test(copy) && DISCLAIMED.test(copy)
    );

    // If these ever vanish the lint above would pass vacuously.
    expect(disclaimers.length).toBeGreaterThan(0);
  });
});
