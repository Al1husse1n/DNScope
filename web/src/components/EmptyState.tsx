import React from 'react';
import { Search } from 'lucide-react';

export const EmptyState: React.FC = () => {
  const focusInput = () => {
    const el = document.getElementById('domain-input');
    el?.focus();
  };

  return (
    <div className="text-center py-14 px-4 border border-border rounded-xl bg-card max-w-xl mx-auto my-8">
      <div className="w-10 h-10 rounded-xl bg-band border border-border flex items-center justify-center mx-auto text-accent mb-4">
        <Search className="w-5 h-5" />
      </div>
      <h3 className="text-base text-foreground">No investigations yet</h3>
      <p className="text-sm text-muted-foreground mt-2 max-w-md mx-auto">
        Domain submission arrives in P6b. For now, investigations created via API or tests will
        appear here.
      </p>
      <div className="mt-6">
        <button
          type="button"
          onClick={focusInput}
          className="inline-flex items-center gap-2 px-4 py-2 rounded-xl bg-primary hover:bg-primary-hover text-primary-foreground text-xs transition cursor-pointer"
        >
          <Search className="w-3.5 h-3.5" />
          Investigate a domain
        </button>
      </div>
    </div>
  );
};
