import React, { useState } from 'react';
import { useNavigate } from 'react-router-dom';
import { useInvestigations } from '../api/investigations';
import { RiskBadge } from '../components/RiskBadge';
import { ScoreGauge } from '../components/ScoreGauge';
import { RateLimitBanner } from '../components/RateLimitBanner';
import { ErrorPanel } from '../components/ErrorPanel';
import { LoadingSkeleton } from '../components/LoadingSkeleton';
import { EmptyState } from '../components/EmptyState';
import { formatRelativeTime } from '../utils/relativeTime';

const PAGE_SIZE = 20;

export const InvestigationsListPage: React.FC = () => {
  const [offset, setOffset] = useState(0);
  const navigate = useNavigate();

  const { data, isLoading, isError, error, refetch } = useInvestigations(PAGE_SIZE, offset);

  const isRateLimited = error?.status === 429;
  const retryAfter = error?.retryAfter || 60;

  const handleRowClick = (id: string) => {
    navigate(`/investigations/${id}`);
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
          <h1 className="text-2xl font-bold tracking-tight text-white">Investigations</h1>
          {data && (
            <span className="px-2.5 py-0.5 rounded-full text-xs font-mono font-semibold bg-slate-800 text-slate-300 border border-slate-700">
              {total}
            </span>
          )}
        </div>
      </div>

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
          <div className="overflow-x-auto border border-slate-800 rounded-xl bg-slate-900 shadow-xl">
            <table className="w-full text-left text-sm text-slate-300">
              <thead className="bg-slate-950/60 border-b border-slate-800 text-xs uppercase tracking-wider text-slate-400 font-mono">
                <tr>
                  <th className="py-3.5 px-4 font-semibold">Domain</th>
                  <th className="py-3.5 px-4 font-semibold">Risk Level</th>
                  <th className="py-3.5 px-4 font-semibold">Score</th>
                  <th className="py-3.5 px-4 font-semibold text-right">Created</th>
                </tr>
              </thead>
              <tbody className="divide-y divide-slate-800">
                {items.map((inv) => (
                  <tr
                    key={inv.id}
                    onClick={() => handleRowClick(inv.id)}
                    onKeyDown={(e) => handleKeyDown(e, inv.id)}
                    tabIndex={0}
                    role="button"
                    className="hover:bg-slate-800/50 cursor-pointer transition focus:outline-none focus:bg-slate-800/70"
                  >
                    <td className="py-4 px-4 font-mono font-bold text-slate-100">{inv.domain}</td>
                    <td className="py-4 px-4">
                      <RiskBadge level={inv.risk_level} />
                    </td>
                    <td className="py-4 px-4">
                      <ScoreGauge score={inv.risk_score} riskLevel={inv.risk_level} width={200} />
                    </td>
                    <td
                      className="py-4 px-4 text-right text-xs text-slate-400 font-mono"
                      title={inv.created_at}
                    >
                      {formatRelativeTime(inv.created_at)}
                    </td>
                  </tr>
                ))}
              </tbody>
            </table>
          </div>

          <div className="flex items-center justify-between mt-4 text-xs text-slate-400 font-mono px-2">
            <div>
              Showing {startCount}–{endCount} of {total}
            </div>
            <div className="flex gap-2">
              <button
                onClick={() => setOffset((prev) => Math.max(0, prev - PAGE_SIZE))}
                disabled={offset === 0}
                className="px-3 py-1.5 rounded bg-slate-800 hover:bg-slate-700 disabled:opacity-40 disabled:cursor-not-allowed text-slate-200 transition"
              >
                Previous
              </button>
              <button
                onClick={() => setOffset((prev) => prev + PAGE_SIZE)}
                disabled={offset + PAGE_SIZE >= total}
                className="px-3 py-1.5 rounded bg-slate-800 hover:bg-slate-700 disabled:opacity-40 disabled:cursor-not-allowed text-slate-200 transition"
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
