import { api } from './client';

export const HEALTH_CONNECT_CONSENT_TYPE = 'health_connect';
export const HEALTH_CONNECT_CONSENT_VERSION = '1';

export interface ConsentRecordResponse {
  id: string;
  consent_type: string;
  consent_version: string;
  granted: boolean;
  created_at: string;
}

export interface ConsentStatusItem {
  consent_type: string;
  consent_version: string | null;
  granted: boolean;
  updated_at: string | null;
}

export interface ConsentListResponse {
  current: ConsentStatusItem[];
  history: ConsentRecordResponse[];
}

export interface ConsentRecordRequest {
  type: string;
  version: string;
  granted: boolean;
}

export async function fetchUserConsents(): Promise<ConsentListResponse> {
  return api.get<ConsentListResponse>('/user/me/consents');
}

export async function recordUserConsent(payload: ConsentRecordRequest): Promise<ConsentRecordResponse> {
  return api.post<ConsentRecordResponse>('/user/me/consents', payload);
}

export async function revokeUserConsent(type: string): Promise<ConsentRecordResponse> {
  return api.post<ConsentRecordResponse>('/user/me/consents/revoke', { type });
}
