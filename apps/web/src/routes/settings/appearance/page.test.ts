import { render, screen, fireEvent, waitFor } from '@testing-library/svelte';
import { describe, expect, it, vi } from 'vitest';
import Page from './+page.svelte';

vi.mock('svelte-i18n', async () => {
  const { readable, writable } = await import('svelte/store');
  return { _: readable((key: string) => key), locale: writable('de') };
});

vi.mock('$lib/i18n', async () => {
  const i18n = await import('svelte-i18n');
  return {
    setAppLocale: vi.fn((next: string) => i18n.locale.set(next)),
  };
});

describe('/settings/appearance', () => {
  it('renders theme, language and layout links', async () => {
    render(Page);
    expect(await screen.findByTestId('settings-language-control')).toBeTruthy();
    expect(screen.getByTestId('settings-theme-toggle-panel')).toBeTruthy();
    expect(screen.getByTestId('settings-home-layout')).toBeTruthy();
    expect(screen.getByTestId('settings-app-open')).toBeTruthy();
  });

  it('switches locale through the segmented language control', async () => {
    render(Page);
    await fireEvent.click(await screen.findByTestId('language-en'));
    await waitFor(() =>
      expect(screen.getByTestId('language-en').getAttribute('aria-pressed')).toBe('true')
    );
  });
});
