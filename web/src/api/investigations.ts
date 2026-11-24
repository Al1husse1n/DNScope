import { useQuery, UseQueryResult } from '@tanstack/react-query';
import { apiFetch, ApiError } from './client';
import { useAuth } from '../auth/useAuth';
import type { InvestigationResponse, ListInvestigationsResponse } from './types';

export const investigationKeys = {
  all: ['investigations'] as const,
  lists: () => [...investigationKeys.all, 'list'] as const,
  list: (limit: number, offset: number) =>
    [...investigationKeys.lists(), { limit, offset }] as const,
  details: () => [...investigationKeys.all, 'detail'] as const,
  detail: (id: string) => [...investigationKeys.details(), id] as const,
};

export function useInvestigations(
  limit = 20,
  offset = 0,
): UseQueryResult<ListInvestigationsResponse, ApiError> {
  const { rawKey } = useAuth();

  return useQuery({
    queryKey: investigationKeys.list(limit, offset),
    queryFn: () =>
      apiFetch<ListInvestigationsResponse>(`/investigations?limit=${limit}&offset=${offset}`, {
        apiKey: rawKey,
      }),
    enabled: !!rawKey,
    staleTime: 30_000,
    retry: (failureCount, error) => {
      if (error instanceof ApiError && error.status === 429) {
        return false;
      }
      return failureCount < 2;
    },
  });
}

export function useInvestigation(id: string): UseQueryResult<InvestigationResponse, ApiError> {
  const { rawKey } = useAuth();

  return useQuery({
    queryKey: investigationKeys.detail(id),
    queryFn: () =>
      apiFetch<InvestigationResponse>(`/investigations/${id}`, {
        apiKey: rawKey,
      }),
    enabled: !!rawKey && !!id,
    staleTime: 30_000,
    retry: (failureCount, error) => {
      if (error instanceof ApiError && error.status === 429) {
        return false;
      }
      return failureCount < 2;
    },
  });
}
