import { apiFetch } from './client';
import type { ListInvestigationsResponse } from './types';

export async function testApiKey(rawKey: string): Promise<void> {
  await apiFetch<ListInvestigationsResponse>('/investigations?limit=1', {
    apiKey: rawKey,
  });
}
