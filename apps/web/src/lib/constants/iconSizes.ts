/**
 * Icon size scale (ISP-9) — pixel-number mirror of the --icon-sm/-md CSS
 * tokens in app.css, for @lucide/svelte's `size` prop (a plain number, not
 * something a CSS custom property can feed directly).
 *
 * Values are the dominant size found in each real usage cluster
 * (14/16px -> sm, 18/20/22px -> md), not arbitrary round numbers. Only two
 * tiers are defined because only two clusters exist in real UI-icon usage.
 *
 * Brand-mark sizes (CorrelCoreLogo) are a separate scale — not Lucide icons.
 */
export const ICON_SIZE_SM = 14;
export const ICON_SIZE_MD = 18;

/** Settings footer mark */
export const BRAND_MARK_SM = 18;
/** Desktop AppNav rail */
export const BRAND_MARK_MD = 24;
/** Auth chrome */
export const BRAND_MARK_LG = 36;
/** Landing header */
export const BRAND_MARK_XL = 40;
/** Landing hero */
export const BRAND_MARK_HERO = 72;
