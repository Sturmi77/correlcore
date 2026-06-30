import { redirect } from '@sveltejs/kit';
import type { PageServerLoad } from './$types';

/** Legacy M3 retro flow — ADR-0030 wizard replaces this route. */
export const load: PageServerLoad = () => {
  throw redirect(307, '/onboarding');
};
