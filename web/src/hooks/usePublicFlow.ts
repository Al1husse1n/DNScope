import { useState, useRef, useCallback, useEffect } from 'react';
import { investigatePublic, PublicInvestigationResponse } from '../api/public';
import { ApiError } from '../api/client';

export type PublicFlowStage =
  'idle' | 'submitting' | 'running' | 'complete' | 'failed' | 'rate_limited';

export interface UsePublicFlowOptions {
  onCompleted?: (result: PublicInvestigationResponse) => void;
}

export function usePublicFlow(options?: UsePublicFlowOptions) {
  const [stage, setStage] = useState<PublicFlowStage>('idle');
  const [domain, setDomain] = useState<string>('');
  const [startedAt, setStartedAt] = useState<number | null>(null);
  const [result, setResult] = useState<PublicInvestigationResponse | null>(null);
  const [error, setError] = useState<string | null>(null);
  const [retryAfter, setRetryAfter] = useState<number | null>(null);

  const abortControllerRef = useRef<AbortController | null>(null);
  const optionsRef = useRef(options);
  optionsRef.current = options;

  useEffect(() => {
    return () => {
      if (abortControllerRef.current) {
        abortControllerRef.current.abort();
      }
    };
  }, []);

  const submit = useCallback(async (targetDomain: string) => {
    if (abortControllerRef.current) {
      abortControllerRef.current.abort();
    }

    const controller = new AbortController();
    abortControllerRef.current = controller;

    // 90-second client timeout
    const timeoutId = setTimeout(() => {
      controller.abort();
    }, 90000);

    const now = Date.now();
    setDomain(targetDomain);
    setStartedAt(now);
    setResult(null);
    setError(null);
    setRetryAfter(null);
    setStage('running');

    try {
      const data = await investigatePublic(targetDomain, controller.signal);
      clearTimeout(timeoutId);
      setResult(data);
      setStage('complete');
      optionsRef.current?.onCompleted?.(data);
    } catch (err: unknown) {
      clearTimeout(timeoutId);
      if (controller.signal.aborted) {
        setStage('failed');
        setError('Investigation timed out after 90 seconds.');
        return;
      }
      if (err instanceof ApiError) {
        if (err.status === 400) {
          setStage('failed');
          setError(err.message || 'Invalid domain');
          return;
        }
        if (err.status === 429) {
          setStage('rate_limited');
          setRetryAfter(err.retryAfter ?? 60);
          return;
        }
        setStage('failed');
        setError(err.message || 'Investigation failed');
        return;
      }
      setStage('failed');
      setError(err instanceof Error ? err.message : 'Investigation failed');
    }
  }, []);

  const reset = useCallback(() => {
    if (abortControllerRef.current) {
      abortControllerRef.current.abort();
    }
    setStage('idle');
    setDomain('');
    setStartedAt(null);
    setResult(null);
    setError(null);
    setRetryAfter(null);
  }, []);

  return {
    stage,
    domain,
    startedAt,
    result,
    error,
    retryAfter,
    submit,
    reset,
  };
}
