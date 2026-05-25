import { describe, expect, it } from 'vitest';
import { render, screen } from '@testing-library/svelte';
import Panel from './Panel.svelte';

describe('Panel', () => {
  it('renders as the requested element with the variant class', () => {
    render(Panel, {
      props: {
        as: 'article',
        variant: 'chart',
        'data-testid': 'chart-panel',
      },
    });

    const panel = screen.getByTestId('chart-panel');
    expect(panel.tagName).toBe('ARTICLE');
    expect(panel.className).toContain('ui-panel--chart');
  });
});
