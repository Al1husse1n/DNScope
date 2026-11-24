import React from 'react';
import { AlertTriangle } from 'lucide-react';
import type { InconclusiveCheck } from '../api/types';

interface InconclusivePanelProps {
  checks: InconclusiveCheck[];
}

export const InconclusivePanel: React.FC<InconclusivePanelProps> = ({ checks }) => {
  if (checks.length === 0) return null;

  return (
    <div className="p-4 rounded-lg bg-amber-950/40 border border-amber-900/60 text-amber-200">
      <div className="flex items-center gap-2 mb-2 font-medium text-amber-300">
        <AlertTriangle className="w-4 h-4 text-amber-400" />
        <span className="text-sm font-semibold">Inconclusive Checks</span>
      </div>
      <ul className="space-y-1 text-xs text-amber-300/90 ml-6 list-disc">
        {checks.map((chk, idx) => (
          <li key={idx}>
            <span className="font-mono font-medium text-amber-200 uppercase">
              {chk.agent_name.toUpperCase()}
            </span>
            : {chk.reason}
          </li>
        ))}
      </ul>
    </div>
  );
};
