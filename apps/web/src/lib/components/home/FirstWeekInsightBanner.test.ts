import { fireEvent, render, screen } from '@testing-library/svelte';
import { describe, expect, it, vi } from 'vitest';
import FirstWeekInsightBanner from './FirstWeekInsightBanner.svelte';

vi.mock('svelte-i18n', async () => {
  const { readable } = await import('svelte/store');

  return {
    _: readable((key: string) => key),
  };
});

describe('FirstWeekInsightBanner', () => {
  it('renders neutral copy and dispatches dismiss', async () => {
    const onDismiss = vi.fn();
    render(FirstWeekInsightBanner, { events: { dismiss: onDismiss } });

    expect(screen.getByText('home.first_week_banner.title')).toBeTruthy();
    expect(screen.queryByText('home.first_week_banner.view')).toBeNull();

    await fireEvent.click(screen.getByLabelText('home.first_week_banner.dismiss'));
    expect(onDismiss).toHaveBeenCalledTimes(1);
  });
});
