import type { PageServerLoad } from './$types';

/** Guided onboarding sequence — shown before the first daily entry. Auth is
 *  client-side, so gating (already-onboarded → home) happens in the page's
 *  onMount, not here. The route renders unconditionally for authenticated
 *  cold-start users; Home redirects incomplete onboardings in. */
export const load: PageServerLoad = () => {
  return {};
};
