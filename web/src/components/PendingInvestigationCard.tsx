import React, { useEffect, useState } from 'react';
import { Loader2, Check, AlertTriangle, ArrowRight } from 'lucide-react';
import type { SubmissionStage } from '../hooks/useSubmissionFlow';

interface PendingInvestigationCardProps {
  stage: SubmissionStage;
  onNavigate: (id: string) => void;
  onDismiss: () => void;
}

const STAGES = [
  'Resolving DNS records',
  'Looking up registration data',
  'Checking threat intelligence',
  'Generating analyst narrative',
];

export const PendingInvestigationCard: React.FC<PendingInvestigationCardProps> = ({
  stage,
  onNavigate,
  onDismiss,
}) => {
  const [elapsed, setElapsed] = useState(0);

  // Timer for elapsed counter during polling
  useEffect(() => {
    if (stage.kind !== 'polling') {
      setElapsed(0);
      return;
    }

    const update = () => {
      const sec = Math.max(0, Math.floor((Date.now() - stage.startedAt) / 1000));
      setElapsed(sec);
    };

    update();
    const interval = setInterval(update, 1000);
    return () => clearInterval(interval);
  }, [stage]);

  // Navigate after 600ms delay on completion
  useEffect(() => {
    if (stage.kind === 'completed') {
      const timer = setTimeout(() => {
        onNavigate(stage.investigationId);
      }, 600);
      return () => clearTimeout(timer);
    }
  }, [stage, onNavigate]);

  if (stage.kind === 'idle' || stage.kind === 'submitting' || stage.kind === 'rate_limited') {
    return null;
  }

  // Failed state
  if (stage.kind === 'failed') {
    return (
      <div
        role="alert"
        className="bg-risk-critical-bg border border-border rounded-xl p-5 mb-6 text-risk-critical-fg"
      >
        <div className="flex items-start justify-between gap-4">
          <div className="flex items-start gap-3">
            <AlertTriangle className="w-5 h-5 shrink-0 mt-0.5" />
            <div>
              <div className="flex items-center gap-2">
                <span>✗ Investigation failed</span>
                {stage.domain && (
                  <span className="font-mono text-sm text-risk-critical-fg">— {stage.domain}</span>
                )}
              </div>
              <div className="text-sm text-risk-critical-fg mt-1">{stage.error}</div>
            </div>
          </div>
          <button
            onClick={onDismiss}
            className="px-3 py-1.5 rounded-xl text-xs bg-secondary hover:bg-secondary-hover text-secondary-foreground transition cursor-pointer"
          >
            Dismiss
          </button>
        </div>
      </div>
    );
  }

  // Completed state
  if (stage.kind === 'completed') {
    return (
      <div className="rounded-xl bg-band border border-border overflow-hidden mb-6">
        <div className="flex items-center justify-between px-5 py-3">
          <div className="flex items-center gap-2.5">
            <Check className="w-4 h-4 text-risk-low-fg shrink-0" />
            <span className="text-sm text-foreground">✓ Investigation complete</span>
          </div>
          <button
            onClick={() => onNavigate(stage.investigationId)}
            className="inline-flex items-center gap-1.5 px-3.5 py-1.5 rounded-xl text-xs bg-primary hover:bg-primary-hover text-primary-foreground transition cursor-pointer"
          >
            View <ArrowRight className="w-3.5 h-3.5" />
          </button>
        </div>
        <div className="p-5 bg-card border-t border-border rounded-[calc(0.75rem-1px)] space-y-3">
          <div className="grid grid-cols-1 sm:grid-cols-2 gap-2.5">
            {STAGES.map((label, index) => (
              <div
                key={label}
                className="flex items-center gap-2.5 p-2.5 rounded-lg text-xs bg-risk-low-bg text-risk-low-fg"
              >
                <div className="w-4 h-4 flex items-center justify-center shrink-0">
                  <span data-testid={`stage-${index}-done`}>✓</span>
                </div>
                <span className="truncate">{label}</span>
              </div>
            ))}
          </div>
          <div className="text-xs text-subtle-foreground text-center pt-2 border-t border-border">
            Progress is approximate. Actual timing varies.
          </div>
        </div>
      </div>
    );
  }

  // Polling state
  const getStageStatus = (index: number) => {
    if (index === 0) {
      if (elapsed < 2) return 'waiting';
      if (elapsed < 5) return 'running';
      return 'done';
    }
    if (index === 1) {
      if (elapsed < 5) return 'waiting';
      if (elapsed < 8) return 'running';
      return 'done';
    }
    if (index === 2) {
      if (elapsed < 8) return 'waiting';
      if (elapsed < 11) return 'running';
      return 'done';
    }
    if (elapsed < 11) return 'waiting';
    return 'running';
  };

  return (
    <div className="rounded-xl bg-band border border-border overflow-hidden mb-6">
      <div className="flex items-center justify-between flex-wrap gap-2 px-5 py-3">
        <div className="flex items-center gap-3">
          <Loader2 className="w-4 h-4 text-accent animate-spin shrink-0" />
          <span className="font-mono text-base text-foreground">{stage.domain}</span>
        </div>
        <span className="text-xs font-mono text-muted-foreground">Running for {elapsed}s…</span>
      </div>

      <div className="p-5 bg-card border-t border-border rounded-[calc(0.75rem-1px)] space-y-3">
        <div className="grid grid-cols-1 sm:grid-cols-2 gap-2.5">
          {STAGES.map((label, index) => {
            const status = getStageStatus(index);
            return (
              <div
                key={label}
                className={`flex items-center gap-2.5 p-2.5 rounded-lg text-xs transition-colors ${
                  status === 'done'
                    ? 'bg-risk-low-bg text-risk-low-fg'
                    : status === 'running'
                      ? 'bg-secondary text-foreground'
                      : 'bg-input text-subtle-foreground'
                }`}
              >
                <div className="w-4 h-4 flex items-center justify-center shrink-0">
                  {status === 'done' && (
                    <span className="text-risk-low-fg" data-testid={`stage-${index}-done`}>
                      ✓
                    </span>
                  )}
                  {status === 'running' && (
                    <Loader2
                      className="w-3.5 h-3.5 text-accent animate-spin"
                      data-testid={`stage-${index}-running`}
                    />
                  )}
                  {status === 'waiting' && (
                    <span className="text-subtle-foreground" data-testid={`stage-${index}-waiting`}>
                      ●
                    </span>
                  )}
                </div>
                <span className="truncate">{label}</span>
              </div>
            );
          })}
        </div>

        <div className="text-xs text-subtle-foreground text-center pt-2 border-t border-border">
          Progress is approximate. Actual timing varies.
        </div>
      </div>
    </div>
  );
};
