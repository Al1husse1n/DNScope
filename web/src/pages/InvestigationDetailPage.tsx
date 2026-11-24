import React from 'react';
import { useParams, Link } from 'react-router-dom';
import { ArrowLeft, Clock } from 'lucide-react';
import { useInvestigation } from '../api/investigations';
import { RiskBadge } from '../components/RiskBadge';
import { ScoreGauge } from '../components/ScoreGauge';
import { RuleTraceTable } from '../components/RuleTraceTable';
import { NarrativeCard } from '../components/NarrativeCard';
import { InconclusivePanel } from '../components/InconclusivePanel';
import { RateLimitBanner } from '../components/RateLimitBanner';
import { ErrorPanel } from '../components/ErrorPanel';
import { LoadingSkeleton } from '../components/LoadingSkeleton';
import { formatRelativeTime } from '../utils/relativeTime';

export const InvestigationDetailPage: React.FC = () => {
  const { id = '' } = useParams<{ id: string }>();
  const { data: inv, isLoading, isError, error, refetch } = useInvestigation(id);

  const isRateLimited = error?.status === 429;
  const isNotFound = error?.status === 404;

  if (isLoading) {
    return (
      <div className="max-w-5xl mx-auto px-4 sm:px-6 py-8">
        <LoadingSkeleton type="detail" />
      </div>
    );
  }

  if (isRateLimited) {
    return (
      <div className="max-w-5xl mx-auto px-4 sm:px-6 py-8">
        <RateLimitBanner retryAfter={error?.retryAfter || 60} onRetry={() => refetch()} />
      </div>
    );
  }

  if (isNotFound) {
    return (
      <div className="max-w-5xl mx-auto px-4 sm:px-6 py-12 text-center">
        <ErrorPanel message="Investigation not found." />
        <Link
          to="/"
          className="inline-flex items-center gap-1.5 text-sm text-sky-400 hover:text-sky-300 font-medium mt-4"
        >
          <ArrowLeft className="w-4 h-4" /> Back to investigations
        </Link>
      </div>
    );
  }

  if (isError || !inv) {
    return (
      <div className="max-w-5xl mx-auto px-4 sm:px-6 py-8">
        <ErrorPanel
          message={error?.message || 'Failed to load investigation details.'}
          onRetry={() => refetch()}
        />
        <div className="mt-4">
          <Link
            to="/"
            className="inline-flex items-center gap-1.5 text-sm text-sky-400 hover:text-sky-300 font-medium"
          >
            <ArrowLeft className="w-4 h-4" /> Back to investigations
          </Link>
        </div>
      </div>
    );
  }

  const scoreResult = inv.assessment.score_result;

  return (
    <div className="max-w-5xl mx-auto px-4 sm:px-6 py-8 space-y-8">
      {/* Header & Navigation */}
      <div>
        <Link
          to="/"
          className="inline-flex items-center gap-1.5 text-xs font-mono text-slate-400 hover:text-slate-200 transition mb-4"
        >
          <ArrowLeft className="w-3.5 h-3.5" /> Back to investigations
        </Link>

        <div className="bg-slate-900 border border-slate-800 rounded-xl p-6 shadow-xl space-y-4">
          <div className="flex flex-col sm:flex-row sm:items-center justify-between gap-4">
            <div>
              <div className="flex items-center gap-3">
                <h1 className="text-2xl sm:text-3xl font-bold font-mono text-white tracking-tight">
                  {inv.domain}
                </h1>
                <RiskBadge level={scoreResult.risk_level} />
              </div>
              <div className="flex items-center gap-3 mt-2 text-xs text-slate-400 font-mono">
                <span className="flex items-center gap-1" title={inv.created_at}>
                  <Clock className="w-3.5 h-3.5" />
                  Investigated {formatRelativeTime(inv.created_at)}
                </span>
                <span>•</span>
                <span className="text-slate-500">ID: {inv.id}</span>
              </div>
            </div>

            <div className="sm:self-center">
              <ScoreGauge
                score={scoreResult.score}
                riskLevel={scoreResult.risk_level}
                width={260}
              />
            </div>
          </div>
        </div>
      </div>

      {/* Inconclusive checks if any */}
      {inv.assessment.inconclusive_checks.length > 0 && (
        <InconclusivePanel checks={inv.assessment.inconclusive_checks} />
      )}

      {/* AI Narrative */}
      <NarrativeCard narrative={inv.assessment.narrative} />

      {/* Rule Trace Table */}
      <div className="space-y-3">
        <h2 className="text-lg font-semibold text-white tracking-tight">Rule Evaluation Trace</h2>
        <RuleTraceTable ruleHits={scoreResult.rule_hits} />
      </div>

      {/* Deterministic Explanation */}
      {inv.assessment.rule_trace_explanation && (
        <div className="space-y-2">
          <h2 className="text-xs uppercase tracking-wider text-slate-400 font-semibold font-mono">
            Deterministic Engine Trace
          </h2>
          <pre className="p-4 rounded-lg bg-slate-900/60 border border-slate-800 text-xs font-mono text-slate-300 overflow-x-auto whitespace-pre-wrap leading-relaxed">
            {inv.assessment.rule_trace_explanation}
          </pre>
        </div>
      )}
    </div>
  );
};
