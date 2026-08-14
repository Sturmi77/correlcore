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

  describe('expandedByDefault (#673)', () => {
    const expandedProps = {
      ...baseProps,
      expandedByDefault: true,
      unsetHint: 'Optional – tap to record.',
    };

    it('shows the slider up front while unset, with the not-recorded readout and hint', () => {
      render(OptionalScaleSlider, { props: { ...expandedProps, value: null } });
      // Slider is visible instead of the add button.
      const slider = screen.getByRole('slider') as HTMLInputElement;
      expect(slider.value).toBe('3'); // sits at the default position…
      expect(screen.queryByText('Rate sleep quality')).toBeNull();
      // …but reads as not recorded and shows the hint.
      expect(screen.getByText('–')).toBeTruthy();
      expect(screen.getByText('Optional – tap to record.')).toBeTruthy();
      // Nothing to clear while unset.
      expect(screen.queryByText('Clear')).toBeNull();
    });

    it('records a real value on first interaction (increment from unset)', async () => {
      render(OptionalScaleSlider, { props: { ...expandedProps, value: null } });
      // Unset → not-recorded readout, no clear control yet.
      expect(screen.getByText('–')).toBeTruthy();
      expect(screen.queryByText('Clear')).toBeNull();

      await fireEvent.click(screen.getByLabelText('Increase'));

      const slider = screen.getByRole('slider') as HTMLInputElement;
      expect(slider.value).toBe('4'); // 3 (default position) + 1 → now recorded
      // A recorded value shows the numeric readout and the clear control.
      expect(screen.getByText('4')).toBeTruthy();
      expect(screen.getByText('Clear')).toBeTruthy();
    });

    it('clearing a set value keeps the slider visible (stays expanded, not the add button)', async () => {
      render(OptionalScaleSlider, { props: { ...expandedProps, value: 4 } });
      await fireEvent.click(screen.getByText('Clear'));
      // Still a slider (not the collapsed add button), back to the unset readout.
      expect(screen.getByRole('slider')).toBeTruthy();
      expect(screen.queryByText('Rate sleep quality')).toBeNull();
      expect(screen.getByText('–')).toBeTruthy();
    });
  });
});
