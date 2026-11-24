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
      className="p-6 rounded-lg bg-red-950/40 border border-red-900 text-red-200 max-w-xl mx-auto my-6"
    >
      <div className="flex items-start gap-3">
        <AlertCircle className="w-5 h-5 text-red-400 shrink-0 mt-0.5" />
        <div className="flex-1">
          <h3 className="text-sm font-semibold text-red-300">Error</h3>
          <p className="text-sm text-red-300/90 mt-1">{message}</p>
          {onRetry && (
            <button
              onClick={onRetry}
              className="mt-4 inline-flex items-center gap-1.5 px-3 py-1.5 rounded text-xs font-medium bg-red-900 hover:bg-red-800 text-white transition cursor-pointer"
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
