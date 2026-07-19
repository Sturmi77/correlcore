<script lang="ts">
  /**
   * Pull-to-refresh chrome for the authenticated app scroll shell.
   *
   * Gesture attaches to `scrollElement` (the overflow-y main). Pages register
   * refresh work via `registerPageRefresh`; this component only owns the
   * pull UI and trigger.
   */
  import { onDestroy, onMount } from 'svelte';
  import { _ } from 'svelte-i18n';
  import IconRender from './IconRender.svelte';
  import { pageRefresh, runRegisteredPageRefresh } from '$lib/stores/pageRefresh';
  import { ICON_SIZE_MD } from '$lib/constants/iconSizes';

  /** Scroll container that owns overflow-y (typically `#main-content`). */
  export let scrollElement: HTMLElement | null = null;
  /** When true, gesture is ignored (e.g. entry sheet open). */
  export let disabled = false;

  const THRESHOLD_PX = 72;
  const MAX_PULL_PX = 112;
  const DEADZONE_PX = 8;

  let pullPx = 0;
  let tracking = false;
  let armed = false;
  let startY = 0;
  let reduceMotion = false;
  let attachedElement: HTMLElement | null = null;

  $: canRefresh = !disabled && $pageRefresh.hasHandler;
  $: refreshing = $pageRefresh.refreshing;
  $: indicatorVisible = pullPx > DEADZONE_PX || refreshing;
  $: statusLabel = refreshing
    ? $_('a11y.pull_to_refresh.refreshing')
    : pullPx >= THRESHOLD_PX
      ? $_('a11y.pull_to_refresh.release')
      : $_('a11y.pull_to_refresh.pull');

  function detachScrollElement(): void {
    if (!attachedElement) return;
    attachedElement.removeEventListener('touchstart', onTouchStart);
    attachedElement.removeEventListener('touchmove', onTouchMove);
    attachedElement.removeEventListener('touchend', onTouchEnd);
    attachedElement.removeEventListener('touchcancel', onTouchCancel);
    attachedElement = null;
  }

  function attachScrollElement(el: HTMLElement | null): void {
    if (attachedElement === el) return;
    detachScrollElement();
    if (!el) return;
    el.addEventListener('touchstart', onTouchStart, { passive: true });
    el.addEventListener('touchmove', onTouchMove, { passive: false });
    el.addEventListener('touchend', onTouchEnd, { passive: true });
    el.addEventListener('touchcancel', onTouchCancel, { passive: true });
    attachedElement = el;
  }

  $: attachScrollElement(scrollElement);

  onMount(() => {
    reduceMotion =
      typeof window !== 'undefined' &&
      window.matchMedia('(prefers-reduced-motion: reduce)').matches;
  });

  onDestroy(() => {
    detachScrollElement();
  });

  function resetPull(): void {
    tracking = false;
    armed = false;
    startY = 0;
    if (!refreshing) pullPx = 0;
  }

  function onTouchStart(event: TouchEvent): void {
    if (!canRefresh || refreshing) return;
    if (event.touches.length !== 1) return;
    if (!scrollElement || scrollElement.scrollTop > 0) return;
    tracking = true;
    armed = false;
    startY = event.touches[0].clientY;
    pullPx = 0;
  }

  function onTouchMove(event: TouchEvent): void {
    if (!tracking || !canRefresh || refreshing) return;
    if (event.touches.length !== 1) {
      resetPull();
      return;
    }
    if (scrollElement && scrollElement.scrollTop > 0) {
      resetPull();
      return;
    }

    const delta = event.touches[0].clientY - startY;
    if (delta <= DEADZONE_PX) {
      if (armed) {
        armed = false;
        pullPx = 0;
      }
      return;
    }

    armed = true;
    // Rubber-band: diminishing returns past threshold.
    const overshoot = Math.max(0, delta - DEADZONE_PX);
    const nextPull = Math.min(MAX_PULL_PX, overshoot * 0.55);
    pullPx = reduceMotion ? Math.min(THRESHOLD_PX, nextPull) : nextPull;
    if (pullPx > 0) {
      event.preventDefault();
    }
  }

  async function onTouchEnd(): Promise<void> {
    if (!tracking) return;
    const shouldRefresh = armed && pullPx >= THRESHOLD_PX && canRefresh && !refreshing;
    tracking = false;
    armed = false;
    startY = 0;

    if (!shouldRefresh) {
      pullPx = 0;
      return;
    }

    pullPx = THRESHOLD_PX;
    await runRegisteredPageRefresh();
    pullPx = 0;
  }

  function onTouchCancel(): void {
    resetPull();
  }
</script>

<div
  class="ptr"
  class:ptr--active={indicatorVisible}
  class:ptr--refreshing={refreshing}
  style="--ptr-pull: {refreshing ? THRESHOLD_PX : pullPx}px"
  data-testid="pull-to-refresh"
>
  <div
    class="ptr__indicator"
    aria-live="polite"
    aria-atomic="true"
    aria-busy={refreshing}
    data-testid="pull-to-refresh-indicator"
  >
    <span class="ptr__icon" class:ptr__icon--spin={refreshing} aria-hidden="true">
      <IconRender icon="refresh-cw" size={ICON_SIZE_MD} />
    </span>
    <span class="ptr__label">{indicatorVisible ? statusLabel : ''}</span>
  </div>
  <div class="ptr__content">
    <slot />
  </div>
</div>

<style>
  .ptr {
    position: relative;
    min-height: 100%;
  }

  .ptr__indicator {
    display: flex;
    align-items: center;
    justify-content: center;
    gap: var(--space-2);
    height: var(--ptr-pull);
    max-height: 7rem;
    overflow: hidden;
    color: var(--color-text-muted);
    font-size: var(--text-sm);
    pointer-events: none;
  }

  .ptr__icon {
    display: inline-flex;
    transition: transform 120ms ease-out;
    transform: rotate(calc(var(--ptr-pull) * 2.5deg));
  }

  .ptr__icon--spin {
    animation: ptr-spin 0.8s linear infinite;
    transform: none;
  }

  .ptr__label {
    min-height: 1.25em;
  }

  .ptr__content {
    min-height: 100%;
  }

  @media (prefers-reduced-motion: reduce) {
    .ptr__icon,
    .ptr__icon--spin {
      transition: none;
      animation: none;
      transform: none;
    }
  }

  @keyframes ptr-spin {
    to {
      transform: rotate(360deg);
    }
  }
</style>
