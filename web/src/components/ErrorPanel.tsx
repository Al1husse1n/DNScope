import React from 'react';
import { AlertCircle, RefreshCw } from 'lucide-react';

interface ErrorPanelProps {
  message: string;
  onRetry?: () => void;
}

export const ErrorPanel: React.FC<ErrorPanelProps> = ({ message, onRetry }) => {
  return (
    <div
      role="alert"
      className="p-6 rounded-xl bg-risk-critical-bg border border-border text-risk-critical-fg max-w-xl mx-auto my-6"
    >
      <div className="flex items-start gap-3">
        <AlertCircle className="w-5 h-5 shrink-0 mt-0.5" />
        <div className="flex-1">
          <h3 className="text-sm">Error</h3>
          <p className="text-sm mt-1">{message}</p>
          {onRetry && (
            <button
              onClick={onRetry}
              className="mt-4 inline-flex items-center gap-1.5 px-3.5 py-1.5 rounded-xl text-xs bg-secondary hover:bg-secondary-hover text-secondary-foreground transition cursor-pointer"
            >
              <RefreshCw className="w-3.5 h-3.5" />
              Try again
            </button>
          )}
        </div>
      </div>
    </div>
  );
};
