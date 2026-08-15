import { render, screen, fireEvent, waitFor } from '@testing-library/svelte';
import { describe, expect, it, vi } from 'vitest';
import Page from './+page.svelte';

vi.mock('svelte-i18n', async () => {
  const { readable } = await import('svelte/store');
  return { _: readable((key: string) => key), locale: readable('en') };
});

const { logoutMock, gotoMock, deleteAccountMock } = vi.hoisted(() => ({
  logoutMock: vi.fn(async () => undefined),
  gotoMock: vi.fn(),
  deleteAccountMock: vi.fn(async () => undefined),
}));

vi.mock('$lib/stores/auth', async () => {
  const { readable } = await import('svelte/store');
  return {
    auth: readable({ status: 'authenticated', user: { id: 'user-1', email: 'user@example.com' } }),
    logout: logoutMock,
  };
});
vi.mock('$app/navigation', () => ({ goto: gotoMock }));
vi.mock('$lib/api/user', () => ({ deleteAccount: deleteAccountMock }));
vi.mock('$lib/api/consents', () => ({
  HEALTH_CONNECT_CONSENT_TYPE: 'health_connect',
  HEALTH_CONNECT_CONSENT_VERSION: '1',
  fetchUserConsents: vi.fn(async () => ({ current: [], history: [] })),
  recordUserConsent: vi.fn(),
  revokeUserConsent: vi.fn(),
}));
vi.mock('$lib/healthConnect/consent', () => ({ getHealthConnectConsentStatus: () => null }));

describe('/settings/privacy', () => {
  it('renders consent, privacy policy, delete and logout controls', async () => {
    render(Page);
    expect(await screen.findByTestId('settings-health-connect-consent')).toBeTruthy();
    expect(screen.getByTestId('settings-privacy-policy')).toBeTruthy();
    expect(screen.getByTestId('settings-delete-account')).toBeTruthy();
    expect(screen.getByTestId('settings-logout')).toBeTruthy();
  });

  it('logs the user out and returns home', async () => {
    render(Page);
    await fireEvent.click(await screen.findByTestId('settings-logout'));
    await waitFor(() => expect(logoutMock).toHaveBeenCalled());
    expect(gotoMock).toHaveBeenCalledWith('/', { replaceState: true });
  });

  it('deletes the account after password confirmation', async () => {
    render(Page);
    await fireEvent.click(await screen.findByTestId('settings-delete-account'));
    await fireEvent.input(await screen.findByTestId('settings-delete-password'), {
      target: { value: 'hunter2' },
    });
    await fireEvent.click(screen.getByTestId('settings-delete-confirm'));
    await waitFor(() => expect(deleteAccountMock).toHaveBeenCalledWith({ password: 'hunter2' }));
  });
});
