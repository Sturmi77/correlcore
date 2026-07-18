<script lang="ts">
  // One-shot brand-load animation shown while the app boots (i18n dict load /
  // auth hydrate). Purely CSS-driven — no timers, no artificial delay: it is
  // on screen only as long as the real loading state it replaces.
  export let label = '';
</script>

<div class="cc-splash" role="status" aria-live="polite" aria-busy="true">
  <div class="cc-splash-mark" aria-hidden="true">
    <span class="cc-tile" style="--i: 0; background: var(--color-heatmap-1);"></span>
    <span class="cc-tile" style="--i: 1; background: var(--color-heatmap-2);"></span>
    <span class="cc-tile" style="--i: 2; background: var(--color-heatmap-3);"></span>
    <span class="cc-tile" style="--i: 3; background: var(--color-heatmap-2);"></span>
    <span class="cc-tile" style="--i: 4; background: var(--color-heatmap-3);"></span>
    <span class="cc-tile" style="--i: 5; background: var(--color-heatmap-4);"></span>
    <span class="cc-tile" style="--i: 6; background: var(--color-heatmap-3);"></span>
    <span class="cc-tile" style="--i: 7; background: var(--color-heatmap-4);"></span>
    <span class="cc-tile" style="--i: 8; background: var(--color-primary);"></span>
  </div>
  <div class="cc-splash-word">
    <span class="cc-word-a">correl</span><span class="cc-word-b">core</span>
  </div>
  {#if label}<span class="sr-only">{label}</span>{/if}
</div>

<style>
  .cc-splash {
    flex: 1;
    width: 100%;
    display: flex;
    flex-direction: column;
    align-items: center;
    justify-content: center;
    gap: var(--space-4, 16px);
    background: var(--color-bg);
  }

  .cc-splash-mark {
    display: grid;
    grid-template-columns: repeat(3, 1fr);
    grid-template-rows: repeat(3, 1fr);
    gap: 6px;
    width: 64px;
    height: 64px;
  }

  .cc-tile {
    border-radius: var(--radius-sm, 4px);
    transform: scale(0.2);
    opacity: 0;
    animation: cc-tile-in 320ms cubic-bezier(0.16, 1, 0.3, 1) forwards;
    animation-delay: calc(var(--i) * 55ms);
  }

  @keyframes cc-tile-in {
    to {
      transform: scale(1);
      opacity: 1;
    }
  }

  .cc-splash-word {
    font-size: var(--text-lg, 20px);
    font-weight: 750;
    letter-spacing: -0.01em;
    opacity: 0;
    transform: translateY(8px);
    animation: cc-word-in 260ms cubic-bezier(0.16, 1, 0.3, 1) forwards;
    animation-delay: 520ms;
  }

  @keyframes cc-word-in {
    to {
      opacity: 1;
      transform: translateY(0);
    }
  }

  .cc-word-a {
    color: var(--color-text);
  }

  .cc-word-b {
    color: var(--color-primary);
  }

  @media (prefers-reduced-motion: reduce) {
    .cc-tile,
    .cc-splash-word {
      animation-duration: 1ms;
      animation-delay: 0ms;
      transform: none;
      opacity: 1;
    }
  }
</style>
