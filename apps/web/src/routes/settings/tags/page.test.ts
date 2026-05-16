import { render, screen, waitFor } from '@testing-library/svelte';
import { describe, expect, it, vi, beforeEach } from 'vitest';
import Page from './+page.svelte';
import type { TagResponse } from '$lib/api/tags';

vi.mock('svelte-i18n', async () => {
  const { readable } = await import('svelte/store');
  return {
    _: readable((key: string) => key),
  };
});

vi.mock('$lib/stores/auth', async () => {
  const { readable } = await import('svelte/store');
  return {
    auth: readable({
      status: 'authenticated',
      user: { id: 'user-1', email: 'user@example.com' },
    }),
  };
});

vi.mock('$lib/api/tags', async () => {
  const actual = await vi.importActual<typeof import('$lib/api/tags')>('$lib/api/tags');
  return {
    ...actual,
    listDefaultTags: vi.fn(),
    listVisibleTags: vi.fn(),
    updateTag: vi.fn(),
    deleteTag: vi.fn(),
  };
});

vi.mock('$lib/stores/tags', () => ({
  refreshTags: vi.fn(),
}));

import * as tagsApi from '$lib/api/tags';

function makeTag(overrides: Partial<TagResponse> = {}): TagResponse {
  return {
    id: 'tag-' + Math.random().toString(36).slice(2, 8),
    user_id: 'user-1',
    slug: 'sample',
    name: 'Sample',
    category: 'other',
    icon: null,
    color: '#01696f',
    is_default: false,
    is_hidden: false,
    created_at: '2026-05-16T10:00:00Z',
    updated_at: '2026-05-16T10:00:00Z',
    ...overrides,
  };
}

describe('/settings/tags Sprint 8', () => {
  beforeEach(() => {
    vi.clearAllMocks();
    vi.mocked(tagsApi.listDefaultTags).mockResolvedValue([]);
  });

  it('renders active and inactive tag groups', async () => {
    vi.mocked(tagsApi.listVisibleTags).mockResolvedValue([
      makeTag({ id: 'active', name: 'Active Tag' }),
      makeTag({ id: 'inactive', name: 'Inactive Tag', is_hidden: true }),
    ]);

    render(Page);

    expect(await screen.findByTestId('tag-settings-active')).toBeTruthy();
    expect(screen.getByTestId('tag-settings-inactive')).toBeTruthy();
    expect(screen.getByText('Active Tag')).toBeTruthy();
    expect(screen.getByText('Inactive Tag')).toBeTruthy();
  });

  it('loads tags with include_hidden so inactive tags can be reactivated', async () => {
    vi.mocked(tagsApi.listVisibleTags).mockResolvedValue([]);

    render(Page);

    await waitFor(() => {
      expect(tagsApi.listVisibleTags).toHaveBeenCalledWith({ include_hidden: true });
    });
  });
});
