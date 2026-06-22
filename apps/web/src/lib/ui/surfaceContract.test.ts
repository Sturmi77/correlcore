import { describe, expect, it } from 'vitest';
import {
  BASELINE_VIEWPORTS,
  DESKTOP_SHELL_BREAKPOINT_PX,
  PRIMARY_SURFACES,
  surfaceRoleForWidth,
  UI_DATA_STATES,
} from './surfaceContract';

describe('surface contract', () => {
  it('uses the implemented 768px shell breakpoint', () => {
    expect(surfaceRoleForWidth(DESKTOP_SHELL_BREAKPOINT_PX - 1)).toBe('mobile-daily');
    expect(surfaceRoleForWidth(DESKTOP_SHELL_BREAKPOINT_PX)).toBe('web-analysis');
  });

  it('defines the canonical QA viewport matrix', () => {
    expect(Object.values(BASELINE_VIEWPORTS)).toEqual([
      { width: 390, height: 844 },
      { width: 430, height: 932 },
      { width: 768, height: 1024 },
      { width: 1280, height: 900 },
      { width: 1440, height: 900 },
    ]);
  });

  it('keeps all six async UI states explicit', () => {
    expect(UI_DATA_STATES).toEqual(['loading', 'error', 'empty', 'offline', 'partial', 'ready']);
  });

  it('keeps Entry inside the five-surface contract but outside primary navigation', () => {
    expect(PRIMARY_SURFACES).toHaveLength(5);
    expect(PRIMARY_SURFACES.find((surface) => surface.id === 'entry')).toMatchObject({
      route: '/entries/new',
      navigation: false,
      mobile: 'capture-flow',
      web: 'entry-workspace',
    });
    expect(PRIMARY_SURFACES.filter((surface) => surface.navigation)).toHaveLength(4);
  });
});
