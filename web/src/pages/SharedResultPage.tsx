import React, { useState, useEffect, useCallback } from 'react';
import { useParams, Link } from 'react-router-dom';
import { ArrowLeft, Clock, Copy, Check, AlertTriangle, AlertCircle } from 'lucide-react';
import { getSharedResult, PublicInvestigationResponse } from '../api/public';
import { ApiError } from '../api/client';
import { NavBar } from '../components/NavBar';
import { RiskBadge } from '../components/RiskBadge';
import { ScoreGauge } from '../components/ScoreGauge';
import { RuleTraceTable } from '../components/RuleTraceTable';
import { NarrativeCard } from '../components/NarrativeCard';
import { InconclusivePanel } from '../components/InconclusivePanel';
import { RateLimitBanner } from '../components/RateLimitBanner';
import { ErrorPanel } from '../components/ErrorPanel';
import { LoadingSkeleton } from '../components/LoadingSkeleton';
import { formatRelativeTime } from '../utils/relativeTime';

export const SharedResultPage: React.FC = () => {
  const { shareId = '' } = useParams<{ shareId: string }>();
  const [data, setData] = useState<PublicInvestigationResponse | null>(null);
  const [loading, setLoading] = useState<boolean>(true);
  const [error, setError] = useState<ApiError | null>(null);
  const [copied, setCopied] = useState<boolean>(false);

  const fetchResult = useCallback(async () => {
    if (!shareId) return;
    setLoading(true);
    setError(null);
    try {
      const res = await getSharedResult(shareId);
      setData(res);
    } catch (err: unknown) {
      if (err instanceof ApiError) {
        setError(err);
      } else {
        setError(new ApiError(0, 'error', null, null, 'Failed to load report.'));
      }
    } finally {
      setLoading(false);
    }
  }, [shareId]);

  useEffect(() => {
    fetchResult();
  }, [fetchResult]);

  const handleCopy = async () => {
    const url = window.location.href;
    try {
      await navigator.clipboard.writeText(url);
      setCopied(true);
      setTimeout(() => setCopied(false), 2000);
    } catch {
      // Fallback
    }
  };

  if (loading) {
    return (
      <div className="min-h-screen bg-background text-foreground flex flex-col">
        <NavBar />
        <main className="max-w-5xl w-full mx-auto px-4 sm:px-6 py-8">
          <LoadingSkeleton type="detail" />
        </main>
      </div>
    );
  }

  if (error?.status === 429) {
    return (
      <div className="min-h-screen bg-background text-foreground flex flex-col">
        <NavBar />
        <main className="max-w-5xl w-full mx-auto px-4 sm:px-6 py-8">
          <RateLimitBanner retryAfter={error.retryAfter || 60} onRetry={fetchResult} />
        </main>
      </div>
    );
  }

  if (error?.status === 404) {
    return (
      <div className="min-h-screen bg-background text-foreground flex flex-col">
        <NavBar />
        <main className="max-w-2xl w-full mx-auto px-4 sm:px-6 py-16 text-center">
          <div className="w-12 h-12 rounded-xl bg-risk-critical-bg border border-border flex items-center justify-center text-risk-critical-fg mx-auto mb-4">
            <AlertCircle className="w-6 h-6" />
          </div>
          <h1 className="text-2xl text-foreground mb-2">This result has expired</h1>
          <p className="text-sm text-muted-foreground mb-6">
            Public investigation links are preserved for 1 hour. This report is no longer available.
          </p>
          <Link
            to="/"
            className="inline-flex items-center gap-2 px-5 py-2.5 rounded-xl bg-primary hover:bg-primary-hover text-primary-foreground text-sm transition"
          >
            Investigate again →
          </Link>
        </main>
      </div>
    );
  }

  if (error || !data) {
    return (
      <div className="min-h-screen bg-background text-foreground flex flex-col">
        <NavBar />
        <main className="max-w-5xl w-full mx-auto px-4 sm:px-6 py-8">
          <ErrorPanel message={error?.message || 'Failed to load report.'} onRetry={fetchResult} />
          <div className="mt-4">
            <Link
              to="/"
              className="inline-flex items-center gap-1.5 text-sm text-accent hover:text-primary-hover"
            >
              <ArrowLeft className="w-4 h-4" /> Back to home
            </Link>
          </div>
        </main>
      </div>
    );
  }

  const { domain, normalized_domain, created_at, assessment, narrative_source } = data;
  const isDeterministicOnly = narrative_source === 'deterministic_only';

  return (
    <div className="min-h-screen bg-background text-foreground flex flex-col">
      <NavBar />

      <main className="max-w-5xl w-full mx-auto px-4 sm:px-6 py-8 space-y-6">
        {/* Navigation & Share Row */}
        <div className="flex items-center justify-between flex-wrap gap-4">
          <Link
            to="/"
            className="inline-flex items-center gap-1.5 text-sm text-accent hover:text-primary-hover transition focus:outline-none focus-visible:ring-2 focus-visible:ring-accent rounded-xl"
          >
            <ArrowLeft className="w-4 h-4" /> Investigate another domain
          </Link>

          <button
            onClick={handleCopy}
            className="inline-flex items-center gap-1.5 px-3.5 py-1.5 text-xs rounded-xl bg-secondary hover:bg-secondary-hover text-secondary-foreground transition cursor-pointer focus:outline-none focus-visible:ring-2 focus-visible:ring-accent"
          >
            {copied ? (
              <>
                <Check className="w-3.5 h-3.5 text-risk-low-fg" />
                <span className="text-risk-low-fg">Copied!</span>
              </>
            ) : (
              <>
                <Copy className="w-3.5 h-3.5 text-muted-foreground" />
                <span>Copy share link</span>
              </>
            )}
          </button>
        </div>

        {/* Daily Cap Banner if Deterministic Only */}
        {isDeterministicOnly && (
          <div
            role="alert"
            className="bg-risk-medium-bg border border-border rounded-xl p-4 flex items-center gap-3 text-risk-medium-fg"
          >
            <AlertTriangle className="w-5 h-5 shrink-0" />
            <div className="text-sm">
              <span>Daily AI analysis cap reached — </span>
              showing deterministic risk scoring. Score, rule hits, and inconclusive checks are
              fully populated.
            </div>
          </div>
        )}

        {/* Header / Summary Card */}
        <div className="bg-card border border-border rounded-xl p-6">
          <div className="flex flex-col sm:flex-row items-start sm:items-center justify-between gap-6">
            <div className="space-y-1.5">
              <h1 className="text-2xl sm:text-3xl font-mono text-foreground tracking-tight">
                {domain}
              </h1>
              {normalized_domain && normalized_domain !== domain && (
                <div className="text-xs font-mono text-muted-foreground">
                  Normalized: {normalized_domain}
                </div>
              )}
              <div className="flex items-center gap-1.5 text-xs text-muted-foreground pt-1">
                <Clock className="w-3.5 h-3.5" />
                <span>Investigated {formatRelativeTime(created_at)}</span>
              </div>
            </div>

            <div className="flex items-center gap-4 self-stretch sm:self-auto justify-between sm:justify-end">
              <div className="text-right">
                <div className="text-xs text-muted-foreground mb-1">Risk level</div>
                <RiskBadge level={assessment.score_result.risk_level} />
              </div>
              <ScoreGauge
                score={assessment.score_result.score}
                riskLevel={assessment.score_result.risk_level}
              />
            </div>
          </div>
        </div>

        {/* Rule Trace Table */}
        <RuleTraceTable ruleHits={assessment.score_result.rule_hits} />

        {/* Narrative Card */}
        <NarrativeCard narrative={assessment.narrative} />

        {/* Inconclusive Panel */}
        <InconclusivePanel checks={assessment.inconclusive_checks} />
      </main>
    </div>
  );
};
