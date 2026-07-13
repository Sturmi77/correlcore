import { render, screen } from '@testing-library/svelte';
import { describe, expect, it } from 'vitest';
import BottomSheetHarness from './BottomSheet.harness.svelte';

describe('BottomSheet', () => {
  it('renders sheet content when open', () => {
    render(BottomSheetHarness);

    const sheet = screen.getByTestId('bottom-sheet');
    expect(sheet.getAttribute('aria-labelledby')).toBe('sheet-title');
    expect(sheet.textContent).toContain('Sheet title');
  });
});
