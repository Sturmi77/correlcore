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

const { deleteCycleDataMock, downloadExportMock, saveBlobMock } = vi.hoisted(() => ({
  deleteCycleDataMock: vi.fn(async () => ({ cleared_entries: 3 })),
  downloadExportMock: vi.fn(async () => new Blob(['x'])),
  saveBlobMock: vi.fn(),
}));

vi.mock('$lib/api/entries', () => ({ deleteCycleData: deleteCycleDataMock }));
vi.mock('$lib/stores/entriesOffline', () => ({ clearCycleDataOffline: vi.fn(async () => 0) }));
vi.mock('$lib/api/export', () => ({
  downloadExport: downloadExportMock,
  exportFilename: (kind: string) => `export.${kind}`,
  saveBlob: saveBlobMock,
}));
vi.mock('$lib/api/preferences', () => ({
  fetchUserPreferences: vi.fn(async () => ({ cycle_tracking_enabled: true })),
  updateUserPreferences: vi.fn(async (p: { cycle_tracking_enabled?: boolean }) => ({
    cycle_tracking_enabled: p.cycle_tracking_enabled ?? true,
  })),
}));

describe('/settings/data', () => {
  it('exposes vocabulary links, cycle and export controls', async () => {
    render(Page);
    expect(await screen.findByTestId('settings-vocab-tags')).toBeTruthy();
    expect(screen.getByTestId('settings-vocab-symptoms')).toBeTruthy();
    expect(screen.getByTestId('cycle-toggle')).toBeTruthy();
    expect(screen.getByTestId('cycle-delete-data')).toBeTruthy();
  });

  it('downloads a ZIP export', async () => {
    render(Page);
    await screen.findByTestId('cycle-toggle');
    await fireEvent.click(screen.getByText('settings.export.zip'));
    await waitFor(() => expect(downloadExportMock).toHaveBeenCalledWith('zip'));
    expect(saveBlobMock).toHaveBeenCalled();
  });

  it('confirms cycle-data deletion through the dialog', async () => {
    render(Page);
    await fireEvent.click(await screen.findByTestId('cycle-delete-data'));
    await fireEvent.click(await screen.findByTestId('cycle-delete-confirm'));
    await waitFor(() => expect(deleteCycleDataMock).toHaveBeenCalled());
  });
});
