import { redirect } from '@sveltejs/kit';
import type { PageServerLoad } from './$types';

/** Guided wizard is preview-only; new users tag-select inline in the first entry sheet.
 *  Redirect to `/` without `?openEntry=1` so PWA/homescreen restores of `/onboarding`
 *  do not race the standalone launch normalizer and re-open the entry sheet. Home still
 *  auto-opens the first-entry sheet for incomplete onboarding. */
export const load: PageServerLoad = ({ url }) => {
  if (url.searchParams.get('preview') === '1') {
    return {};
  }
  throw redirect(307, '/');
};
