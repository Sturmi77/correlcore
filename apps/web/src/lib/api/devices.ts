/**
 * Device push-token API client (M11 Sprint 5).
 */

import { api } from './client';

export type PushProvider = 'fcm' | 'unifiedpush';
export type PushPlatform = 'android' | 'ios' | 'web';

export interface DeviceTokenResponse {
  id: string;
  provider: PushProvider;
  platform: PushPlatform;
  device_label: string | null;
  created_at: string;
  updated_at: string;
  last_seen_at: string;
}

export interface PushTestResponse {
  sent: number;
  skipped: number;
  message: string;
}

export async function registerPushToken(payload: {
  token: string;
  provider?: PushProvider;
  platform?: PushPlatform;
  device_label?: string | null;
}): Promise<DeviceTokenResponse> {
  return api.put<DeviceTokenResponse>('/devices/push-token', {
    token: payload.token,
    provider: payload.provider ?? 'fcm',
    platform: payload.platform ?? 'android',
    device_label: payload.device_label ?? null,
  });
}

export async function unregisterPushToken(token: string): Promise<void> {
  await api.delete('/devices/push-token', { json: { token } });
}

export async function listPushTokens(): Promise<DeviceTokenResponse[]> {
  return api.get<DeviceTokenResponse[]>('/devices/push-tokens');
}

export async function sendPushTest(): Promise<PushTestResponse> {
  return api.post<PushTestResponse>('/devices/push-test');
}
