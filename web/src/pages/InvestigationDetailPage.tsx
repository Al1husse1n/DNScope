import React from 'react';
import { useParams, Link, useNavigate } from 'react-router-dom';
import { ArrowLeft, Clock, RotateCcw } from 'lucide-react';
import { useQueryClient } from '@tanstack/react-query';
import { useInvestigation } from '../api/investigations';
import { useSubmissionFlow } from '../hooks/useSubmissionFlow';
import { RiskBadge } from '../components/RiskBadge';
import { ScoreGauge } from '../components/ScoreGauge';
import { RuleTraceTable } from '../components/RuleTraceTable';
import { NarrativeCard } from '../components/NarrativeCard';
import { InconclusivePanel } from '../components/InconclusivePanel';
import { RateLimitBanner } from '../components/RateLimitBanner';
import { PendingInvestigationCard } from '../components/PendingInvestigationCard';
import { ErrorPanel } from '../components/ErrorPanel';
import { LoadingSkeleton } from '../components/LoadingSkeleton';
import { formatRelativeTime } from '../utils/relativeTime';

export const InvestigationDetailPage: React.FC = () => {
  const { id = '' } = useParams<{ id: string }>();
  const navigate = useNavigate();
  const queryClient = useQueryClient();

  const flow = useSubmissionFlow({
    onCompleted: (newId) => {
      queryClient.invalidateQueries({ queryKey: ['investigations'] });
      navigate(`/dashboard/investigations/${newId}`);
    },
  });

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
          to="/dashboard"
          className="inline-flex items-center gap-1.5 text-sm text-accent hover:text-primary-hover mt-4"
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
            to="/dashboard"
            className="inline-flex items-center gap-1.5 text-sm text-accent hover:text-primary-hover"
          >
            <ArrowLeft className="w-4 h-4" /> Back to investigations
          </Link>
        </div>
      </div>
    );
  }

  const scoreResult = inv.assessment.score_result;

  return (
    <div className="max-w-5xl mx-auto px-4 sm:px-6 py-8 space-y-6">
      <div>
        <div className="flex items-center justify-between mb-4">
          <Link
            to="/dashboard"
            className="inline-flex items-center gap-1.5 text-xs text-muted-foreground hover:text-foreground transition"
          >
            <ArrowLeft className="w-3.5 h-3.5" /> Back to investigations
          </Link>
          <button
            type="button"
            onClick={() => flow.submit(inv.domain)}
            disabled={flow.stage.kind === 'submitting' || flow.stage.kind === 'polling'}
            className="inline-flex items-center gap-1.5 px-3.5 py-1.5 rounded-xl text-xs bg-secondary hover:bg-secondary-hover disabled:opacity-40 disabled:cursor-not-allowed text-secondary-foreground transition cursor-pointer focus:outline-none focus-visible:ring-2 focus-visible:ring-accent"
          >
            <RotateCcw className="w-3.5 h-3.5 text-muted-foreground" />
            Re-run investigation
          </button>
        </div>

        {flow.stage.kind === 'rate_limited' && (
          <div className="mb-4">
            <RateLimitBanner
              retryAfter={flow.stage.retryAfter}
              onRetry={() => flow.submit(inv.domain)}
            />
          </div>
        )}

        {flow.formError && (
          <div
            role="alert"
            className="text-xs font-mono text-risk-critical-fg bg-risk-critical-bg border border-border rounded-xl px-3.5 py-2.5 mb-4 flex items-center justify-between"
          >
            <span>{flow.formError}</span>
            <button
              onClick={flow.dismiss}
              className="text-risk-critical-fg hover:text-foreground text-xs ml-4 cursor-pointer"
            >
              Dismiss
            </button>
          </div>
        )}

        <PendingInvestigationCard
          stage={flow.stage}
          onNavigate={(newId) => navigate(`/investigations/${newId}`)}
          onDismiss={flow.dismiss}
        />

        <div className="bg-card border border-border rounded-xl p-6 space-y-4">
          <div className="flex flex-col sm:flex-row sm:items-center justify-between gap-4">
            <div>
              <div className="flex items-center gap-3">
                <h1 className="text-2xl sm:text-3xl font-mono text-foreground tracking-tight">
                  {inv.domain}
                </h1>
                <RiskBadge level={scoreResult.risk_level} />
              </div>
              <div className="flex items-center gap-3 mt-2 text-xs text-muted-foreground font-mono">
                <span className="flex items-center gap-1">
                  <Clock className="w-3.5 h-3.5" />
                  Investigated {formatRelativeTime(inv.created_at)}
                </span>
                <span>•</span>
                <span className="text-subtle-foreground">ID: {inv.id}</span>
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

      {inv.assessment.inconclusive_checks.length > 0 && (
        <InconclusivePanel checks={inv.assessment.inconclusive_checks} />
      )}

      <NarrativeCard narrative={inv.assessment.narrative} />

      <div className="space-y-3">
        <h2 className="text-base text-foreground tracking-tight">Rule evaluation trace</h2>
        <RuleTraceTable ruleHits={scoreResult.rule_hits} />
      </div>

      {inv.assessment.rule_trace_explanation && (
        <div className="rounded-xl bg-band border border-border overflow-hidden">
          <div className="px-4 py-2.5 text-xs text-muted-foreground">
            Deterministic engine trace
          </div>
          <pre className="p-4 bg-card border-t border-border rounded-[calc(0.75rem-1px)] text-xs font-mono text-muted-foreground overflow-x-auto whitespace-pre-wrap leading-relaxed">
            {inv.assessment.rule_trace_explanation}
          </pre>
        </div>
      )}
    </div>
  );
};
