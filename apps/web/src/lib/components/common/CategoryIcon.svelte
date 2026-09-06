<script lang="ts">
  /**
   * CategoryIcon — one curated, statically-imported Lucide icon per tag
   * category (#672).
   *
   * Unlike IconRender's per-item dynamic import (which fetches
   * `@lucide/svelte/icons/<slug>` at runtime and silently renders nothing on a
   * typo or a Lucide rename), these eight icons are imported statically: they
   * are tree-shaken, verified at build time, and never blank. Category-level
   * iconography replaces the fragile, largely-decorative per-tag glyphs — the
   * tag name (always shown) plus the category colour carry per-item identity.
   */
  import type { TagCategory } from '$lib/api/tags';
  import { ICON_SIZE_SM } from '$lib/constants/iconSizes';
  import type { Component } from 'svelte';
  import type { LucideProps } from '@lucide/svelte';

  import Dumbbell from '@lucide/svelte/icons/dumbbell';
  import Users from '@lucide/svelte/icons/users';
  import Briefcase from '@lucide/svelte/icons/briefcase';
  import Sparkles from '@lucide/svelte/icons/sparkles';
  import Utensils from '@lucide/svelte/icons/utensils';
  import HeartPulse from '@lucide/svelte/icons/heart-pulse';
  import RotateCw from '@lucide/svelte/icons/rotate-cw';
  import Shapes from '@lucide/svelte/icons/shapes';

  export let category: TagCategory;
  export let size: number = ICON_SIZE_SM;

  const icons = {
    sport: Dumbbell,
    social: Users,
    work: Briefcase,
    leisure: Sparkles,
    consumption: Utensils,
    health: HeartPulse,
    cycle: RotateCw,
    other: Shapes,
  } satisfies Record<TagCategory, Component<LucideProps>>;

  $: Icon = icons[category];
</script>

<svelte:component this={Icon} {size} aria-hidden="true" />
