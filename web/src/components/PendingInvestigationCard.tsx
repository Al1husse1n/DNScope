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
        className="bg-rose-950/40 border border-rose-800/80 rounded-xl p-5 mb-6 text-rose-200 shadow-lg"
      >
        <div className="flex items-start justify-between gap-4">
          <div className="flex items-start gap-3">
            <AlertTriangle className="w-5 h-5 text-rose-400 shrink-0 mt-0.5" />
            <div>
              <div className="font-semibold text-rose-100 flex items-center gap-2">
                <span>✗ Investigation failed</span>
                {stage.domain && (
                  <span className="font-mono text-sm text-rose-300 font-normal">
                    — {stage.domain}
                  </span>
                )}
              </div>
              <div className="text-sm text-rose-300/90 mt-1">{stage.error}</div>
            </div>
          </div>
          <button
            onClick={onDismiss}
            className="px-3 py-1.5 rounded text-xs font-medium bg-rose-900/60 hover:bg-rose-800/80 text-rose-200 border border-rose-700/60 transition"
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
      <div className="bg-slate-900 border border-slate-800 rounded-xl p-5 mb-6 shadow-xl space-y-4">
        <div className="flex items-center justify-between">
          <div className="flex items-center gap-3">
            <Check className="w-5 h-5 text-emerald-400 shrink-0" />
            <span className="font-semibold text-emerald-100">✓ Investigation complete</span>
          </div>
          <button
            onClick={() => onNavigate(stage.investigationId)}
            className="inline-flex items-center gap-1.5 px-3 py-1.5 rounded text-xs font-medium bg-emerald-700 hover:bg-emerald-600 text-white transition"
          >
            View <ArrowRight className="w-3.5 h-3.5" />
          </button>
        </div>
        <div className="grid grid-cols-1 sm:grid-cols-2 gap-2.5 pt-1">
          {STAGES.map((label, index) => (
            <div
              key={label}
              className="flex items-center gap-2.5 p-2.5 rounded-lg border text-xs font-mono bg-slate-950/60 border-emerald-900/60 text-emerald-300"
            >
              <div className="w-4 h-4 flex items-center justify-center shrink-0">
                <span className="text-emerald-400 font-bold" data-testid={`stage-${index}-done`}>
                  ✓
                </span>
              </div>
              <span className="truncate">{label}</span>
            </div>
          ))}
        </div>
        <div className="text-[11px] text-slate-500 font-mono text-center pt-1 border-t border-slate-800/60">
          Progress is approximate. Actual timing varies.
        </div>
      </div>
    );
  }

  // Polling state
  const isCompleted = false;

  const getStageStatus = (index: number) => {
    if (isCompleted) return 'done';
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
    // index === 3
    if (elapsed < 11) return 'waiting';
    return 'running';
  };

  return (
    <div className="bg-slate-900 border border-slate-800 rounded-xl p-5 mb-6 shadow-xl space-y-4">
      {/* Header */}
      <div className="flex items-center justify-between flex-wrap gap-2">
        <div className="flex items-center gap-3">
          <Loader2 className="w-5 h-5 text-sky-400 animate-spin shrink-0" />
          <span className="font-mono text-lg font-bold text-white">{stage.domain}</span>
        </div>
        <span className="text-xs font-mono text-slate-400">Running for {elapsed}s…</span>
      </div>

      {/* 4-stage checklist */}
      <div className="grid grid-cols-1 sm:grid-cols-2 gap-2.5 pt-1">
        {STAGES.map((label, index) => {
          const status = getStageStatus(index);
          return (
            <div
              key={label}
              className={`flex items-center gap-2.5 p-2.5 rounded-lg border text-xs font-mono transition-colors ${
                status === 'done'
                  ? 'bg-slate-950/60 border-emerald-900/60 text-emerald-300'
                  : status === 'running'
                    ? 'bg-slate-950/80 border-sky-800/80 text-sky-200'
                    : 'bg-slate-950/30 border-slate-800/50 text-slate-500'
              }`}
            >
              <div className="w-4 h-4 flex items-center justify-center shrink-0">
                {status === 'done' && (
                  <span className="text-emerald-400 font-bold" data-testid={`stage-${index}-done`}>
                    ✓
                  </span>
                )}
                {status === 'running' && (
                  <Loader2
                    className="w-3.5 h-3.5 text-sky-400 animate-spin"
                    data-testid={`stage-${index}-running`}
                  />
                )}
                {status === 'waiting' && (
                  <span
                    className="text-slate-600 font-bold text-xs"
                    data-testid={`stage-${index}-waiting`}
                  >
                    ●
                  </span>
                )}
              </div>
              <span className="truncate">{label}</span>
            </div>
          );
        })}
      </div>

      {/* Disclaimer */}
      <div className="text-[11px] text-slate-500 font-mono text-center pt-1 border-t border-slate-800/60">
        Progress is approximate. Actual timing varies.
      </div>
    </div>
  );
};
