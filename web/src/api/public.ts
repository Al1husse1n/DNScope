import { apiFetch, postJson } from './client';
import { SupervisorAssessment } from './types';

export interface PublicInvestigationResponse {
  share_id: string;
  domain: string;
  normalized_domain: string;
  created_at: string;
  assessment: SupervisorAssessment;
  narrative_source: 'gemini' | 'deterministic_only';
}

export async function investigatePublic(
  domain: string,
  signal?: AbortSignal,
): Promise<PublicInvestigationResponse> {
  return postJson<PublicInvestigationResponse>('/investigate', { domain }, { signal });
}

export async function getSharedResult(
  shareId: string,
  signal?: AbortSignal,
): Promise<PublicInvestigationResponse> {
  return apiFetch<PublicInvestigationResponse>(`/r/${shareId}`, { signal });
}
