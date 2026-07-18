<script lang="ts">
  /**
   * Brand mark — 3×3 heatmap grid matching correlcore-logo-mark-*.svg.
   * Colors come from theme tokens so light/dark switch without asset swaps.
   * Pass an empty `title` when the mark is decorative (e.g. inside a labeled link).
   */
  export let size = 64;
  export let title = 'CorrelCore';

  $: decorative = title.trim().length === 0;
</script>

<svg
  aria-label={decorative ? undefined : title}
  aria-hidden={decorative ? 'true' : undefined}
  role={decorative ? 'presentation' : 'img'}
  viewBox="0 0 36 36"
  width={size}
  height={size}
  fill="none"
  xmlns="http://www.w3.org/2000/svg"
>
  <rect x="0" y="0" width="10" height="10" rx="2" fill="var(--color-heatmap-1)" />
  <rect x="13" y="0" width="10" height="10" rx="2" fill="var(--color-heatmap-2)" />
  <rect x="26" y="0" width="10" height="10" rx="2" fill="var(--color-heatmap-3)" />
  <rect x="0" y="13" width="10" height="10" rx="2" fill="var(--color-heatmap-2)" />
  <rect x="13" y="13" width="10" height="10" rx="2" fill="var(--color-heatmap-3)" />
  <rect x="26" y="13" width="10" height="10" rx="2" fill="var(--color-heatmap-4)" />
  <rect x="0" y="26" width="10" height="10" rx="2" fill="var(--color-heatmap-3)" />
  <rect x="13" y="26" width="10" height="10" rx="2" fill="var(--color-heatmap-4)" />
  <rect x="26" y="26" width="10" height="10" rx="2" fill="var(--color-primary)" />
</svg>
