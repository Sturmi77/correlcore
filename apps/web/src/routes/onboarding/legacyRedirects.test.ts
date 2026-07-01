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
  it('redirects /onboarding to home with openEntry', async () => {
    await expectRedirect(
      () => loadOnboarding({ url: new URL('http://localhost/onboarding') } as never),
      '/?openEntry=1'
    );
  });

  it('keeps /onboarding?preview=1 for the legacy wizard', async () => {
    const result = await loadOnboarding({
      url: new URL('http://localhost/onboarding?preview=1'),
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
