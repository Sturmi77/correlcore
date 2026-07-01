import { api } from './client';

export interface DeleteAccountRequest {
  password: string;
}

export async function deleteAccount(payload: DeleteAccountRequest): Promise<void> {
  await api.delete('/user/me', { json: payload });
}
