import React, { useState } from 'react';
import { useNavigate } from 'react-router-dom';
import { useQueryClient } from '@tanstack/react-query';
import { useInvestigations } from '../api/investigations';
import { useSubmissionFlow } from '../hooks/useSubmissionFlow';
import { RiskBadge } from '../components/RiskBadge';
import { ScoreGauge } from '../components/ScoreGauge';
import { RateLimitBanner } from '../components/RateLimitBanner';
import { ErrorPanel } from '../components/ErrorPanel';
import { LoadingSkeleton } from '../components/LoadingSkeleton';
import { EmptyState } from '../components/EmptyState';
import { StatsRow } from '../components/StatsRow';
import { SubmissionForm } from '../components/SubmissionForm';
import { PendingInvestigationCard } from '../components/PendingInvestigationCard';
import { formatRelativeTime } from '../utils/relativeTime';

const PAGE_SIZE = 20;

export const InvestigationsListPage: React.FC = () => {
  const [offset, setOffset] = useState(0);
  const navigate = useNavigate();
  const queryClient = useQueryClient();

  const flow = useSubmissionFlow({
    onCompleted: (newId) => {
      queryClient.invalidateQueries({ queryKey: ['investigations'] });
      navigate(`/dashboard/investigations/${newId}`);
    },
  });

  const { data, isLoading, isError, error, refetch } = useInvestigations(PAGE_SIZE, offset);

  const isRateLimited = error?.status === 429;
  const retryAfter = error?.retryAfter || 60;

  const handleRowClick = (id: string) => {
    navigate(`/dashboard/investigations/${id}`);
  };

  const handleKeyDown = (e: React.KeyboardEvent, id: string) => {
    if (e.key === 'Enter' || e.key === ' ') {
      e.preventDefault();
      handleRowClick(id);
    }
  };

  const total = data?.total || 0;
  const items = data?.items || [];
  const startCount = total === 0 ? 0 : offset + 1;
  const endCount = Math.min(offset + PAGE_SIZE, total);

  return (
    <div className="max-w-6xl mx-auto px-4 sm:px-6 py-8">
      <div className="flex items-center justify-between mb-6">
        <div className="flex items-center gap-3">
          <h1 className="text-2xl tracking-tight text-foreground">Investigations</h1>
          {data && (
            <span className="px-2.5 py-0.5 rounded-md text-xs font-mono bg-secondary text-muted-foreground">
              {total}
            </span>
          )}
        </div>
      </div>

      {items.length > 0 && <StatsRow items={items} />}

      <SubmissionForm flow={flow} />

      <PendingInvestigationCard
        stage={flow.stage}
        onNavigate={(id) => navigate(`/investigations/${id}`)}
        onDismiss={flow.dismiss}
      />

      {isRateLimited && <RateLimitBanner retryAfter={retryAfter} onRetry={() => refetch()} />}

      {isLoading && <LoadingSkeleton rows={5} />}

      {isError && !isRateLimited && (
        <ErrorPanel
          message={error?.message || 'Failed to load investigations.'}
          onRetry={() => refetch()}
        />
      )}

      {!isLoading && !isError && items.length === 0 && <EmptyState />}

      {!isLoading && !isError && items.length > 0 && (
        <>
          <div className="rounded-xl bg-band border border-border overflow-hidden">
            <div className="overflow-x-auto bg-card">
              <table className="w-full text-left text-sm text-foreground">
                <thead className="bg-band border-b border-border text-xs text-muted-foreground">
                  <tr>
                    <th className="py-3.5 px-4">Domain</th>
                    <th className="py-3.5 px-4">Risk level</th>
                    <th className="py-3.5 px-4">Score</th>
                    <th className="py-3.5 px-4 text-right">Created</th>
                  </tr>
                </thead>
                <tbody className="divide-y divide-border">
                  {items.map((inv) => (
                    <tr
                      key={inv.id}
                      onClick={() => handleRowClick(inv.id)}
                      onKeyDown={(e) => handleKeyDown(e, inv.id)}
                      tabIndex={0}
                      role="button"
                      className="hover:bg-band/60 cursor-pointer transition focus:outline-none focus:bg-band"
                    >
                      <td className="py-4 px-4 font-mono text-foreground">{inv.domain}</td>
                      <td className="py-4 px-4">
                        <RiskBadge level={inv.risk_level} />
                      </td>
                      <td className="py-4 px-4">
                        <ScoreGauge score={inv.risk_score} riskLevel={inv.risk_level} width={200} />
                      </td>
                      <td className="py-4 px-4 text-right text-xs text-muted-foreground font-mono">
                        {formatRelativeTime(inv.created_at)}
                      </td>
                    </tr>
                  ))}
                </tbody>
              </table>
            </div>
          </div>

          <div className="flex items-center justify-between mt-4 text-xs text-muted-foreground font-mono px-2">
            <div>
              Showing {startCount}–{endCount} of {total}
            </div>
            <div className="flex gap-2">
              <button
                onClick={() => setOffset((prev) => Math.max(0, prev - PAGE_SIZE))}
                disabled={offset === 0}
                className="px-3.5 py-1.5 rounded-xl bg-secondary hover:bg-secondary-hover disabled:opacity-40 disabled:cursor-not-allowed text-secondary-foreground transition cursor-pointer"
              >
                Previous
              </button>
              <button
                onClick={() => setOffset((prev) => prev + PAGE_SIZE)}
                disabled={offset + PAGE_SIZE >= total}
                className="px-3.5 py-1.5 rounded-xl bg-secondary hover:bg-secondary-hover disabled:opacity-40 disabled:cursor-not-allowed text-secondary-foreground transition cursor-pointer"
              >
                Next
              </button>
            </div>
          </div>
        </>
      )}
    </div>
  );
};
