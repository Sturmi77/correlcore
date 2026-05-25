import { fireEvent, render, screen } from '@testing-library/svelte';
import { describe, expect, it, vi } from 'vitest';
import TabBar from './TabBar.svelte';

describe('TabBar', () => {
  const options = [
    { id: 'mood', label: 'Mood', testId: 'tab-mood' },
    { id: 'activities', label: 'Activities', testId: 'tab-activities' },
  ];

  it('renders tabs with the selected state', () => {
    render(TabBar, {
      props: {
        value: 'mood',
        options,
        ariaLabel: 'Trend sections',
      },
    });

    expect(screen.getByRole('tablist', { name: 'Trend sections' })).toBeTruthy();
    expect(screen.getByTestId('tab-mood').getAttribute('aria-selected')).toBe('true');
    expect(screen.getByTestId('tab-activities').getAttribute('aria-selected')).toBe('false');
  });

  it('dispatches change for a new tab', async () => {
    const onChange = vi.fn();
    render(TabBar, {
      props: {
        value: 'mood',
        options,
        ariaLabel: 'Trend sections',
      },
      events: { change: onChange },
    });

    await fireEvent.click(screen.getByTestId('tab-activities'));

    expect(onChange).toHaveBeenCalledOnce();
    expect(onChange.mock.calls[0][0].detail).toEqual({ value: 'activities' });
  });
});
