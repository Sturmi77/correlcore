<script lang="ts">
  import { page } from '$app/stores';
  import { _ } from 'svelte-i18n';
  import ChartLine from 'lucide-svelte/icons/chart-line';
  import House from 'lucide-svelte/icons/house';
  import Lightbulb from 'lucide-svelte/icons/lightbulb';
  import Settings from 'lucide-svelte/icons/settings';
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
          <Icon size={22} strokeWidth={active ? 2.25 : 2} aria-hidden="true" />
          <span class="app-nav__label">{$_(item.labelKey)}</span>
        </a>
      </li>
    {/each}
  </ul>
</nav>
