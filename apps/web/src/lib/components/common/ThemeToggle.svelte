<script lang="ts">
  /**
   * ThemeToggle — shared light/dark toggle button.
   *
   * Extracted so every screen with chrome (home, auth shell, /entries/new …)
   * exposes the same control. Two visual variants:
   *
   *   - `withLabel = true`  (default): icon + localized target theme label,
   *     used on screens with enough horizontal room (home top bar, entry view).
   *   - `withLabel = false`: icon only, used in compact headers (auth shell).
   *
   * The component is purely presentational — it only flips the global
   * `theme` store, which persists to localStorage and toggles the
   * `data-theme` attribute on `<html>` (see `$lib/stores/theme`).
   */

  import { _ } from 'svelte-i18n';
  import { theme } from '$lib/stores/theme';

  /** Show the textual label next to the icon. */
  export let withLabel: boolean = true;
  /** Icon edge length in px. */
  export let iconSize: number = 18;
  /** Optional override for `data-testid` (handy in route-specific tests). */
  export let testId: string | undefined = undefined;

  $: currentTheme = $theme;
  $: ariaLabel = currentTheme === 'dark' ? $_('theme.toggle_light') : $_('theme.toggle_dark');
</script>

<button
  type="button"
  class="btn btn-sm variant-ghost-surface"
  on:click={() => theme.toggle()}
  aria-label={ariaLabel}
  data-testid={testId ?? 'theme-toggle'}
>
  {#if currentTheme === 'dark'}
    <svg
      width={iconSize}
      height={iconSize}
      viewBox="0 0 24 24"
      fill="none"
      stroke="currentColor"
      stroke-width="2"
      aria-hidden="true"
    >
      <circle cx="12" cy="12" r="5" />
      <path
        d="M12 1v2M12 21v2M4.22 4.22l1.42 1.42M18.36 18.36l1.42 1.42M1 12h2M21 12h2M4.22 19.78l1.42-1.42M18.36 5.64l1.42-1.42"
      />
    </svg>
    {#if withLabel}<span>{$_('theme.light')}</span>{/if}
  {:else}
    <svg
      width={iconSize}
      height={iconSize}
      viewBox="0 0 24 24"
      fill="none"
      stroke="currentColor"
      stroke-width="2"
      aria-hidden="true"
    >
      <path d="M21 12.79A9 9 0 1 1 11.21 3 7 7 0 0 0 21 12.79z" />
    </svg>
    {#if withLabel}<span>{$_('theme.dark')}</span>{/if}
  {/if}
</button>
