/**
 * Health Connect import gate — requires explicit DSGVO Art. 9 consent (Issue #31).
 */

import {
  HEALTH_CONNECT_CONSENT_TYPE,
  type ConsentListResponse,
  type ConsentStatusItem,
} from '$lib/api/consents';

/** Return the latest Health Connect consent state, if any. */
export function getHealthConnectConsentStatus(
  consents: ConsentListResponse | null | undefined
): ConsentStatusItem | null {
  if (!consents?.current?.length) return null;
  return consents.current.find((item) => item.consent_type === HEALTH_CONNECT_CONSENT_TYPE) ?? null;
}

/**
 * Gate for M8/M11 Health Connect import paths.
 * Returns false until the user has granted consent on the server.
 */
export function canUseHealthConnectImport(
  consents: ConsentListResponse | null | undefined
): boolean {
  const status = getHealthConnectConsentStatus(consents);
  return status?.granted === true;
}
