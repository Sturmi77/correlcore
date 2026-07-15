import { describe, expect, it } from 'vitest';
import {
  HEALTH_CONNECT_CONSENT_TYPE,
  type ConsentListResponse,
} from '$lib/api/consents';
import {
  canUseHealthConnectImport,
  getHealthConnectConsentStatus,
} from '$lib/healthConnect/consent';

function makeConsents(granted: boolean): ConsentListResponse {
  return {
    current: [
      {
        consent_type: HEALTH_CONNECT_CONSENT_TYPE,
        consent_version: '1',
        granted,
        updated_at: '2026-07-15T12:00:00Z',
      },
    ],
    history: [],
  };
}

describe('healthConnect consent gate', () => {
  it('returns false when consent data is missing', () => {
    expect(canUseHealthConnectImport(null)).toBe(false);
    expect(canUseHealthConnectImport({ current: [], history: [] })).toBe(false);
  });

  it('returns false when consent was never granted', () => {
    expect(canUseHealthConnectImport(makeConsents(false))).toBe(false);
  });

  it('returns true only after explicit grant', () => {
    expect(canUseHealthConnectImport(makeConsents(true))).toBe(true);
  });

  it('exposes the latest Health Connect status', () => {
    const status = getHealthConnectConsentStatus(makeConsents(true));
    expect(status?.consent_type).toBe(HEALTH_CONNECT_CONSENT_TYPE);
    expect(status?.updated_at).toBe('2026-07-15T12:00:00Z');
  });
});
