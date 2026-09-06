import { render, screen, fireEvent, waitFor } from '@testing-library/svelte';
import { describe, expect, it, vi } from 'vitest';
import Page from './+page.svelte';

vi.mock('svelte-i18n', async () => {
  const { readable } = await import('svelte/store');
  return { _: readable((key: string) => key), locale: readable('en') };
});

vi.mock('$lib/stores/auth', async () => {
  const { readable } = await import('svelte/store');
  return {
    auth: readable({ status: 'authenticated', user: { id: 'user-1', email: 'user@example.com' } }),
  };
});

vi.mock('$app/stores', async () => {
  const { readable } = await import('svelte/store');
  return {
    page: readable({ url: new URL('http://localhost/settings/analysis') }),
  };
});

const { updatePrefsMock, regenerateMock, fetchDigestMock } = vi.hoisted(() => ({
  updatePrefsMock: vi.fn(async (p: Record<string, boolean>) => ({
    analytics_enabled: p.analytics_enabled ?? true,
    digest_enabled: p.digest_enabled ?? false,
  })),
  regenerateMock: vi.fn(async () => ({ insight_count: 5 })),
  fetchDigestMock: vi.fn(async () => {
    throw new Error('no digest');
  }),
}));

vi.mock('$lib/api/preferences', () => ({
  fetchUserPreferences: vi.fn(async () => ({ analytics_enabled: true, digest_enabled: false })),
  updateUserPreferences: updatePrefsMock,
}));
vi.mock('$lib/api/insights', () => ({
  regenerateInsights: regenerateMock,
  fetchLatestInsightDigest: fetchDigestMock,
}));

describe('/settings/analysis', () => {
  it('renders analytics + digest toggles and regenerate control', async () => {
    render(Page);
    expect(await screen.findByTestId('analytics-toggle')).toBeTruthy();
    expect(screen.getByTestId('digest-toggle')).toBeTruthy();
    expect(screen.getByTestId('regenerate-insights')).toBeTruthy();
    expect(screen.getByTestId('digest-preview-link')).toBeTruthy();
  });

  it('persists the analytics toggle', async () => {
    render(Page);
    const toggle = (await screen.findByTestId('analytics-toggle')) as HTMLInputElement;
    await fireEvent.click(toggle);
    await waitFor(() =>
      expect(updatePrefsMock).toHaveBeenCalledWith(
        expect.objectContaining({ analytics_enabled: false })
      )
    );
  });

  it('regenerates insights on demand', async () => {
    render(Page);
    await fireEvent.click(await screen.findByTestId('regenerate-insights'));
    await waitFor(() => expect(regenerateMock).toHaveBeenCalled());
  });

  it('shows pending digest hint after enabling when no snapshot exists', async () => {
    render(Page);
    const toggle = (await screen.findByTestId('digest-toggle')) as HTMLInputElement;
    await fireEvent.click(toggle);
    await waitFor(() =>
      expect(updatePrefsMock).toHaveBeenCalledWith(
        expect.objectContaining({ digest_enabled: true })
      )
    );
    expect(await screen.findByTestId('digest-pending-hint')).toBeTruthy();
  });
});
