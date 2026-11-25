import React from 'react';
import type { RuleHit } from '../api/types';

interface RuleTraceTableProps {
  ruleHits: RuleHit[];
}

export const RuleTraceTable: React.FC<RuleTraceTableProps> = ({ ruleHits }) => {
  if (ruleHits.length === 0) {
    return <p className="text-muted-foreground text-sm py-4">No scoring rules triggered.</p>;
  }

  return (
    <div className="rounded-xl bg-band border border-border overflow-hidden">
      <div className="overflow-x-auto bg-card">
        <table className="w-full text-left text-sm text-foreground">
          <thead className="bg-band border-b border-border text-xs text-muted-foreground">
            <tr>
              <th className="py-3 px-4">Rule ID</th>
              <th className="py-3 px-4">Description</th>
              <th className="py-3 px-4 text-right">Points</th>
              <th className="py-3 px-4">Evidence refs</th>
            </tr>
          </thead>
          <tbody className="divide-y divide-border font-sans">
            {ruleHits.map((hit) => {
              const isPositive = hit.points > 0;
              const isNegative = hit.points < 0;
              const pointsClass = isPositive
                ? 'text-risk-critical-fg'
                : isNegative
                  ? 'text-risk-low-fg'
                  : 'text-muted-foreground';
              const formattedPoints = isPositive ? `+${hit.points}` : `${hit.points}`;

              return (
                <tr key={hit.rule_id} className="hover:bg-band/60 transition">
                  <td className="py-3 px-4 font-mono text-xs text-foreground">{hit.rule_id}</td>
                  <td className="py-3 px-4 text-muted-foreground">{hit.description}</td>
                  <td className={`py-3 px-4 text-right font-mono tabular-nums ${pointsClass}`}>
                    {formattedPoints}
                  </td>
                  <td className="py-3 px-4">
                    <div className="flex flex-wrap gap-1.5">
                      {hit.evidence_refs.map((ref) => (
                        <span
                          key={ref}
                          className="inline-flex px-2 py-0.5 rounded-md text-xs font-mono bg-secondary text-muted-foreground"
                        >
                          {ref}
                        </span>
                      ))}
                    </div>
                  </td>
                </tr>
              );
            })}
          </tbody>
        </table>
      </div>
    </div>
  );
};
