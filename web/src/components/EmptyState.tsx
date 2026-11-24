import React from 'react';
import { Search } from 'lucide-react';

export const EmptyState: React.FC = () => {
  return (
    <div className="text-center py-16 px-4 border border-dashed border-slate-800 rounded-xl bg-slate-900/20 max-w-xl mx-auto my-8">
      <div className="w-12 h-12 rounded-full bg-slate-800/80 flex items-center justify-center mx-auto text-slate-400 mb-4">
        <Search className="w-6 h-6" />
      </div>
      <h3 className="text-base font-semibold text-slate-200">No investigations yet</h3>
      <p className="text-sm text-slate-400 mt-2 max-w-md mx-auto">
        Domain submission arrives in P6b. For now, investigations created via API or tests will
        appear here.
      </p>
      <div className="mt-6 text-xs text-slate-500 font-mono">
        Need keys or sample investigations? Run{' '}
        <code className="bg-slate-800 text-slate-300 px-1.5 py-0.5 rounded">
          make seed-admin-key
        </code>
      </div>
    </div>
  );
};
