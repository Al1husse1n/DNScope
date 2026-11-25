import React, { useState, useEffect } from 'react';
import { Loader2, Search } from 'lucide-react';
import { useSubmissionFlow } from '../hooks/useSubmissionFlow';
import { RateLimitBanner } from './RateLimitBanner';

export interface SubmissionFormProps {
  onSubmitted?: () => void;
  flow?: ReturnType<typeof useSubmissionFlow>;
}

interface SubmissionFormInnerProps {
  onSubmitted?: () => void;
  flow: ReturnType<typeof useSubmissionFlow>;
}

const SubmissionFormInner: React.FC<SubmissionFormInnerProps> = ({ onSubmitted, flow }) => {
  const [domain, setDomain] = useState('');
  const [lastSubmittedDomain, setLastSubmittedDomain] = useState('');
  const [rateLimitSeconds, setRateLimitSeconds] = useState(0);

  const trimmed = domain.trim();
  const isValidLength = trimmed.length >= 1 && trimmed.length <= 253;

  const isSubmitting = flow.stage.kind === 'submitting';
  const isPolling = flow.stage.kind === 'polling';
  const isRateLimited = flow.stage.kind === 'rate_limited';

  useEffect(() => {
    if (flow.stage.kind === 'rate_limited') {
      setRateLimitSeconds(flow.stage.retryAfter);
    } else {
      setRateLimitSeconds(0);
    }
  }, [flow.stage]);

  useEffect(() => {
    if (rateLimitSeconds <= 0) return;
    const timer = setInterval(() => {
      setRateLimitSeconds((prev) => {
        if (prev <= 1) {
          clearInterval(timer);
          return 0;
        }
        return prev - 1;
      });
    }, 1000);
    return () => clearInterval(timer);
  }, [rateLimitSeconds]);

  const handleSubmit = async (e: React.FormEvent) => {
    e.preventDefault();
    if (!isValidLength || isSubmitting || isPolling || rateLimitSeconds > 0) return;

    setLastSubmittedDomain(trimmed);
    await flow.submit(trimmed);
    onSubmitted?.();
  };

  const handleRetryRateLimit = async () => {
    if (!lastSubmittedDomain) return;
    await flow.submit(lastSubmittedDomain);
  };

  const isSubmitDisabled =
    !isValidLength || isSubmitting || isPolling || (isRateLimited && rateLimitSeconds > 0);

  return (
    <div className="rounded-xl bg-band border border-border overflow-hidden mb-6">
      <div className="px-5 py-2.5 text-xs text-muted-foreground">
        <label htmlFor="domain-input" className="cursor-pointer">
          Investigate a domain
        </label>
      </div>

      <div className="p-5 bg-card border-t border-border rounded-[calc(0.75rem-1px)]">
        {/* Rate limit banner */}
        {flow.stage.kind === 'rate_limited' && (
          <div className="mb-4">
            <RateLimitBanner retryAfter={flow.stage.retryAfter} onRetry={handleRetryRateLimit} />
          </div>
        )}

        {/* Inline Form Error */}
        {flow.formError && (
          <div
            role="alert"
            className="text-xs font-mono text-risk-critical-fg bg-risk-critical-bg border border-border rounded-xl px-3.5 py-2.5 mb-3.5"
          >
            {flow.formError}
          </div>
        )}

        <form onSubmit={handleSubmit} className="flex flex-col sm:flex-row gap-3">
          <div className="relative flex-1">
            <div className="absolute inset-y-0 left-0 pl-3.5 flex items-center pointer-events-none text-subtle-foreground">
              <Search className="w-4 h-4" />
            </div>
            <input
              id="domain-input"
              type="text"
              autoFocus
              autoComplete="off"
              disabled={isSubmitting || isPolling}
              placeholder="example.com or suspicious-domain.net"
              value={domain}
              onChange={(e) => setDomain(e.target.value)}
              className="w-full pl-10 pr-4 py-2.5 rounded-xl bg-input border border-border-strong text-foreground placeholder-muted-foreground/80 font-mono text-sm focus:outline-none focus:border-accent focus:ring-1 focus:ring-accent disabled:opacity-50 disabled:cursor-not-allowed transition"
            />
          </div>
          <button
            type="submit"
            disabled={isSubmitDisabled}
            className="inline-flex items-center justify-center gap-2 px-5 py-2.5 rounded-xl bg-primary hover:bg-primary-hover disabled:opacity-40 disabled:cursor-not-allowed text-primary-foreground text-sm transition font-sans cursor-pointer focus:outline-none focus-visible:ring-2 focus-visible:ring-accent"
          >
            {isSubmitting ? (
              <>
                <Loader2 className="w-4 h-4 animate-spin" />
                <span>Investigating…</span>
              </>
            ) : (
              <span>Investigate</span>
            )}
          </button>
        </form>
      </div>
    </div>
  );
};

const SubmissionFormWithInternalFlow: React.FC<Omit<SubmissionFormProps, 'flow'>> = ({
  onSubmitted,
}) => {
  const flow = useSubmissionFlow();
  return <SubmissionFormInner onSubmitted={onSubmitted} flow={flow} />;
};

export const SubmissionForm: React.FC<SubmissionFormProps> = ({ onSubmitted, flow }) => {
  if (flow) {
    return <SubmissionFormInner onSubmitted={onSubmitted} flow={flow} />;
  }
  return <SubmissionFormWithInternalFlow onSubmitted={onSubmitted} />;
};
