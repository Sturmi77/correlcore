import { fireEvent, render, screen, waitFor } from '@testing-library/svelte';
import { beforeEach, describe, expect, it, vi } from 'vitest';
import { MAX_TAGS_PER_ENTRY, type TagResponse } from '$lib/api/tags';
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

vi.mock('$lib/stores/tags', async () => {
  const { derived, writable } = await import('svelte/store');
  tagStoreMocks.state = writable<{ status: 'ready'; tags: TagResponse[] }>({
    status: 'ready',
    tags: [],
  });
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
      expect(tagStoreMocks.submitTag).toHaveBeenCalledWith({
        slug: 'deep-work',
        name: 'Deep Work',
        category: 'other',
        icon: null,
        color: null,
      });
      expect(screen.getByText('Deep Work')).toBeTruthy();
    });

    const createdChip = screen.getByRole('button', { name: 'Deep Work' });
    expect(createdChip.getAttribute('aria-pressed')).toBe('true');
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
