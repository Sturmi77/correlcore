import { fireEvent, render, screen, waitFor } from '@testing-library/svelte';
import { beforeEach, describe, expect, it, vi } from 'vitest';
import { MAX_TAGS_PER_ENTRY, type TagResponse } from '$lib/api/tags';
import { categoryColorForCurrentTheme } from '$lib/constants/tagDefaults';
import TagPicker from './TagPicker.svelte';

vi.mock('svelte-i18n', () => ({
  _: {
    subscribe: (run: (formatter: (key: string) => string) => void) => {
      run((key: string) => key);
      return () => undefined;
    },
  },
}));

const tagStoreMocks = vi.hoisted(() => {
  return {
    state: undefined as unknown as {
      set(value: { status: 'ready'; tags: TagResponse[] }): void;
      update(
        updater: (state: { status: 'ready'; tags: TagResponse[] }) => {
          status: 'ready';
          tags: TagResponse[];
        }
      ): void;
      subscribe(run: (value: { status: 'ready'; tags: TagResponse[] }) => void): () => void;
    },
    refreshTags: vi.fn(),
    submitTag: vi.fn(),
  };
});

const statsMocks = vi.hoisted(() => ({ fetchTagHeatmap: vi.fn() }));

vi.mock('$lib/api/stats', () => ({
  fetchTagHeatmap: statsMocks.fetchTagHeatmap,
}));

vi.mock('$lib/stores/tags', async () => {
  const { derived, writable } = await import('svelte/store');
  tagStoreMocks.state = writable<{ status: 'ready'; tags: TagResponse[] }>({
    status: 'ready',
    tags: [],
  });
  const tagsList = derived(tagStoreMocks.state, ($s) => ($s.status === 'ready' ? $s.tags : []));
  const tagsByCategory = derived(tagStoreMocks.state, ($s) => {
    const grouped = {
      sport: [],
      social: [],
      work: [],
      leisure: [],
      consumption: [],
      health: [],
      cycle: [],
      other: [],
    } as Record<string, TagResponse[]>;
    for (const tag of $s.tags) {
      if (!tag.is_hidden) grouped[tag.category].push(tag);
    }
    return grouped;
  });

  return {
    tags: { subscribe: tagStoreMocks.state.subscribe },
    tagsList,
    tagsByCategory,
    refreshTags: tagStoreMocks.refreshTags,
    submitTag: tagStoreMocks.submitTag,
  };
});

function tag(overrides: Partial<TagResponse> = {}): TagResponse {
  return {
    id: 'tag-1',
    user_id: 'user-1',
    slug: 'focus',
    name: 'Focus',
    category: 'work',
    icon: null,
    color: null,
    is_default: false,
    is_hidden: false,
    include_in_analytics: true,
    habit_type: 'none',
    target_frequency: null,
    created_at: '2026-05-01T00:00:00Z',
    updated_at: '2026-05-01T00:00:00Z',
    ...overrides,
  };
}

