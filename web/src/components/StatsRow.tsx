import React from 'react';
import type { InvestigationSummary } from '../api/types';

interface StatsRowProps {
  items: InvestigationSummary[];
}

export const StatsRow: React.FC<StatsRowProps> = ({ items }) => {
  const total = items.length;

  const highRiskCount = items.filter(
    (item) => item.risk_level === 'HIGH' || item.risk_level === 'CRITICAL',
  ).length;

  const now = Date.now();
  const recentCount = items.filter((item) => {
    const createdTime = new Date(item.created_at).getTime();
    const diff = now - createdTime;
    return diff >= 0 && diff <= 24 * 60 * 60 * 1000;
  }).length;

  return (
    <div className="grid grid-cols-1 sm:grid-cols-3 gap-4 mb-6">
      {/* Total Card */}
      <div className="bg-slate-900 border border-slate-800 rounded-xl p-4 shadow-sm">
        <div className="text-[11px] font-mono font-semibold tracking-wider uppercase text-slate-400">
          TOTAL
        </div>
        <div data-testid="stat-total" className="text-2xl font-bold font-mono text-slate-100 mt-1">
          {total}
        </div>
        <div className="text-xs text-slate-500 font-mono mt-1">on this page</div>
      </div>

      {/* High Risk Card */}
      <div className="bg-slate-900 border border-slate-800 rounded-xl p-4 shadow-sm">
        <div className="text-[11px] font-mono font-semibold tracking-wider uppercase text-slate-400">
          HIGH RISK
        </div>
        <div
          data-testid="stat-high-risk"
          className={`text-2xl font-bold font-mono mt-1 ${
            highRiskCount > 0 ? 'text-amber-400' : 'text-slate-400'
          }`}
        >
          {highRiskCount}
        </div>
        <div className="text-xs text-slate-500 font-mono mt-1">on this page</div>
      </div>

      {/* Last 24h Card */}
      <div className="bg-slate-900 border border-slate-800 rounded-xl p-4 shadow-sm">
        <div className="text-[11px] font-mono font-semibold tracking-wider uppercase text-slate-400">
          LAST 24H
        </div>
        <div
          data-testid="stat-recent"
          className={`text-2xl font-bold font-mono mt-1 ${
            recentCount > 0 ? 'text-emerald-400' : 'text-slate-400'
          }`}
        >
          {recentCount}
        </div>
        <div className="text-xs text-slate-500 font-mono mt-1">on this page</div>
      </div>
    </div>
  );
};
