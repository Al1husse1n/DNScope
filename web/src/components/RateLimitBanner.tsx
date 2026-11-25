import React, { useEffect, useState } from 'react';
import { AlertCircle, RefreshCw } from 'lucide-react';

interface RateLimitBannerProps {
  retryAfter: number;
  onRetry: () => void;
}

export const RateLimitBanner: React.FC<RateLimitBannerProps> = ({ retryAfter, onRetry }) => {
  const [secondsLeft, setSecondsLeft] = useState(retryAfter);

  useEffect(() => {
    setSecondsLeft(retryAfter);
  }, [retryAfter]);

  useEffect(() => {
    if (secondsLeft <= 0) return;

    const timer = setInterval(() => {
      setSecondsLeft((prev) => {
        if (prev <= 1) {
          clearInterval(timer);
          return 0;
        }
        return prev - 1;
      });
    }, 1000);

    return () => clearInterval(timer);
  }, [secondsLeft]);

  return (
    <div
      role="alert"
      className="bg-risk-medium-bg border border-border rounded-xl p-4 my-4 flex items-center justify-between text-risk-medium-fg"
    >
      <div className="flex items-center gap-3">
        <AlertCircle className="w-5 h-5 shrink-0" />
        <span className="text-sm">
          {secondsLeft > 0 ? `Rate limit reached. Retry in ${secondsLeft}s.` : 'Ready to retry.'}
        </span>
      </div>
      <button
        onClick={onRetry}
        disabled={secondsLeft > 0}
        className={`inline-flex items-center gap-1.5 px-3.5 py-1.5 rounded-xl text-xs transition-colors ${
          secondsLeft > 0
            ? 'bg-secondary text-subtle-foreground cursor-not-allowed'
            : 'bg-primary hover:bg-primary-hover text-primary-foreground cursor-pointer'
        }`}
      >
        <RefreshCw className="w-3.5 h-3.5" />
        Retry
      </button>
    </div>
  );
};