describe('TagPicker', () => {
  beforeEach(() => {
    tagStoreMocks.state.set({ status: 'ready', tags: [tag()] });
    tagStoreMocks.refreshTags.mockReset();
    tagStoreMocks.submitTag.mockReset();
    statsMocks.fetchTagHeatmap.mockReset();
    // Default: no recent usage, so the full catalogue renders directly.
    statsMocks.fetchTagHeatmap.mockResolvedValue({ start_date: '', end_date: '', tags: [] });
  });

  it('renders a curated category icon in the visible category header (#672)', () => {
    render(TagPicker, { props: { selected: [] } });
    // The default tag is in the "work" category, so that header is visible.
    const heading = screen.getByText('tag.category.work').closest('h3');
    expect(heading).not.toBeNull();
    // Category-level iconography is a statically-imported Lucide SVG.
    expect(heading?.querySelector('svg')).toBeTruthy();
  });

  it('does not render a per-tag icon glyph inside the chip (#672)', () => {
    tagStoreMocks.state.set({
      status: 'ready',
      tags: [tag({ id: 'iconned', name: 'Iconned', category: 'work', icon: 'dumbbell' })],
    });
    render(TagPicker, { props: { selected: [] } });
    const chip = screen.getByRole('button', { name: 'Iconned' });
    // The chip is now name + colour only — no decorative per-item icon.
    expect(chip.querySelector('svg')).toBeNull();
  });

  it('creates a custom tag inline and selects it', async () => {
    const created = tag({
      id: 'tag-new',
      slug: 'deep-work',
      name: 'Deep Work',
      category: 'work',
    });
    tagStoreMocks.submitTag.mockImplementation(async () => {
      tagStoreMocks.state.update((state) => ({ status: 'ready', tags: [...state.tags, created] }));
      return created;
    });

    render(TagPicker, { props: { selected: [] } });

    await fireEvent.click(screen.getByText('+ tag.custom.add_button'));
    await fireEvent.input(screen.getByPlaceholderText('tag.custom.name_placeholder'), {
      target: { value: 'Deep Work' },
    });
    await fireEvent.click(screen.getByText('tag.custom.save'));

    await waitFor(() => {
      // No icon field any more (#672); colour defaults to the group colour.
      expect(tagStoreMocks.submitTag).toHaveBeenCalledWith({
        slug: 'deep-work',
        name: 'Deep Work',
        category: 'other',
        color: categoryColorForCurrentTheme('other'),
      });
      expect(screen.getByText('Deep Work')).toBeTruthy();
    });

    const createdChip = screen.getByRole('button', { name: 'Deep Work' });
    expect(createdChip.getAttribute('aria-pressed')).toBe('true');
  });

  it('offers no icon field and suggests the group colour on category change', async () => {
    tagStoreMocks.submitTag.mockImplementation(async () => {
      const created = tag({ id: 'tag-run', slug: 'running', name: 'Running', category: 'sport' });
      tagStoreMocks.state.update((state) => ({ status: 'ready', tags: [...state.tags, created] }));
      return created;
    });

    render(TagPicker, { props: { selected: [] } });
    await fireEvent.click(screen.getByText('+ tag.custom.add_button'));

    // The icon field is gone.
    expect(screen.queryByText('tag.custom.icon_label')).toBeNull();

    await fireEvent.input(screen.getByPlaceholderText('tag.custom.name_placeholder'), {
      target: { value: 'Running' },
    });
    // Switching the category re-suggests that group's colour.
    const category = screen
      .getByText('tag.custom.category_label')
      .parentElement?.querySelector('select') as HTMLSelectElement;
    await fireEvent.change(category, { target: { value: 'sport' } });
    await fireEvent.click(screen.getByText('tag.custom.save'));

    await waitFor(() => {
      expect(tagStoreMocks.submitTag).toHaveBeenCalledWith({
        slug: 'running',
        name: 'Running',
        category: 'sport',
        color: categoryColorForCurrentTheme('sport'),
      });
    });
  });

  it('shows a "recently used" row first and keeps the full catalogue behind a disclosure', async () => {
    tagStoreMocks.state.set({
      status: 'ready',
      tags: [
        tag({ id: 'focus-id', slug: 'focus', name: 'Focus', category: 'work' }),
        tag({ id: 'sport-id', slug: 'sport', name: 'Sport', category: 'sport' }),
      ],
    });
    statsMocks.fetchTagHeatmap.mockResolvedValue({
      start_date: '2026-05-01',
      end_date: '2026-05-14',
      tags: [
        {
          tag_id: 'sport-id',
          slug: 'sport',
          name: 'Sport',
          category: 'sport',
          color: null,
          days: [{ date: '2026-05-13', count: 3 }],
        },
      ],
    });

    render(TagPicker, { props: { selected: [] } });

    // The recency row appears once the heatmap resolves; the catalogue is hidden.
    await waitFor(() => {
      expect(screen.getByTestId('tag-recent')).toBeTruthy();
    });
    expect(screen.getByTestId('tag-recent').querySelector('button')?.textContent).toContain(
      'Sport'
    );
    expect(screen.queryByTestId('tag-all')).toBeNull();

    // "All tags" disclosure reveals the categorised catalogue on demand.
    await fireEvent.click(screen.getByTestId('tag-all-toggle'));
    expect(screen.getByTestId('tag-all')).toBeTruthy();
    expect(screen.getByText('tag.category.work')).toBeTruthy();
  });

  it('falls back to the full catalogue when the recency source fails', async () => {
    statsMocks.fetchTagHeatmap.mockRejectedValue(new Error('offline'));
    render(TagPicker, { props: { selected: [] } });

    // No recency row, but tagging still works: the catalogue renders directly.
    await waitFor(() => {
      expect(screen.getByRole('button', { name: 'Focus' })).toBeTruthy();
    });
    expect(screen.queryByTestId('tag-recent')).toBeNull();
    expect(screen.queryByTestId('tag-all-toggle')).toBeNull();
  });

  it('keeps the catalogue visible with a selection when recency is empty (#902 review)', async () => {
    // Empty recency + a pre-selected tag (edit flow / heatmap failure with a
    // selection) must NOT collapse the catalogue: the disclosure is gated on
    // real recency data, not on selected-tag padding.
    statsMocks.fetchTagHeatmap.mockResolvedValue({ start_date: '', end_date: '', tags: [] });
    render(TagPicker, { props: { selected: ['tag-1'] } });

    await waitFor(() => {
      expect(screen.getByTestId('tag-all')).toBeTruthy();
    });
    expect(screen.queryByTestId('tag-recent')).toBeNull();
    expect(screen.queryByTestId('tag-all-toggle')).toBeNull();
    // The selected tag stays visible (and pressed) in the catalogue.
    expect(screen.getByRole('button', { name: 'Focus' }).getAttribute('aria-pressed')).toBe('true');
  });

  it('explains the selection limit and blocks new choices', () => {
    const selected = Array.from({ length: MAX_TAGS_PER_ENTRY }, (_, index) => `selected-${index}`);
    render(TagPicker, { props: { selected } });

    expect(screen.getByTestId('tag-limit-message').textContent).toContain('tag.limit_reached');
    expect(screen.getByRole('button', { name: 'Focus' }).hasAttribute('disabled')).toBe(true);
    expect(
      screen.getByText('+ tag.custom.add_button').closest('button')?.hasAttribute('disabled')
    ).toBe(true);
  });
});
