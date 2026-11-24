import { useState, useEffect, useRef, useCallback } from 'react';
import { usePostInvestigation, useJob } from '../api/jobs';
import { ApiError } from '../api/client';

export type SubmissionStage =
  | { kind: 'idle' }
  | { kind: 'submitting' }
  | { kind: 'polling'; jobId: string; domain: string; startedAt: number }
  | { kind: 'completed'; jobId: string; investigationId: string }
  | { kind: 'failed'; jobId: string; domain: string; error: string }
  | { kind: 'rate_limited'; retryAfter: number };

export interface UseSubmissionFlowOptions {
  onCompleted?: (investigationId: string) => void;
}

export function useSubmissionFlow(options?: UseSubmissionFlowOptions) {
  const [stage, setStage] = useState<SubmissionStage>({ kind: 'idle' });
  const [formError, setFormError] = useState<string | null>(null);

  const optionsRef = useRef(options);
  optionsRef.current = options;

  const postInvestigation = usePostInvestigation();
  const pollingJobId = stage.kind === 'polling' ? stage.jobId : null;
  const jobQuery = useJob(pollingJobId);

  // 60-second timeout for polling
  useEffect(() => {
    if (stage.kind !== 'polling') return;

    const timer = setTimeout(() => {
      setStage({
        kind: 'failed',
        jobId: stage.jobId,
        domain: stage.domain,
        error: 'Investigation did not complete within 60 seconds.',
      });
    }, 60000);

    return () => clearTimeout(timer);
  }, [stage]);

  // Handle job status transitions
  useEffect(() => {
    if (stage.kind !== 'polling') return;
    const jobData = jobQuery.data;
    if (!jobData) return;

    if (jobData.status === 'COMPLETED' && jobData.investigation_id) {
      const invId = jobData.investigation_id;
      const jId = stage.jobId;
      setStage({
        kind: 'completed',
        jobId: jId,
        investigationId: invId,
      });
      optionsRef.current?.onCompleted?.(invId);
    } else if (jobData.status === 'FAILED') {
      setStage({
        kind: 'failed',
        jobId: stage.jobId,
        domain: stage.domain,
        error: jobData.error ?? 'Unknown error',
      });
    }
  }, [stage, jobQuery.data]);

  const submit = useCallback(
    async (domain: string) => {
      setFormError(null);
      setStage({ kind: 'submitting' });

      try {
        const res = await postInvestigation.mutateAsync({ domain });
        setStage({
          kind: 'polling',
          jobId: res.job_id,
          domain,
          startedAt: Date.now(),
        });
      } catch (err: unknown) {
        if (err instanceof ApiError) {
          if (err.status === 400) {
            setStage({ kind: 'idle' });
            setFormError(err.message || 'Invalid domain');
            return;
          }
          if (err.status === 429) {
            setStage({
              kind: 'rate_limited',
              retryAfter: err.retryAfter ?? 60,
            });
            return;
          }
          setStage({ kind: 'idle' });
          setFormError(err.message || 'Submission failed');
          return;
        }

        const msg = err instanceof Error ? err.message : 'Submission failed';
        setStage({ kind: 'idle' });
        setFormError(msg);
      }
    },
    [postInvestigation],
  );

  const dismiss = useCallback(() => {
    setStage({ kind: 'idle' });
    setFormError(null);
  }, []);

  return {
    stage,
    formError,
    submit,
    dismiss,
  };
}

