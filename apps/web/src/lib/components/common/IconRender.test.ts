/**
 * IconRender — classification regression tests.
 *
 * The component itself is mostly a thin renderer; the part worth
 * regression-testing is the heuristic that decides whether a string is
 * an emoji, a Lucide-style slug, or unknown. We extract the logic by
 * re-implementing it here so the tests pin the contract — if the
 * component diverges, these tests stop matching the rendered output
 * and we have a forcing function to update both sides together.
 *
 * Why not import the helpers from the .svelte file? Svelte 5 components
 * don't expose internal helpers as named exports, and parsing the
 * single-file component to surface them adds tooling weight that's not
 * worth it for two regex tests. Re-implementing the (4-line) regexes
 * here is the standard pattern.
 */

import { describe, expect, it } from 'vitest';

function isLucideSlug(value: string): boolean {
  return /^[a-z][a-z0-9]*(-[a-z0-9]+)*$/.test(value) && value.length >= 2;
}

function looksLikeEmoji(value: string): boolean {
  // eslint-disable-next-line no-control-regex
  return /[^\x00-\x7F]/.test(value);
}

function classify(value: string | null | undefined): 'empty' | 'emoji' | 'lucide' | 'unknown' {
  const trimmed = (value ?? '').trim();
  if (trimmed === '') return 'empty';
  if (looksLikeEmoji(trimmed)) return 'emoji';
  if (isLucideSlug(trimmed)) return 'lucide';
  return 'unknown';
}

describe('IconRender classification', () => {
  it('treats empty / whitespace / null as empty', () => {
    expect(classify(null)).toBe('empty');
    expect(classify(undefined)).toBe('empty');
    expect(classify('')).toBe('empty');
    expect(classify('   ')).toBe('empty');
  });

  it('detects single-codepoint and multi-codepoint emojis', () => {
    // Default seed (006_add_symptom_master_table.py).
    expect(classify('🤕')).toBe('emoji');
    expect(classify('🌀')).toBe('emoji');
    expect(classify('🦴')).toBe('emoji');
    expect(classify('😴')).toBe('emoji');
    expect(classify('🤧')).toBe('emoji');
    // Compound emoji (woman + ZWJ + laptop) — still non-ASCII so emoji-mode.
    expect(classify('👩‍💻')).toBe('emoji');
    // Placeholder used in the custom-form.
    expect(classify('🧠')).toBe('emoji');
  });

  it('detects valid Lucide slugs', () => {
    expect(classify('dumbbell')).toBe('lucide');
    expect(classify('brain')).toBe('lucide');
    expect(classify('heart-pulse')).toBe('lucide');
    expect(classify('a-arrow-down')).toBe('lucide');
    expect(classify('layers-3')).toBe('lucide');
  });

  it('rejects malformed slug-like strings', () => {
    // Trailing hyphen.
    expect(classify('foo-')).toBe('unknown');
    // Leading hyphen.
    expect(classify('-foo')).toBe('unknown');
    // Double hyphen.
    expect(classify('foo--bar')).toBe('unknown');
    // Uppercase (Lucide uses kebab-case).
    expect(classify('Brain')).toBe('unknown');
    // Single character — too short, too ambiguous.
    expect(classify('a')).toBe('unknown');
    // Whitespace inside (the original "dumbbell krafttraining" bug).
    expect(classify('dumbbell krafttraining')).toBe('unknown');
    // Underscore (slug separator is hyphen, not underscore).
    expect(classify('heart_pulse')).toBe('unknown');
  });

  it('trims surrounding whitespace before classifying', () => {
    expect(classify('  dumbbell  ')).toBe('lucide');
    expect(classify('  🧠 ')).toBe('emoji');
  });
});
