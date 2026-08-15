import { render, screen, fireEvent, waitFor } from '@testing-library/svelte';
import { describe, expect, it, vi, beforeEach } from 'vitest';

vi.mock('svelte-i18n', async () => {
  const { readable } = await import('svelte/store');
  return {
    _: readable((key: string) => key),
    locale: readable('en'),
  };
});

// Auth store — swapped per test via the hoisted writable handle.
interface AuthTestState {
  status: 'loading' | 'authenticated' | 'anonymous';
  user?: { id: string; email: string; is_verified: boolean; is_admin?: boolean };
}

const { gotoMock, authHelpers } = vi.hoisted(() => ({
  gotoMock: vi.fn(),
  authHelpers: {} as { store?: import('svelte/store').Writable<AuthTestState> },
}));

vi.mock('$app/navigation', () => ({ goto: gotoMock }));

vi.mock('$lib/stores/auth', async () => {
  const { writable } = await import('svelte/store');
  const auth = writable<AuthTestState>({
    status: 'authenticated',
    user: { id: 'admin-1', email: 'admin@example.com', is_verified: true, is_admin: true },
  });
  authHelpers.store = auth;
  return { auth: { subscribe: auth.subscribe } };
});

const {
  fetchAdminUsersMock,
  fetchAdminUserMock,
  setAdminUserActiveMock,
  deleteAdminUserMock,
  triggerAdminPasswordResetMock,
} = vi.hoisted(() => ({
  fetchAdminUsersMock: vi.fn(),
  fetchAdminUserMock: vi.fn(),
  setAdminUserActiveMock: vi.fn(),
  deleteAdminUserMock: vi.fn(),
  triggerAdminPasswordResetMock: vi.fn(),
}));

vi.mock('$lib/api/admin', () => ({
  fetchAdminUsers: fetchAdminUsersMock,
  fetchAdminUser: fetchAdminUserMock,
  setAdminUserActive: setAdminUserActiveMock,
  deleteAdminUser: deleteAdminUserMock,
  triggerAdminPasswordReset: triggerAdminPasswordResetMock,
}));

// ApiError needs to be the real class so `instanceof` checks in the page work.
vi.mock('$lib/api/client', async () => {
  const actual = await vi.importActual<typeof import('$lib/api/client')>('$lib/api/client');
  return actual;
});

import Page from './+page.svelte';
import { ApiError } from '$lib/api/client';

function makeUser(over: Partial<Record<string, unknown>> = {}) {
  return {
    id: 'user-2',
    email: 'jane@example.com',
    display_name: 'Jane',
    is_active: true,
    is_verified: true,
    is_admin: false,
    created_at: '2026-05-01T10:00:00Z',
    ...over,
  };
}

describe('/admin user management', () => {
  beforeEach(() => {
    gotoMock.mockClear();
    fetchAdminUsersMock.mockReset();
    fetchAdminUserMock.mockReset();
    setAdminUserActiveMock.mockReset();
    deleteAdminUserMock.mockReset();
    triggerAdminPasswordResetMock.mockReset();
    authHelpers.store?.set({
      status: 'authenticated',
      user: { id: 'admin-1', email: 'admin@example.com', is_verified: true, is_admin: true },
    });
    fetchAdminUsersMock.mockResolvedValue({ items: [makeUser()], total: 1, limit: 50, offset: 0 });
  });

  it('lists users for an admin', async () => {
    render(Page);
    expect(await screen.findByTestId('admin-user-table')).toBeTruthy();
    expect(screen.getByText('jane@example.com')).toBeTruthy();
    expect(fetchAdminUsersMock).toHaveBeenCalled();
  });

  it('shows a forbidden state and never calls the API for a non-admin', async () => {
    authHelpers.store?.set({
      status: 'authenticated',
      user: { id: 'u-9', email: 'u9@example.com', is_verified: true, is_admin: false },
    });
    render(Page);
    expect(await screen.findByTestId('admin-forbidden')).toBeTruthy();
    expect(fetchAdminUsersMock).not.toHaveBeenCalled();
  });

  it('redirects anonymous visitors to login', async () => {
    authHelpers.store?.set({ status: 'anonymous' });
    render(Page);
    await waitFor(() => expect(gotoMock).toHaveBeenCalledWith('/auth/login?next=/admin'));
  });

  it('forwards the email search query to the API', async () => {
    render(Page);
    await screen.findByTestId('admin-user-table');

    await fireEvent.input(screen.getByTestId('admin-search-input'), {
      target: { value: 'jane' },
    });
    await fireEvent.submit(screen.getByTestId('admin-search-form'));

    await waitFor(() =>
      expect(fetchAdminUsersMock).toHaveBeenLastCalledWith(
        expect.objectContaining({ query: 'jane', offset: 0 })
      )
    );
  });

  it('disables a user via the toggle action', async () => {
    setAdminUserActiveMock.mockResolvedValue({ ...makeUser(), is_active: false });
    render(Page);
    await screen.findByTestId('admin-user-table');

    await fireEvent.click(screen.getByTestId('admin-toggle-user-2'));

    await waitFor(() => expect(setAdminUserActiveMock).toHaveBeenCalledWith('user-2', false));
  });

  it('requires the typed email before a delete can be confirmed', async () => {
    fetchAdminUserMock.mockResolvedValue({
      ...makeUser(),
      updated_at: '2026-05-02T10:00:00Z',
      entry_count: 7,
    });
    deleteAdminUserMock.mockResolvedValue(undefined);
    render(Page);
    await screen.findByTestId('admin-user-table');

    await fireEvent.click(screen.getByTestId('admin-delete-user-2'));
    const confirmBtn = (await screen.findByTestId('admin-delete-confirm')) as HTMLButtonElement;
    expect(confirmBtn.disabled).toBe(true);

    await fireEvent.input(screen.getByTestId('admin-delete-confirm-input'), {
      target: { value: 'jane@example.com' },
    });
    await waitFor(() => expect(confirmBtn.disabled).toBe(false));

    await fireEvent.click(confirmBtn);
    await waitFor(() => expect(deleteAdminUserMock).toHaveBeenCalledWith('user-2'));
  });

  it('turns a 403 from the list into the forbidden state', async () => {
    fetchAdminUsersMock.mockRejectedValue(new ApiError(403, 'forbidden', '/admin/users'));
    render(Page);
    expect(await screen.findByTestId('admin-forbidden')).toBeTruthy();
  });
});
