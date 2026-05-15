import { render, screen } from '@testing-library/svelte';
import { readable } from 'svelte/store';
import { describe, expect, it, vi } from 'vitest';
import ScaleSlider from './ScaleSlider.svelte';

vi.mock('svelte-i18n', () => ({
  _: readable((key: string) => key),
}));

describe('ScaleSlider', () => {
  it('shows stress legend keys for relaxed vs very stressed', () => {
    render(ScaleSlider, {
      props: {
        id: 'test-stress',
        label: 'Stress',
        decrementLabel: 'Less',
        incrementLabel: 'More',
        scaleType: 'stress',
        value: 3,
      },
    });

    expect(screen.getByText(/entry\.scale\.stress_low/)).toBeTruthy();
    expect(screen.getByText(/entry\.scale\.stress_high/)).toBeTruthy();
    const slider = screen.getByRole('slider', { name: 'Stress' });
    expect(slider.getAttribute('aria-describedby')).toBe('test-stress-legend');
  });
});
