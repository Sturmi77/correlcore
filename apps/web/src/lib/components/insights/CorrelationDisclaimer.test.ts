import { describe, it, expect, vi } from 'vitest';
import { render, screen, fireEvent } from '@testing-library/svelte';
import CorrelationDisclaimer from './CorrelationDisclaimer.svelte';

const mockI18n = {
  subscribe: (_run: (fn: (key: string) => string) => void) => {
    _run((key) => key);
    return () => {};
  },
};

vi.mock('svelte-i18n', () => ({ _: mockI18n }));

describe('CorrelationDisclaimer', () => {
  it('renders nothing when open=false', () => {
    render(CorrelationDisclaimer, { props: { open: false } });
    expect(screen.queryByTestId('cd-modal')).toBeNull();
  });

  it('renders modal when open=true', () => {
    render(CorrelationDisclaimer, { props: { open: true } });
    expect(screen.getByTestId('cd-modal')).toBeTruthy();
  });

  it('has aria-modal=true', () => {
    render(CorrelationDisclaimer, { props: { open: true } });
    const modal = screen.getByTestId('cd-modal');
    expect(modal.getAttribute('aria-modal')).toBe('true');
  });

  it('renders all 4 content sections', () => {
    render(CorrelationDisclaimer, { props: { open: true } });
    expect(screen.getByTestId('cd-section-1')).toBeTruthy();
    expect(screen.getByTestId('cd-section-2')).toBeTruthy();
    expect(screen.getByTestId('cd-section-3')).toBeTruthy();
    expect(screen.getByTestId('cd-section-4')).toBeTruthy();
  });

  it('dispatches close on close-button click', async () => {
    const { container } = render(CorrelationDisclaimer, { props: { open: true } });
    const handler = vi.fn();
    container.addEventListener('close', handler);
    await fireEvent.click(screen.getByTestId('cd-close'));
    expect(handler).toHaveBeenCalledOnce();
  });

  it('dispatches close on got-it button click', async () => {
    const { container } = render(CorrelationDisclaimer, { props: { open: true } });
    const handler = vi.fn();
    container.addEventListener('close', handler);
    await fireEvent.click(screen.getByTestId('cd-got-it'));
    expect(handler).toHaveBeenCalledOnce();
  });

  it('dispatches close on backdrop click', async () => {
    const { container } = render(CorrelationDisclaimer, { props: { open: true } });
    const handler = vi.fn();
    container.addEventListener('close', handler);
    await fireEvent.click(screen.getByTestId('cd-backdrop'));
    expect(handler).toHaveBeenCalledOnce();
  });

  it('dispatches close on Escape key', async () => {
    const { container } = render(CorrelationDisclaimer, { props: { open: true } });
    const handler = vi.fn();
    container.addEventListener('close', handler);
    await fireEvent.keyDown(document, { key: 'Escape' });
    expect(handler).toHaveBeenCalledOnce();
  });
});
