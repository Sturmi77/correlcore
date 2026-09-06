import { render, screen } from '@testing-library/svelte';
import { readable } from 'svelte/store';
import { describe, expect, it, vi } from 'vitest';
import SettingsCategoryBar from './SettingsCategoryBar.svelte';

vi.mock('svelte-i18n', () => ({
  _: readable((key: string) => key),
}));

vi.mock('$app/stores', () => ({
  page: readable({ url: new URL('http://localhost/settings/analysis') }),
}));

describe('SettingsCategoryBar', () => {
  it('renders real category links and highlights the active route', () => {
    render(SettingsCategoryBar);

    const bar = screen.getByTestId('settings-category-bar');
    expect(bar).toBeTruthy();

    const analysis = screen.getByTestId('settings-cat-analysis') as HTMLAnchorElement;
    expect(analysis.getAttribute('href')).toBe('/settings/analysis');
    expect(analysis.getAttribute('aria-current')).toBe('page');

    const data = screen.getByTestId('settings-cat-data') as HTMLAnchorElement;
    expect(data.getAttribute('href')).toBe('/settings/data');
    expect(data.getAttribute('aria-current')).toBeNull();
  });
});
