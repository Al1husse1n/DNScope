import { useMutation, useQuery } from '@tanstack/react-query';
import type { JobResponse } from './types';
import { apiFetch } from './client';
import { useAuth } from '../auth/useAuth';

export interface CreateInvestigationResponse {
  job_id: string;
  status: 'PENDING';
}

export function usePostInvestigation() {
  const { rawKey } = useAuth();
  return useMutation<CreateInvestigationResponse, Error, { domain: string }>({
    mutationFn: ({ domain }) =>
      apiFetch<CreateInvestigationResponse>('/investigations', {
        method: 'POST',
        apiKey: rawKey,
        body: { domain },
      }),
  });
}

export function useJob(jobId: string | null) {
  const { rawKey } = useAuth();
  return useQuery<JobResponse>({
    queryKey: ['jobs', jobId],
    queryFn: () => apiFetch<JobResponse>(`/jobs/${jobId}`, { apiKey: rawKey }),
    enabled: !!jobId && !!rawKey,
    refetchInterval: (query) => {
      const status = query.state.data?.status;
      if (status === 'PENDING' || status === 'RUNNING') return 1500;
      return false; // stop polling on COMPLETED or FAILED
    },
    staleTime: 0,
  });
}

