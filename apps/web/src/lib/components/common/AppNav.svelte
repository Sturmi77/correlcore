<script lang="ts">
  import { page } from '$app/stores';
  import { _ } from 'svelte-i18n';
  import ChartLine from 'lucide-svelte/icons/chart-line';
  import House from 'lucide-svelte/icons/house';
  import Lightbulb from 'lucide-svelte/icons/lightbulb';
  import Settings from 'lucide-svelte/icons/settings';
  import CorrelCoreLogo from '$lib/components/common/CorrelCoreLogo.svelte';
  import { ICON_SIZE_MD } from '$lib/constants/iconSizes';
  import { isNavItemActive, NAV_ITEMS, type NavItemConfig } from '$lib/navigation/appNav';

  const ICONS: Record<NavItemConfig['icon'], typeof House> = {
    home: House,
    lightbulb: Lightbulb,
    'chart-line': ChartLine,
    settings: Settings,
  };

  $: pathname = $page.url.pathname;
</script>

<nav class="app-nav" aria-label={$_('nav.aria_label')}>
  <!-- Desktop rail brand only (hidden on mobile bottom bar via CSS). -->
  <a href="/" class="app-nav__brand" aria-label={$_('app.name')} data-testid="app-nav-brand">
    <CorrelCoreLogo size={24} title="" />
  </a>
  <ul class="app-nav__list">
    {#each NAV_ITEMS as item (item.href)}
      {@const active = isNavItemActive(pathname, item.href, item.match)}
      {@const Icon = ICONS[item.icon]}
      <li class="app-nav__item-wrap">
        <a
          href={item.href}
          class="app-nav__item"
          class:app-nav__item--active={active}
          aria-current={active ? 'page' : undefined}
          aria-label={$_(item.labelKey)}
        >
          <Icon size={ICON_SIZE_MD} strokeWidth={active ? 2.25 : 2} aria-hidden="true" />
          <span class="app-nav__label">{$_(item.labelKey)}</span>
        </a>
      </li>
    {/each}
  </ul>
</nav>
