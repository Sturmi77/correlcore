import { describe, expect, it } from 'vitest';
import { load as loadOnboarding } from './+page.server';
import { load as loadRetro } from './retro/+page.server';
import { load as loadProfile } from './profile/+page.server';

async function expectRedirect(load: () => unknown, location: string): Promise<void> {
  try {
    await load();
    expect.unreachable('expected redirect');
  } catch (error) {
    expect(error).toEqual(expect.objectContaining({ status: 307, location }));
  }
}

describe('onboarding redirects', () => {
  it('renders the onboarding sequence instead of redirecting', async () => {
    const result = await loadOnboarding({
      url: new URL('http://localhost/onboarding'),
    } as never);
    expect(result).toEqual({});
  });

  it('redirects /onboarding/retro to the guided wizard', async () => {
    await expectRedirect(() => loadRetro({} as never), '/onboarding');
  });

  it('redirects /onboarding/profile to the guided wizard', async () => {
    await expectRedirect(() => loadProfile({} as never), '/onboarding');
  });
});
