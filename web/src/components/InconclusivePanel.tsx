import React from 'react';
import { AlertTriangle } from 'lucide-react';
import type { InconclusiveCheck } from '../api/types';

interface InconclusivePanelProps {
  checks: InconclusiveCheck[];
}

export const InconclusivePanel: React.FC<InconclusivePanelProps> = ({ checks }) => {
  if (checks.length === 0) return null;

  return (
    <div className="rounded-xl bg-band border border-border overflow-hidden">
      <div className="flex items-center gap-2 px-4 py-2.5 text-xs text-risk-medium-fg">
        <AlertTriangle className="w-3.5 h-3.5" />
        <span>Inconclusive checks</span>
      </div>
      <div className="p-4 bg-card border-t border-border rounded-[calc(0.75rem-1px)]">
        <ul className="space-y-1.5 text-xs text-muted-foreground ml-4 list-disc">
          {checks.map((chk, idx) => (
            <li key={idx}>
              <span className="font-mono text-foreground">{chk.agent_name.toUpperCase()}</span>:{' '}
              {chk.reason}
            </li>
          ))}
        </ul>
      </div>
    </div>
  );
};
