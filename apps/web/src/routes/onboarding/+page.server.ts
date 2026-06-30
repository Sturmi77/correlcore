import { redirect } from '@sveltejs/kit';
import type { PageServerLoad } from './$types';
import { OPEN_ENTRY_HOME_PATH } from '$lib/navigation/openEntry';

/** Guided wizard is preview-only; new users tag-select inline in the first entry sheet. */
export const load: PageServerLoad = ({ url }) => {
  if (url.searchParams.get('preview') === '1') {
    return {};
  }
  throw redirect(307, OPEN_ENTRY_HOME_PATH);
};
