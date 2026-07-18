/**
 * Runtime platform helpers for Capacitor vs browser (ADR-0006 / M11 Sprint 3).
 *
 * `VITE_CAPACITOR=1` is injected by `pnpm --filter @correlcore/web build:capacitor`.
 * Browser / Docker builds leave it unset so cookie auth stays the default.
 */

/** True when the bundle was built for the Capacitor Android/iOS shell. */
export function isCapacitorBuild(): boolean {
  const flag = import.meta.env.VITE_CAPACITOR;
  return flag === '1' || flag === 'true';
}

/**
 * Use in-memory Bearer tokens instead of HttpOnly cookies.
 * Alias of {@link isCapacitorBuild} — kept separate for readability at call sites.
 */
export function usesBearerAuth(): boolean {
  return isCapacitorBuild();
}
