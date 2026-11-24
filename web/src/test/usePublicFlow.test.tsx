import { describe, it, expect, vi, beforeEach, afterEach } from 'vitest';
import { renderHook, act } from '@testing-library/react';
import { usePublicFlow } from '../hooks/usePublicFlow';
import * as publicApi from '../api/public';
import { ApiError } from '../api/client';
import type { PublicInvestigationResponse } from '../api/public';

vi.mock('../api/public');

const mockPublicResponse: PublicInvestigationResponse = {
  share_id: '11111111-2222-3333-4444-555555555555',
  domain: 'example.com',
  normalized_domain: 'example.com',
  created_at: new Date().toISOString(),
  assessment: {
    score_result: {
      score: 25,
      risk_level: 'LOW',
      rule_hits: [
        {
          rule_id: 'R1',
          description: 'Test rule hit',
          points: 25,
          evidence_refs: ['ref1'],
        },
      ],
      total_points_before_clamp: 25,
    },
    rule_trace_explanation: 'Trace explanation',
    narrative: 'Analyst summary',
    inconclusive_checks: [],
  },
  narrative_source: 'gemini',
};

describe('usePublicFlow', () => {
  beforeEach(() => {
    vi.restoreAllMocks();
  });

  afterEach(() => {
    vi.restoreAllMocks();
  });

  it('sets stage to complete upon successful 201 investigation', async () => {
    vi.mocked(publicApi.investigatePublic).mockResolvedValueOnce(mockPublicResponse);
    const onCompleted = vi.fn();

    const { result } = renderHook(() => usePublicFlow({ onCompleted }));

    expect(result.current.stage).toBe('idle');

    await act(async () => {
      await result.current.submit('example.com');
    });

    expect(publicApi.investigatePublic).toHaveBeenCalledWith(
      'example.com',
      expect.any(AbortSignal),
    );
    expect(result.current.stage).toBe('complete');
    expect(result.current.result).toEqual(mockPublicResponse);
    expect(result.current.error).toBeNull();
    expect(onCompleted).toHaveBeenCalledWith(mockPublicResponse);
  });

  it('sets stage to failed on 400 invalid_domain', async () => {
    vi.mocked(publicApi.investigatePublic).mockRejectedValueOnce(
      new ApiError(400, 'invalid_domain', null, null, 'Invalid domain format'),
    );

    const { result } = renderHook(() => usePublicFlow());

    await act(async () => {
      await result.current.submit('http://invalid.com');
    });

    expect(result.current.stage).toBe('failed');
    expect(result.current.error).toBe('Invalid domain format');
    expect(result.current.result).toBeNull();
  });

  it('sets stage to rate_limited on 429 response', async () => {
    vi.mocked(publicApi.investigatePublic).mockRejectedValueOnce(
      new ApiError(429, 'rate_limited', 45, null, 'Rate limit reached'),
    );

    const { result } = renderHook(() => usePublicFlow());

    await act(async () => {
      await result.current.submit('ratelimited.com');
    });

    expect(result.current.stage).toBe('rate_limited');
    expect(result.current.retryAfter).toBe(45);
  });

  it('sets stage to failed on network error', async () => {
    vi.mocked(publicApi.investigatePublic).mockRejectedValueOnce(
      new ApiError(0, 'network_error', null, null, 'Network error'),
    );

    const { result } = renderHook(() => usePublicFlow());

    await act(async () => {
      await result.current.submit('offline.com');
    });

    expect(result.current.stage).toBe('failed');
    expect(result.current.error).toBe('Network error');
  });

  it('resets state back to idle on reset()', async () => {
    vi.mocked(publicApi.investigatePublic).mockRejectedValueOnce(
      new ApiError(400, 'invalid_domain', null, null, 'Invalid domain'),
    );

    const { result } = renderHook(() => usePublicFlow());

    await act(async () => {
      await result.current.submit('bad.com');
    });

    expect(result.current.stage).toBe('failed');

    act(() => {
      result.current.reset();
    });

    expect(result.current.stage).toBe('idle');
    expect(result.current.domain).toBe('');
    expect(result.current.error).toBeNull();
    expect(result.current.result).toBeNull();
  });
});
