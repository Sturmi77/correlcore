import { fireEvent, render, screen } from '@testing-library/svelte';
import { describe, expect, it, vi } from 'vitest';
import SegmentedControl from './SegmentedControl.svelte';

describe('SegmentedControl', () => {
  const options = [
    { id: 'week', label: '7D', testId: 'range-week' },
    { id: 'month', label: '30D', testId: 'range-month' },
  ];

  it('renders options as one accessible grouped control', () => {
    render(SegmentedControl, {
      props: {
        value: 'week',
        options,
        ariaLabel: 'Time range',
        testId: 'range-control',
      },
    });

    expect(screen.getByRole('group', { name: 'Time range' })).toBeTruthy();
    expect(screen.getByTestId('range-week').getAttribute('aria-pressed')).toBe('true');
    expect(screen.getByTestId('range-month').getAttribute('aria-pressed')).toBe('false');
  });

  it('dispatches change only when a different option is selected', async () => {
    const onChange = vi.fn();
    render(SegmentedControl, {
      props: {
        value: 'week',
        options,
        ariaLabel: 'Time range',
      },
      events: { change: onChange },
    });

    await fireEvent.click(screen.getByTestId('range-week'));
    expect(onChange).not.toHaveBeenCalled();

    await fireEvent.click(screen.getByTestId('range-month'));
    expect(onChange).toHaveBeenCalledOnce();
    expect(onChange.mock.calls[0][0].detail).toEqual({ value: 'month' });
  });
});
