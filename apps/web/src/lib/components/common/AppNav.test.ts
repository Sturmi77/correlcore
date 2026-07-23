import { render, screen } from '@testing-library/svelte';
import { readable } from 'svelte/store';
import { describe, expect, it, vi } from 'vitest';
import AppNav from './AppNav.svelte';

vi.mock('svelte-i18n', () => ({
  _: readable((key: string) => key),
}));

vi.mock('$app/stores', () => ({
  page: readable({ url: { pathname: '/insights' } }),
}));

describe('AppNav', () => {
  it('renders four primary destinations with accessible labels', () => {
    render(AppNav);

    expect(screen.getByRole('navigation', { name: 'nav.aria_label' })).toBeTruthy();
    expect(screen.getByTestId('app-nav-brand')).toBeTruthy();
    expect(screen.getByRole('link', { name: 'nav.home' }).getAttribute('href')).toBe('/');
    expect(screen.getByTestId('app-nav-home-mark')).toBeTruthy();
    expect(screen.getByRole('link', { name: 'nav.insights' }).getAttribute('href')).toBe(
      '/insights'
    );
    expect(screen.getByRole('link', { name: 'nav.trends' }).getAttribute('href')).toBe('/trends');
    expect(screen.getByRole('link', { name: 'nav.settings' }).getAttribute('href')).toBe(
      '/settings'
    );
  });

  it('exposes exactly the four primary destinations in the nav landmark (#448)', () => {
    render(AppNav);

    const nav = screen.getByRole('navigation', { name: 'nav.aria_label' });
    // The brand mark is presentational; a fifth link here would duplicate Home
    // and break the shell contract in surface-foundation.spec.ts.
    expect(nav.querySelectorAll('a')).toHaveLength(4);
    expect(screen.getByTestId('app-nav-brand').tagName).toBe('SPAN');
  });

  it('marks the active route with aria-current', () => {
    render(AppNav);

    expect(screen.getByRole('link', { name: 'nav.insights' }).getAttribute('aria-current')).toBe(
      'page'
    );
    expect(screen.getByRole('link', { name: 'nav.home' }).getAttribute('aria-current')).toBeNull();
  });
});
