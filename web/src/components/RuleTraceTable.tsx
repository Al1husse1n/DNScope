import React from 'react';
import type { RuleHit } from '../api/types';

interface RuleTraceTableProps {
  ruleHits: RuleHit[];
}

export const RuleTraceTable: React.FC<RuleTraceTableProps> = ({ ruleHits }) => {
  if (ruleHits.length === 0) {
    return <p className="text-slate-400 text-sm py-4 italic">No scoring rules triggered.</p>;
  }

  return (
    <div className="overflow-x-auto border border-slate-800 rounded-lg">
      <table className="w-full text-left text-sm text-slate-300">
        <thead className="bg-slate-900/80 border-b border-slate-800 text-xs uppercase tracking-wider text-slate-400">
          <tr>
            <th className="py-3 px-4 font-semibold">Rule ID</th>
            <th className="py-3 px-4 font-semibold">Description</th>
            <th className="py-3 px-4 font-semibold text-right">Points</th>
            <th className="py-3 px-4 font-semibold">Evidence Refs</th>
          </tr>
        </thead>
        <tbody className="divide-y divide-slate-800/70 font-sans">
          {ruleHits.map((hit) => {
            const isPositive = hit.points > 0;
            const isNegative = hit.points < 0;
            const pointsClass = isPositive
              ? 'text-red-400 font-semibold'
              : isNegative
                ? 'text-emerald-400 font-semibold'
                : 'text-slate-400';
            const formattedPoints = isPositive ? `+${hit.points}` : `${hit.points}`;

            return (
              <tr key={hit.rule_id} className="hover:bg-slate-800/30 transition">
                <td className="py-3 px-4 font-mono font-medium text-slate-200">{hit.rule_id}</td>
                <td className="py-3 px-4 text-slate-300">{hit.description}</td>
                <td className={`py-3 px-4 text-right font-mono ${pointsClass}`}>
                  {formattedPoints}
                </td>
                <td className="py-3 px-4">
                  <div className="flex flex-wrap gap-1">
                    {hit.evidence_refs.map((ref) => (
                      <span
                        key={ref}
                        className="inline-flex px-1.5 py-0.5 rounded text-xs font-mono bg-slate-800 text-slate-300 border border-slate-700"
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
  );
};
