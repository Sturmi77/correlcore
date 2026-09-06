import { render, screen } from '@testing-library/svelte';
import { describe, expect, it, vi } from 'vitest';
import ScreenHeader from './ScreenHeader.svelte';

// ScreenHeader formats the back link's aria-label via $_. Mock svelte-i18n with
// a formatter that echoes the key plus interpolated values so the a11y test can
// assert the destination is present (real localisation lives in the locale JSON).
vi.mock('svelte-i18n', async () => {
  const { readable } = await import('svelte/store');
  const format = (key: string, opts?: { values?: Record<string, unknown> }): string => {
    const values = opts?.values;
    return values ? `${key} ${Object.values(values).join(' ')}` : key;
  };
  return {
    _: {
      subscribe: (run: (formatter: typeof format) => void) => {
        run(format);
        return () => undefined;
      },
    },
    locale: readable('en'),
  };
});

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
    // a11y: screen readers get an explicit "Back to …" name, not a bare label
    // that reads like the nav link. The arrow glyph is aria-hidden.
    expect(back.getAttribute('aria-label')).toContain('Settings');
    expect(back.getAttribute('aria-label')).not.toBe('Settings');
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

  it('keeps sticky density tokens available for scrolled controls (#786)', () => {
    render(ScreenHeader, { props: { title: 'Trends', sticky: true, subtitle: 'Charts' } });
    const header = screen.getByRole('banner');
    expect(header.classList.contains('screen-header--sticky')).toBe(true);
    // Density CSS keys off screen-header--scrolled (set by the scroll listener).
    header.classList.add('screen-header--scrolled');
    expect(header.classList.contains('screen-header--scrolled')).toBe(true);
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
