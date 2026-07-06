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

  it('uses context copy and statement for work-context insights', () => {
    render(FirstWeekInsightBanner, {
      props: {
        insight: {
          insight_type: 'work_context_pattern',
          statement: 'Office days are currently above your average.',
        } as never,
      },
    });

    expect(screen.getByText('home.context_banner.title')).toBeTruthy();
    expect(screen.getByText('Office days are currently above your average.')).toBeTruthy();
  });
});
