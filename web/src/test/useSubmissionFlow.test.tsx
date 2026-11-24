import { describe, it, expect, vi, beforeEach, afterEach } from 'vitest';
import { renderHook, act } from '@testing-library/react';
import { useSubmissionFlow } from '../hooks/useSubmissionFlow';
import * as jobsApi from '../api/jobs';
import { ApiError } from '../api/client';
import type { UseQueryResult } from '@tanstack/react-query';
import type { JobResponse } from '../api/types';

vi.mock('../api/jobs');

describe('useSubmissionFlow', () => {
  let mockMutateAsync: ReturnType<typeof vi.fn>;
  let mockJobData: Partial<JobResponse> | undefined;

  beforeEach(() => {
    mockMutateAsync = vi.fn();
    mockJobData = undefined;

    vi.mocked(jobsApi.usePostInvestigation).mockReturnValue({
      mutateAsync: mockMutateAsync,
    } as unknown as ReturnType<typeof jobsApi.usePostInvestigation>);

    vi.mocked(jobsApi.useJob).mockImplementation(() => {
      return {
        data: mockJobData as JobResponse | undefined,
      } as UseQueryResult<JobResponse, Error>;
    });
  });

  afterEach(() => {
    vi.restoreAllMocks();
  });

  it('sets stage to polling upon successful 202 post mutation', async () => {
    mockMutateAsync.mockResolvedValueOnce({ job_id: 'job-123', status: 'PENDING' });

    const { result } = renderHook(() => useSubmissionFlow());

    expect(result.current.stage).toEqual({ kind: 'idle' });

    await act(async () => {
      await result.current.submit('example.com');
    });

    expect(mockMutateAsync).toHaveBeenCalledWith({ domain: 'example.com' });
    expect(result.current.stage).toEqual({
      kind: 'polling',
      jobId: 'job-123',
      domain: 'example.com',
      startedAt: expect.any(Number),
    });
    expect(result.current.formError).toBeNull();
  });

  it('sets formError and resets stage to idle on 400 invalid_domain', async () => {
    mockMutateAsync.mockRejectedValueOnce(
      new ApiError(400, 'invalid_domain', null, null, 'Invalid domain name'),
    );

    const { result } = renderHook(() => useSubmissionFlow());

    await act(async () => {
      await result.current.submit('bad-domain');
    });

    expect(result.current.stage).toEqual({ kind: 'idle' });
    expect(result.current.formError).toBe('Invalid domain name');
  });

  it('sets stage to rate_limited on 429 response with retryAfter', async () => {
    mockMutateAsync.mockRejectedValueOnce(
      new ApiError(429, 'rate_limited', 45, null, 'Too many requests'),
    );

    const { result } = renderHook(() => useSubmissionFlow());

    await act(async () => {
      await result.current.submit('example.com');
    });

    expect(result.current.stage).toEqual({
      kind: 'rate_limited',
      retryAfter: 45,
    });
  });

  it('calls onCompleted once with investigation id when job completes', async () => {
    mockMutateAsync.mockResolvedValueOnce({ job_id: 'job-123', status: 'PENDING' });
    const onCompleted = vi.fn();

    const { result, rerender } = renderHook(() => useSubmissionFlow({ onCompleted }));

    await act(async () => {
      await result.current.submit('example.com');
    });

    // 1. PENDING
    mockJobData = {
      job_id: 'job-123',
      status: 'PENDING',
      domain: 'example.com',
      investigation_id: null,
    };
    rerender();
    expect(result.current.stage.kind).toBe('polling');
    expect(onCompleted).not.toHaveBeenCalled();

    // 2. RUNNING
    mockJobData = {
      job_id: 'job-123',
      status: 'RUNNING',
      domain: 'example.com',
      investigation_id: null,
    };
    rerender();
    expect(result.current.stage.kind).toBe('polling');
    expect(onCompleted).not.toHaveBeenCalled();

    // 3. COMPLETED
    mockJobData = {
      job_id: 'job-123',
      status: 'COMPLETED',
      domain: 'example.com',
      investigation_id: 'inv-456',
    };
    rerender();

    expect(result.current.stage).toEqual({
      kind: 'completed',
      jobId: 'job-123',
      investigationId: 'inv-456',
    });
    expect(onCompleted).toHaveBeenCalledTimes(1);
    expect(onCompleted).toHaveBeenCalledWith('inv-456');
  });

  it('transitions stage to failed with error message when job fails', async () => {
    mockMutateAsync.mockResolvedValueOnce({ job_id: 'job-123', status: 'PENDING' });

    const { result, rerender } = renderHook(() => useSubmissionFlow());

    await act(async () => {
      await result.current.submit('example.com');
    });

    mockJobData = {
      job_id: 'job-123',
      status: 'FAILED',
      domain: 'example.com',
      error: 'Upstream threat intel timeout',
    };
    rerender();

    expect(result.current.stage).toEqual({
      kind: 'failed',
      jobId: 'job-123',
      domain: 'example.com',
      error: 'Upstream threat intel timeout',
    });
  });

  it('transitions to failed state after 60-second polling timeout', async () => {
    vi.useFakeTimers();
    mockMutateAsync.mockResolvedValueOnce({ job_id: 'job-123', status: 'PENDING' });

    const { result } = renderHook(() => useSubmissionFlow());

    await act(async () => {
      await result.current.submit('example.com');
    });

    expect(result.current.stage.kind).toBe('polling');

    // Fast-forward 60 seconds
    act(() => {
      vi.advanceTimersByTime(60000);
    });

    expect(result.current.stage).toEqual({
      kind: 'failed',
      jobId: 'job-123',
      domain: 'example.com',
      error: 'Investigation did not complete within 60 seconds.',
    });

    vi.useRealTimers();
  });
});
