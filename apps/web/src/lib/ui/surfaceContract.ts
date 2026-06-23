export const DESKTOP_SHELL_BREAKPOINT_PX = 768;

export const BASELINE_VIEWPORTS = {
  mobile: { width: 390, height: 844 },
  mobileLarge: { width: 430, height: 932 },
  tablet: { width: 768, height: 1024 },
  desktop: { width: 1280, height: 900 },
  desktopWide: { width: 1440, height: 900 },
} as const;

export type SurfaceRole = 'mobile-daily' | 'web-analysis';

export function surfaceRoleForWidth(width: number): SurfaceRole {
  return width < DESKTOP_SHELL_BREAKPOINT_PX ? 'mobile-daily' : 'web-analysis';
}

export const UI_DATA_STATES = ['loading', 'error', 'empty', 'offline', 'partial', 'ready'] as const;

export type UiDataStateKind = (typeof UI_DATA_STATES)[number];

export const PRIMARY_SURFACES = [
  { id: 'home', route: '/', navigation: true, mobile: 'daily-brief', web: 'dashboard' },
  {
    id: 'entry',
    route: '/entries/new',
    navigation: false,
    mobile: 'capture-flow',
    web: 'entry-workspace',
  },
  {
    id: 'insights',
    route: '/insights',
    navigation: true,
    mobile: 'prioritised-feed',
    web: 'analysis-feed',
  },
  {
    id: 'trends',
    route: '/trends',
    navigation: true,
    mobile: 'summary-and-drilldown',
    web: 'analysis-canvas',
  },
  {
    id: 'settings',
    route: '/settings',
    navigation: true,
    mobile: 'essential-controls',
    web: 'management-workspace',
  },
] as const;
