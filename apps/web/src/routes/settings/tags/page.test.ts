import { fireEvent, render, screen, waitFor } from '@testing-library/svelte';
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
    createTag: vi.fn(),
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
    habit_type: 'none',
    target_frequency: null,
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

  it('saves habit configuration with the tag update', async () => {
    const tag = makeTag({ id: 'habit-tag', name: 'Walk' });
    vi.mocked(tagsApi.listVisibleTags).mockResolvedValue([tag]);
    vi.mocked(tagsApi.updateTag).mockResolvedValue({
      ...tag,
      habit_type: 'build',
      target_frequency: 4,
    });

    render(Page);

    const row = (await screen.findByText('Walk')).closest('article');
    const selects = row?.querySelectorAll('select');
    const habitSelect = selects?.[1] as HTMLSelectElement;
    habitSelect.value = 'build';
    await fireEvent.change(habitSelect);

    const targetInput = row?.querySelector('input[type="number"]') as HTMLInputElement;
    targetInput.value = '4';
    await fireEvent.input(targetInput);

    await fireEvent.click(screen.getByText('settings.tags.save'));

    await waitFor(() => {
      expect(tagsApi.updateTag).toHaveBeenCalledWith(
        'habit-tag',
        expect.objectContaining({ habit_type: 'build', target_frequency: 4 })
      );
    });
  });

  it('creates a new custom tag from the create form', async () => {
    vi.mocked(tagsApi.listVisibleTags).mockResolvedValue([]);
    const created = makeTag({ id: 'new-tag', name: 'Meditation', slug: 'meditation' });
    vi.mocked(tagsApi.createTag).mockResolvedValue(created);
    vi.mocked(tagsApi.listVisibleTags).mockResolvedValueOnce([]).mockResolvedValueOnce([created]);

    render(Page);

    const createSection = await screen.findByTestId('tag-settings-create');
    const nameInput = createSection.querySelectorAll('input.input')[0] as HTMLInputElement;
    expect(nameInput).toBeTruthy();
    nameInput.value = 'Meditation';
    await fireEvent.input(nameInput);
    await fireEvent.click(screen.getByText('settings.tags.create_submit'));

    await waitFor(() => {
      expect(tagsApi.createTag).toHaveBeenCalledWith(
        expect.objectContaining({
          name: 'Meditation',
          slug: 'meditation',
          category: 'other',
        })
      );
    });
  });
});
