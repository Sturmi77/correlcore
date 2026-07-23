<script lang="ts">
  import { page } from '$app/stores';
  import { _ } from 'svelte-i18n';
  import ChartLine from 'lucide-svelte/icons/chart-line';
  import Lightbulb from 'lucide-svelte/icons/lightbulb';
  import Settings from 'lucide-svelte/icons/settings';
  import type { ComponentType } from 'svelte';
  import CorrelCoreLogo from '$lib/components/common/CorrelCoreLogo.svelte';
  import { BRAND_MARK_MD, BRAND_MARK_SM, ICON_SIZE_MD } from '$lib/constants/iconSizes';
  import { isNavItemActive, NAV_ITEMS, type NavItemConfig } from '$lib/navigation/appNav';

  type LucideNavIcon = Exclude<NavItemConfig['icon'], 'home'>;

  const LUCIDE_ICONS: Record<LucideNavIcon, ComponentType> = {
    lightbulb: Lightbulb,
    'chart-line': ChartLine,
    settings: Settings,
  };

  $: pathname = $page.url.pathname;
</script>

<nav class="app-nav" aria-label={$_('nav.aria_label')}>
  <!--
    Desktop rail brand only (hidden on mobile bottom bar via CSS).
    Presentational on purpose: the Home nav item below already links to "/" with
    the same mark, so a second link here would put five links in the navigation
    landmark and duplicate the Home affordance for screen readers (#448).
  -->
  <span class="app-nav__brand" aria-hidden="true" data-testid="app-nav-brand">
    <CorrelCoreLogo size={BRAND_MARK_MD} title="" />
  </span>
  <ul class="app-nav__list">
    {#each NAV_ITEMS as item (item.href)}
      {@const active = isNavItemActive(pathname, item.href, item.match)}
      <li class="app-nav__item-wrap">
        <a
          href={item.href}
          class="app-nav__item"
          class:app-nav__item--active={active}
          aria-current={active ? 'page' : undefined}
          aria-label={$_(item.labelKey)}
        >
          {#if item.icon === 'home'}
            <span
              class="app-nav__home-mark"
              class:app-nav__home-mark--active={active}
              data-testid="app-nav-home-mark"
            >
              <CorrelCoreLogo size={BRAND_MARK_SM} title="" />
            </span>
          {:else}
            {@const Icon = LUCIDE_ICONS[item.icon]}
            <Icon size={ICON_SIZE_MD} strokeWidth={active ? 2.25 : 2} aria-hidden="true" />
          {/if}
          <span class="app-nav__label">{$_(item.labelKey)}</span>
        </a>
      </li>
    {/each}
  </ul>
</nav>
