import { render, screen, fireEvent } from '@testing-library/svelte';
import { describe, expect, it, vi } from 'vitest';
import OptionalScaleSlider from './OptionalScaleSlider.svelte';

vi.mock('svelte-i18n', async () => {
  const { readable } = await import('svelte/store');
  return { _: readable((key: string) => key) };
});

const baseProps = {
  id: 'entry-sleep-quality',
  label: 'Sleep quality',
  addLabel: 'Rate sleep quality',
  clearLabel: 'Clear',
  decrementLabel: 'Decrease',
  incrementLabel: 'Increase',
  scaleType: 'sleep' as const,
  testId: 'entry-sleep-quality',
};

describe('OptionalScaleSlider (#653 B6)', () => {
  it('starts unset: shows the add affordance, no slider', () => {
    render(OptionalScaleSlider, { props: { ...baseProps, value: null } });
    expect(screen.getByText('Rate sleep quality')).toBeTruthy();
    expect(screen.queryByRole('slider')).toBeNull();
  });

  it('does not fabricate a rating until activated, then defaults to 3', async () => {
    render(OptionalScaleSlider, { props: { ...baseProps, value: null } });
    await fireEvent.click(screen.getByTestId('entry-sleep-quality'));
    const slider = screen.getByRole('slider') as HTMLInputElement;
    expect(slider.value).toBe('3');
  });

  it('renders a slider (not an add button) when a value is already set', () => {
    render(OptionalScaleSlider, { props: { ...baseProps, value: 4 } });
    const slider = screen.getByRole('slider') as HTMLInputElement;
    expect(slider.value).toBe('4');
    expect(screen.queryByText('Rate sleep quality')).toBeNull();
  });

  it('clear returns to the unset state (add affordance reappears)', async () => {
    render(OptionalScaleSlider, { props: { ...baseProps, value: 4 } });
    await fireEvent.click(screen.getByText('Clear'));
    expect(screen.queryByRole('slider')).toBeNull();
    expect(screen.getByText('Rate sleep quality')).toBeTruthy();
  });
});
