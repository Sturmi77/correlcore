import { fireEvent, render, screen } from '@testing-library/svelte';
import { describe, expect, it, vi } from 'vitest';
import Button from './Button.svelte';
import IconButton from './IconButton.svelte';

describe('Button', () => {
  it('renders a touch-target button with the requested variant', () => {
    render(Button, { props: { variant: 'primary', fullWidth: true, 'data-testid': 'action' } });

    const button = screen.getByTestId('action');
    expect(button.tagName).toBe('BUTTON');
    expect(button.classList.contains('ui-button--primary')).toBe(true);
    expect(button.classList.contains('ui-button--full')).toBe(true);
  });

  it('renders links through the same primitive', () => {
    render(Button, { props: { href: '/settings', variant: 'link', 'data-testid': 'link' } });

    const link = screen.getByTestId('link');
    expect(link.tagName).toBe('A');
    expect(link.getAttribute('href')).toBe('/settings');
    expect(link.classList.contains('ui-button--link')).toBe(true);
  });

  it('forwards click events from the native button', async () => {
    const onClick = vi.fn();
    render(Button, { props: { onclick: onClick, 'data-testid': 'clickable' } });

    await fireEvent.click(screen.getByTestId('clickable'));

    expect(onClick).toHaveBeenCalledOnce();
  });
});

describe('IconButton', () => {
  it('requires and renders an accessible icon label', () => {
    render(IconButton, { props: { ariaLabel: 'Close panel', 'data-testid': 'icon-button' } });

    const button = screen.getByTestId('icon-button');
    expect(button.getAttribute('aria-label')).toBe('Close panel');
    expect(button.getAttribute('title')).toBe('Close panel');
    expect(button.classList.contains('ui-button--icon-only')).toBe(true);
  });
});
