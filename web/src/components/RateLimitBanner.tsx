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
      className="bg-amber-950/60 border border-amber-800/80 rounded-lg p-4 my-4 flex items-center justify-between text-amber-200"
    >
      <div className="flex items-center gap-3">
        <AlertCircle className="w-5 h-5 text-amber-400 shrink-0" />
        <span className="text-sm font-medium">
          {secondsLeft > 0 ? `Rate limit reached. Retry in ${secondsLeft}s.` : 'Ready to retry.'}
        </span>
      </div>
      <button
        onClick={onRetry}
        disabled={secondsLeft > 0}
        className={`inline-flex items-center gap-1.5 px-3 py-1.5 rounded text-xs font-medium transition-colors ${
          secondsLeft > 0
            ? 'bg-slate-800 text-slate-500 cursor-not-allowed'
            : 'bg-amber-600 hover:bg-amber-500 text-white cursor-pointer'
        }`}
      >
        <RefreshCw className="w-3.5 h-3.5" />
        Retry
      </button>
    </div>
  );
};
