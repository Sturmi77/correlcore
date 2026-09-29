/** Keep post-auth navigation on this origin and out of the auth flow. */
export function safeInternalReturnPath(raw: string | null, fallback = '/'): string {
  if (!raw || [...raw].some((char) => char === '\\' || char.charCodeAt(0) <= 0x1f)) {
    return fallback;
  }
  if (!raw.startsWith('/') || raw.startsWith('//')) return fallback;
  try {
    const parsed = new URL(raw, 'https://correlcore.invalid');
    if (parsed.origin !== 'https://correlcore.invalid') return fallback;
    if (parsed.pathname.startsWith('/auth/')) return fallback;
    return `${parsed.pathname}${parsed.search}${parsed.hash}`;
  } catch {
    return fallback;
  }
}
