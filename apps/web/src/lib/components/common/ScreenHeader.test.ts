import { render, screen } from '@testing-library/svelte';
import { describe, expect, it } from 'vitest';
import ScreenHeader from './ScreenHeader.svelte';

describe('ScreenHeader', () => {
  it('renders one accessible screen heading and supporting copy', () => {
    render(ScreenHeader, {
      props: {
        title: 'Trends',
        subtitle: 'Long-term visualisations from your entries.',
        eyebrow: 'Analytics',
      },
    });

    expect(screen.getByRole('heading', { level: 1, name: 'Trends' })).toBeTruthy();
    expect(screen.getByText('Long-term visualisations from your entries.')).toBeTruthy();
    expect(screen.getByText('Analytics')).toBeTruthy();
  });

  it('supports compact screen headers', () => {
    render(ScreenHeader, {
      props: {
        title: 'Manage tags',
        compact: true,
      },
    });

    expect(screen.getByRole('banner').classList.contains('screen-header--compact')).toBe(true);
  });

  it('renders a shared back affordance when a back target is given', () => {
    render(ScreenHeader, {
      props: {
        title: 'Developer tools',
        back: { href: '/settings', label: 'Settings' },
      },
    });

    const back = screen.getByTestId('screen-back');
    expect(back.getAttribute('href')).toBe('/settings');
    expect(back.textContent).toContain('Settings');
  });

  it('omits the back affordance by default', () => {
    render(ScreenHeader, { props: { title: 'Trends' } });

    expect(screen.queryByTestId('screen-back')).toBeNull();
  });

  it('marks the header as sticky floating chrome when sticky is set (#703 Stage 2)', () => {
    render(ScreenHeader, { props: { title: 'Trends', sticky: true } });

    expect(screen.getByRole('banner').classList.contains('screen-header--sticky')).toBe(true);
  });

  it('is not sticky by default', () => {
    render(ScreenHeader, { props: { title: 'Trends' } });

    expect(screen.getByRole('banner').classList.contains('screen-header--sticky')).toBe(false);
  });

  it('can hide the header visually while keeping the h1 in the DOM', () => {
    render(ScreenHeader, {
      props: {
        title: 'Today',
        visuallyHidden: true,
      },
    });

    expect(screen.getByRole('heading', { level: 1, name: 'Today' })).toBeTruthy();
    expect(screen.getByRole('banner').classList.contains('screen-header--visually-hidden')).toBe(
      true
    );
  });
});
