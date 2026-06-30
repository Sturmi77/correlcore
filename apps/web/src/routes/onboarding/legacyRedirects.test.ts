import { describe, expect, it } from 'vitest';
import { load as loadRetro } from './retro/+page.server';
import { load as loadProfile } from './profile/+page.server';

async function expectOnboardingRedirect(load: () => Promise<unknown>): Promise<void> {
  try {
    await load();
    expect.unreachable('expected redirect');
  } catch (error) {
    expect(error).toEqual(expect.objectContaining({ status: 307, location: '/onboarding' }));
  }
}

describe('legacy onboarding redirects', () => {
  it('redirects /onboarding/retro to the guided wizard', async () => {
    await expectOnboardingRedirect(() => loadRetro({} as never));
  });

  it('redirects /onboarding/profile to the guided wizard', async () => {
    await expectOnboardingRedirect(() => loadProfile({} as never));
  });
});
