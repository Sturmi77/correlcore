<script lang="ts">
  import { page } from '$app/stores';
  import { _ } from 'svelte-i18n';
  import {
    SETTINGS_CATEGORIES,
    isSettingsCategoryActive,
  } from '$lib/navigation/settingsCategories';
</script>

<nav
  class="settings-category-bar"
  aria-label={$_('settings.category_nav.aria_label')}
  data-testid="settings-category-bar"
>
  {#each SETTINGS_CATEGORIES as cat (cat.href)}
    {@const active = isSettingsCategoryActive($page.url.pathname, cat.href)}
    <a
      class="settings-category-bar__item"
      class:settings-category-bar__item--active={active}
      href={cat.href}
      aria-current={active ? 'page' : undefined}
      data-testid={cat.testId}
    >
      {$_(`settings.category_nav.${cat.key}`)}
    </a>
  {/each}
</nav>

<style>
  .settings-category-bar {
    display: flex;
    flex-wrap: wrap;
    gap: var(--space-1);
    padding: var(--space-1);
    border: 1px solid var(--color-border-chart);
    border-radius: var(--radius-md);
    background: var(--color-surface);
  }

  .settings-category-bar__item {
    display: inline-flex;
    align-items: center;
    justify-content: center;
    flex: 1 1 0;
    min-width: 44px;
    min-height: 44px;
    border: 1px solid transparent;
    border-radius: var(--radius-sm);
    padding: 0.45rem 0.7rem;
    color: var(--color-text-muted);
    font: inherit;
    font-size: var(--text-sm);
    font-weight: 650;
    line-height: 1.2;
    text-align: center;
    text-decoration: none;
    transition:
      background-color var(--transition-interactive),
      border-color var(--transition-interactive),
      color var(--transition-interactive);
  }

  .settings-category-bar__item--active {
    border-color: color-mix(in srgb, var(--color-primary) 25%, transparent);
    background: var(--color-primary-highlight);
    color: var(--color-primary);
  }

  @media (hover: hover) {
    .settings-category-bar__item:not(.settings-category-bar__item--active):hover {
      color: var(--color-text);
      background: var(--color-surface-offset);
    }
  }

  @media (max-width: 480px) {
    .settings-category-bar {
      flex-wrap: nowrap;
      margin-inline: calc(var(--space-2) * -1);
      padding-inline: var(--space-2);
      overflow-x: auto;
      overscroll-behavior-x: contain;
      scrollbar-width: none;
      scroll-padding-inline: var(--space-2);
      -webkit-overflow-scrolling: touch;
    }

    .settings-category-bar::-webkit-scrollbar {
      display: none;
    }

    .settings-category-bar__item {
      flex: 0 0 auto;
    }
  }
</style>
