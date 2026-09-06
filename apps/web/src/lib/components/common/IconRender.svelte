<script lang="ts">
  /**
   * IconRender — renders an icon string in one of two ways:
   *
   *   1. **Emoji / single grapheme** (default seed: 🤕 🌀 🦴 😴 🤧, or
   *      whatever the user typed as a Unicode emoji). Rendered as a plain
   *      `<span>` so the browser draws the system emoji font.
   *
   *   2. **Lucide icon slug** (e.g. ``dumbbell``, ``brain``, ``heart-pulse``).
   *      Backend ``Symptom.icon`` and ``Tag.icon`` are documented in
   *      ``backend/app/models/tag.py`` as accepting either form. Slugs are
   *      kebab-case, ASCII letters/digits/hyphens only. Dynamically loaded
   *      from ``@lucide/svelte/icons/<slug>`` to keep the bundle small —
   *      only icons actually referenced by saved symptoms or tags are
   *      pulled in at runtime.
   *
   * Failure mode: if neither shape matches (e.g. user typed "asdf qwer") or
   * the dynamic import fails (typo'd slug → 404), the component renders
   * nothing visible. The surrounding name label always remains, so the
   * entity (symptom, tag, ...) is still identifiable. We never render
   * the raw slug string — that was the original bug
   * ("dumbbell krafttraining").
   *
   * Sizing: ``size`` prop maps to both width/height (px). Default 18 to fit
   * the existing ``.symptom-icon`` line-height; tag chips pass 16.
   */

  import { onMount } from 'svelte';
  import type { Component } from 'svelte';
  import type { LucideProps } from '@lucide/svelte';

  export let icon: string | null | undefined = null;
  export let size = 18;
  /** Optional ARIA label override; defaults to ``aria-hidden=true``. */
  export let label: string | null = null;

  type LucideIcon = Component<LucideProps>;

  /**
   * Cache resolved icon components per slug so repeated mounts don't
   * re-import. Module-scope so it survives between component instances.
   */
  const iconCache = new Map<string, LucideIcon>();

  let LucideComp: LucideIcon | null = null;

  /**
   * Match Lucide's slug shape: lowercase ASCII letters, optional digits and
   * single hyphens. Length 2..32 mirrors the backend ``String(32)`` ceiling.
   * This is intentionally narrow — anything else (multi-char emoji
   * sequences, single grapheme, free-text) falls through to the
   * emoji-/grapheme-render path.
   */
  function isLucideSlug(value: string): boolean {
    return /^[a-z][a-z0-9]*(-[a-z0-9]+)*$/.test(value) && value.length >= 2;
  }

  /**
   * Heuristic: if the string contains anything non-ASCII (emoji codepoints
   * are above U+007F), treat it as an emoji/grapheme regardless of length.
   */
  function looksLikeEmoji(value: string): boolean {
    // eslint-disable-next-line no-control-regex
    return /[^\x00-\x7F]/.test(value);
  }

  $: trimmed = (icon ?? '').trim();
  $: mode =
    trimmed === ''
      ? 'empty'
      : looksLikeEmoji(trimmed)
        ? 'emoji'
        : isLucideSlug(trimmed)
          ? 'lucide'
          : 'unknown';

  onMount(() => {
    if (mode !== 'lucide') return;
    const slug = trimmed;
    if (iconCache.has(slug)) {
      LucideComp = iconCache.get(slug) ?? null;
      return;
    }
    // Vite/SvelteKit resolves this at build time but the actual chunk is
    // only fetched when this code path runs. Errors (slug typo, network)
    // are swallowed — surrounding label keeps the symptom legible.
    import(/* @vite-ignore */ `@lucide/svelte/icons/${slug}.svelte`)
      .then((mod) => {
        const comp = mod.default;
        if (!comp) return;
        iconCache.set(slug, comp);
        LucideComp = comp;
      })
      .catch(() => {
        // Intentionally silent: missing icon must not break the form.
        LucideComp = null;
      });
  });
</script>

{#if mode === 'emoji'}
  <span
    class="icon-render-emoji"
    role={label ? 'img' : undefined}
    aria-label={label}
    aria-hidden={label ? undefined : 'true'}
  >
    {trimmed}
  </span>
{:else if mode === 'lucide' && LucideComp}
  <svelte:component
    this={LucideComp}
    {size}
    aria-hidden={label ? undefined : 'true'}
    aria-label={label}
    role={label ? 'img' : undefined}
  />
{/if}

<style>
  .icon-render-emoji {
    display: inline-block;
    line-height: 1;
    font-size: 1.05em;
  }
</style>
