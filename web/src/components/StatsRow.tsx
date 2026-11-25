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
      <div className="bg-card border border-border rounded-xl p-4">
        <div className="text-xs text-muted-foreground">TOTAL</div>
        <div
          data-testid="stat-total"
          className="text-2xl font-mono tabular-nums text-foreground mt-1"
        >
          {total}
        </div>
        <div className="text-xs text-subtle-foreground mt-1">on this page</div>
      </div>

      <div className="bg-card border border-border rounded-xl p-4">
        <div className="text-xs text-muted-foreground">HIGH RISK</div>
        <div
          data-testid="stat-high-risk"
          className={`text-2xl font-mono tabular-nums mt-1 ${
            highRiskCount > 0 ? 'text-risk-high-fg' : 'text-subtle-foreground'
          }`}
        >
          {highRiskCount}
        </div>
        <div className="text-xs text-subtle-foreground mt-1">on this page</div>
      </div>

      <div className="bg-card border border-border rounded-xl p-4">
        <div className="text-xs text-muted-foreground">LAST 24H</div>
        <div
          data-testid="stat-recent"
          className={`text-2xl font-mono tabular-nums mt-1 ${
            recentCount > 0 ? 'text-risk-low-fg' : 'text-subtle-foreground'
          }`}
        >
          {recentCount}
        </div>
        <div className="text-xs text-subtle-foreground mt-1">on this page</div>
      </div>
    </div>
  );
};
